// vwar_monitor.cpp
// Minimal C++ real-time monitor prototype for Windows.
// Compatible with MSYS2 MinGW64 (g++ -std=c++17).
// Usage: vwar_monitor.exe [exclude_path1] [exclude_path2] ...

#include <windows.h>
#include <string>
#include <vector>
#include <thread>
#include <mutex>
#include <condition_variable>
#include <queue>
#include <chrono>
#include <filesystem>
#include <sstream>
#include <iostream>
#include <algorithm>
#include <atomic>
#include <cstdlib>

namespace fs = std::filesystem;
using namespace std::chrono_literals;

static std::atomic<bool> g_running(true);

// Convert wide string to UTF-8
static std::string wstring_to_utf8(const std::wstring &w) {
    if (w.empty()) return {};
    int size_needed = WideCharToMultiByte(CP_UTF8, 0, w.c_str(), (int)w.size(), NULL, 0, NULL, NULL);
    std::string strTo(size_needed, 0);
    WideCharToMultiByte(CP_UTF8, 0, w.c_str(), (int)w.size(), &strTo[0], size_needed, NULL, NULL);
    return strTo;
}

// ISO8601 UTC timestamp
static std::string iso_timestamp_utc() {
    std::time_t t = std::time(nullptr);
    std::tm gm{};
    gmtime_s(&gm, &t);
    char buf[64];
    std::strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", &gm);
    return std::string(buf);
}

// Named pipe server
class NamedPipeServer {
public:
    NamedPipeServer(const std::wstring &pipeName) : m_pipeName(pipeName), m_pipeHandle(INVALID_HANDLE_VALUE), m_running(true) {}
    void start() { m_thread = std::thread(&NamedPipeServer::run, this); }
    void stop() {
        m_running = false;
        m_cv.notify_all();
        if (m_thread.joinable()) m_thread.join();
    }
    void enqueue(const std::string &msg) {
        std::lock_guard<std::mutex> lk(m_mutex);
        m_queue.push(msg);
        m_cv.notify_one();
    }
private:
    void run() {
        while (m_running) {
            m_pipeHandle = CreateNamedPipeW(m_pipeName.c_str(),
                PIPE_ACCESS_OUTBOUND,
                PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT,
                1,
                64*1024,
                64*1024,
                0,
                NULL);
            if (m_pipeHandle == INVALID_HANDLE_VALUE) {
                std::cerr << "[pipe] CreateNamedPipeW failed: " << GetLastError() << "\n";
                std::this_thread::sleep_for(1s);
                continue;
            }
            std::cerr << "[pipe] Waiting for client to connect...\n";
            BOOL connected = ConnectNamedPipe(m_pipeHandle, NULL) ? TRUE : (GetLastError() == ERROR_PIPE_CONNECTED);
            if (!connected) {
                CloseHandle(m_pipeHandle);
                m_pipeHandle = INVALID_HANDLE_VALUE;
                std::this_thread::sleep_for(500ms);
                continue;
            }
            std::cerr << "[pipe] Client connected.\n";

            while (m_running) {
                std::string msg;
                {
                    std::unique_lock<std::mutex> lk(m_mutex);
                    if (m_queue.empty()) m_cv.wait_for(lk, 500ms);
                    if (!m_queue.empty()) { msg = m_queue.front(); m_queue.pop(); }
                }
                if (!msg.empty()) {
                    DWORD written = 0;
                    BOOL ok = WriteFile(m_pipeHandle, msg.data(), (DWORD)msg.size(), &written, NULL);
                    if (!ok) {
                        std::cerr << "[pipe] WriteFile failed: " << GetLastError() << "\n";
                        break;
                    }
                }
            }

            if (m_pipeHandle != INVALID_HANDLE_VALUE) {
                DisconnectNamedPipe(m_pipeHandle);
                CloseHandle(m_pipeHandle);
                m_pipeHandle = INVALID_HANDLE_VALUE;
            }
            std::this_thread::sleep_for(200ms);
        }
    }

    std::wstring m_pipeName;
    HANDLE m_pipeHandle;
    std::thread m_thread;
    std::mutex m_mutex;
    std::condition_variable m_cv;
    std::queue<std::string> m_queue;
    std::atomic<bool> m_running;
};

// global job queue
static std::mutex g_jobs_mutex;
static std::condition_variable g_jobs_cv;
static std::queue<std::wstring> g_jobs;

void push_job(const std::wstring &p) {
    {
        std::lock_guard<std::mutex> lk(g_jobs_mutex);
        g_jobs.push(p);
    }
    g_jobs_cv.notify_one();
}

bool pop_job(std::wstring &out) {
    std::unique_lock<std::mutex> lk(g_jobs_mutex);
    while (g_jobs.empty() && g_running) g_jobs_cv.wait_for(lk, 500ms);
    if (!g_running || g_jobs.empty()) return false;
    out = g_jobs.front();
    g_jobs.pop();
    return true;
}

// helper lowercase wstring
static std::wstring to_lower_copy(const std::wstring &s) {
    std::wstring r = s;
    std::transform(r.begin(), r.end(), r.begin(), ::towlower);
    return r;
}

bool starts_with_ci(const std::wstring &full, const std::wstring &prefix) {
    auto f = to_lower_copy(full);
    auto p = to_lower_copy(prefix);
    if (p.size() > f.size()) return false;
    return std::equal(p.begin(), p.end(), f.begin());
}

// readiness check
bool is_ready_for_scan(const std::wstring &fullpath, int max_ms = 5000) {
    using namespace std::chrono;
    auto start = steady_clock::now();
    try {
        if (!fs::exists(fullpath) || fs::is_directory(fullpath)) return false;
    } catch (...) { return false; }

    uintmax_t last_size = 0;
    int stable_count = 0;
    while (duration_cast<milliseconds>(steady_clock::now() - start).count() < max_ms) {
        try {
            uintmax_t sz = fs::file_size(fullpath);
            if (sz > 0 && sz == last_size) {
                stable_count++;
                if (stable_count >= 2) {
                    HANDLE h = CreateFileW(fullpath.c_str(), GENERIC_READ, 0, NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
                    if (h != INVALID_HANDLE_VALUE) { CloseHandle(h); return true; }
                }
            } else { stable_count = 0; }
            last_size = sz;
        } catch (...) {}
        std::this_thread::sleep_for(300ms);
    }
    return false;
}

// worker thread (immediate dispatch)
void worker_loop(NamedPipeServer *pipe, const std::vector<std::wstring> &excludes) {
    while (g_running) {
        std::wstring path;
        if (!pop_job(path)) continue;
        if (!g_running) break;

        bool skip = false;
        for (auto &ex : excludes) {
            if (starts_with_ci(path, ex)) { skip = true; break; }
        }
        if (skip) continue;

        std::string p8 = wstring_to_utf8(path);
        std::ostringstream oss;
        oss << "{\"path\":\"";
        for (unsigned char c : p8) {
            if (c == '\\') oss << "\\\\";
            else if (c == '\"') oss << "\\\"";
            else oss << c;
        }
        oss << "\",\"event\":\"created\",\"ts\":\"" << iso_timestamp_utc() << "\"}\n";

        pipe->enqueue(oss.str());
    }
}

// detect roots
std::vector<std::wstring> detect_roots() {
    std::vector<std::wstring> roots;
    char* up = getenv("USERPROFILE");
    if (up) {
        std::wstring user(up, up + strlen(up));
        std::vector<std::wstring> special = { L"Downloads", L"Desktop", L"Documents" };
        for (auto &s : special) {
            fs::path p = fs::path(user) / s;
            if (fs::exists(p)) roots.push_back(p.wstring());
        }
    }

    DWORD mask = GetLogicalDrives();
    for (int i = 0; i < 26; ++i) {
        if (mask & (1 << i)) {
            wchar_t driveRoot[4] = { wchar_t(L'A' + i), L':', L'\\', 0 };
            std::wstring drv(driveRoot);
            if (towupper(drv[0]) == L'C') continue;
            if (fs::exists(drv)) roots.push_back(drv);
        }
    }

    std::sort(roots.begin(), roots.end());
    roots.erase(std::unique(roots.begin(), roots.end()), roots.end());
    return roots;
}

// monitor directory
void monitor_directory(const std::wstring &root) {
    HANDLE hDir = CreateFileW(root.c_str(), FILE_LIST_DIRECTORY,
        FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
        NULL, OPEN_EXISTING,
        FILE_FLAG_BACKUP_SEMANTICS, NULL);

    if (hDir == INVALID_HANDLE_VALUE) {
        std::cerr << "[monitor] CreateFileW failed for " << wstring_to_utf8(root) << " (" << GetLastError() << ")\n";
        return;
    }

    const DWORD bufSize = 64 * 1024;
    std::vector<char> buffer(bufSize);

    while (g_running) {
        DWORD bytesReturned = 0;
        BOOL ok = ReadDirectoryChangesW(hDir, buffer.data(), bufSize, TRUE,
            FILE_NOTIFY_CHANGE_FILE_NAME | FILE_NOTIFY_CHANGE_LAST_WRITE | FILE_NOTIFY_CHANGE_SIZE,
            &bytesReturned, NULL, NULL);

        if (!ok) {
            std::cerr << "[monitor] ReadDirectoryChangesW failed: " << GetLastError() << "\n";
            break;
        }

        char *ptr = buffer.data();
        while (true) {
            FILE_NOTIFY_INFORMATION *fni = reinterpret_cast<FILE_NOTIFY_INFORMATION*>(ptr);
            std::wstring filename(fni->FileName, fni->FileName + fni->FileNameLength / sizeof(WCHAR));
            std::wstring full = root;
            if (!full.empty() && full.back() != L'\\' && full.back() != L'/') full += L"\\";
            full += filename;

            push_job(full);

            if (fni->NextEntryOffset == 0) break;
            ptr += fni->NextEntryOffset;
        }
    }

    CloseHandle(hDir);
}

// entry point
int main(int argc, char **argv) {
    std::wstring pipeName = L"\\\\.\\pipe\\vwar_monitor";

    std::vector<std::wstring> excludes;
    for (int i = 1; i < argc; ++i) {
        try {
            fs::path p = fs::path(argv[i]);
            if (!p.empty()) excludes.push_back(fs::absolute(p).wstring());
        } catch (...) {}
    }

    NamedPipeServer pipe(pipeName);
    pipe.start();

    const int num_workers = 4;
    std::vector<std::thread> workers;
    for (int i = 0; i < num_workers; ++i) workers.emplace_back(worker_loop, &pipe, excludes);

    auto roots = detect_roots();
    std::cerr << "[monitor] Roots to monitor:\n";
    for (auto &r : roots) std::cerr << "  " << wstring_to_utf8(r) << "\n";

    std::vector<std::thread> watchers;
    for (auto &r : roots) watchers.emplace_back(std::thread(monitor_directory, r));

    std::cerr << "[monitor] Running. Press Ctrl-C to exit.\n";

    while (g_running) std::this_thread::sleep_for(500ms);

    g_running = false;
    g_jobs_cv.notify_all();
    for (auto &t : watchers) if (t.joinable()) t.join();
    for (auto &w : workers) if (w.joinable()) w.join();
    pipe.stop();

    return 0;
}

