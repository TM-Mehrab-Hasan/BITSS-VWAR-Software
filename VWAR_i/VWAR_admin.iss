[Setup]
AppName=VWAR
AppVersion=3.0.0
DefaultDirName={pf}\VWAR
DefaultGroupName=VWAR
OutputBaseFilename=VWAR_Installer
LicenseFile="G:\Ratul\Job\BFIN IT\Versions\BITSS VWAR\VWAR_i\license.txt"
PrivilegesRequired=admin
DisableProgramGroupPage=yes
; ✅ Allow user to choose installation directory
DisableDirPage=no
Compression=lzma
SolidCompression=yes
SetupIconFile="G:\Ratul\Job\BFIN IT\Versions\BITSS VWAR\dist\assets\VWAR.ico"
; Multi-language support
ShowLanguageDialog=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Files]
Source: "G:\Ratul\Job\BFIN IT\Versions\BITSS VWAR\dist\VWAR.exe"; DestDir: "{app}"; DestName: "VWAR.exe"; Flags: ignoreversion
Source: "G:\Ratul\Job\BFIN IT\Versions\BITSS VWAR\dist\assets\VWAR.ico"; DestDir: "{app}\assets"; Flags: ignoreversion
; YARA rules folders - CRITICAL for scanning functionality
Source: "G:\Ratul\Job\BFIN IT\Versions\BITSS VWAR\dist\assets\yara\*"; DestDir: "{app}\assets\yara"; Flags: ignoreversion recursesubdirs createallsubdirs
; Language-specific user manuals - installed in assets folder for application to find
Source: "G:\Ratul\Job\BFIN IT\Versions\BITSS VWAR\dist\assets\English copy of BITSS VWAR USER Manual.pdf"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "G:\Ratul\Job\BFIN IT\Versions\BITSS VWAR\dist\assets\French copy of BITSS VWAR USER Manual.pdf"; DestDir: "{app}\assets"; Flags: ignoreversion
; C++ monitor executable for real-time file monitoring
Source: "G:\Ratul\Job\BFIN IT\Versions\BITSS VWAR\dist\vwar_monitor\vwar_monitor.exe"; DestDir: "{app}\vwar_monitor"; DestName: "vwar_monitor.exe"; Flags: ignoreversion

[Icons]
Name: "{commondesktop}\VWAR"; Filename: "{app}\VWAR.exe"; IconFilename: "{app}\assets\VWAR.ico"
Name: "{userstartup}\VWAR"; Filename: "{app}\VWAR.exe"; IconFilename: "{app}\assets\VWAR.ico"
[Run]
; ✅ Create a scheduled task to auto-run VWAR at startup with admin rights
Filename: "schtasks"; \
  Parameters: "/Create /TN ""VWAR"" /TR """"{app}\VWAR.exe"""" /SC ONLOGON /RL HIGHEST /F"; \
  Flags: runhidden runascurrentuser; \
  StatusMsg: "Registering VWAR to run at startup with administrator access..."

; ✅ Optionally run VWAR right after install
Filename: "{app}\VWAR.exe"; Description: "Launch VWAR"; \
  Flags: nowait postinstall skipifsilent

[UninstallRun]
; ✅ Remove the scheduled task on uninstall
Filename: "schtasks"; \
  Parameters: "/Delete /TN ""VWAR"" /F"; \
  Flags: runhidden runascurrentuser; \
  StatusMsg: "Removing VWAR startup task..."

[UninstallDelete]
; ✅ Remove all runtime data folders and their contents
Type: filesandordirs; Name: "{app}\quarantine"
Type: filesandordirs; Name: "{app}\scanvault"
Type: filesandordirs; Name: "{app}\data"
Type: filesandordirs; Name: "{app}\assets"
Type: filesandordirs; Name: "{app}\vwar_monitor"
Type: filesandordirs; Name: "{app}\Backup"
; ✅ Remove any generated files
Type: files; Name: "{app}\*.log"
Type: files; Name: "{app}\*.json"
Type: files; Name: "{app}\*.tmp"
; ✅ Remove desktop and startup icons
Type: files; Name: "{commondesktop}\VWAR.lnk"
Type: files; Name: "{userstartup}\VWAR.lnk"

; [Code]
// function IsVWARRunning(): Boolean;
// begin
  // Result := FindWindowByClassName('TkTopLevel') <> 0;
// end;

// function InitializeSetup(): Boolean;
// begin
  // if IsVWARRunning() then begin
    // MsgBox('VWAR is currently running. Please close it before installing.', mbError, MB_OK);
    // Result := False;
  // end else begin
    // Result := True;
  // end;
// end;
[Code]
function IsVWARProcessRunning(): Boolean;
var
  TempFile: string;
  FileContent: AnsiString;
  ResultCode: Integer;
begin
  Result := False;
  TempFile := ExpandConstant('{tmp}\vwar_process_check.txt');

  // Run tasklist and redirect output to temp file
  if Exec('cmd.exe',
          '/C tasklist /FI "IMAGENAME eq VWAR.exe" > "' + TempFile + '"',
          '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    LoadStringFromFile(TempFile, FileContent);
    if Pos('VWAR.exe', FileContent) > 0 then
      Result := True;
  end;
end;

function InitializeSetup(): Boolean;
begin
  if IsVWARProcessRunning() then begin
    MsgBox('VWAR is currently running. Please close it before installing.', mbError, MB_OK);
    Result := False;
  end else
    Result := True;
end;

function InitializeUninstall(): Boolean;
begin
  if IsVWARProcessRunning() then begin
    MsgBox('VWAR is currently running. Please close it before uninstalling.', mbError, MB_OK);
    Result := False;
  end else
    Result := True;
end;
