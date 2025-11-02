[Setup]
AppName=VWAR Scanner
AppVersion=1.0
DefaultDirName={pf}\VWARScanner
DefaultGroupName=VWARScanner
OutputBaseFilename=VWAR_Installer
LicenseFile="G:\Ratul\Job\BFIN IT\Versions\Bitss\BITSS-VWAR-Software\VWAR_i\license.txt"
PrivilegesRequired=admin
DisableProgramGroupPage=yes
Compression=lzma
SolidCompression=yes
SetupIconFile="G:\Ratul\Job\BFIN IT\Versions\Bitss\BITSS-VWAR-Software\VWAR_i\assets\VWAR.ico"


[Files]
Source: "G:\Ratul\Job\BFIN IT\Versions\Bitss\BITSS-VWAR-Software\VWAR_i\VWAR.exe"; DestDir: "{app}"; DestName: "VWAR.exe"; Flags: ignoreversion
Source: "G:\Ratul\Job\BFIN IT\Versions\Bitss\BITSS-VWAR-Software\VWAR_i\assets\VWAR.ico"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "G:\Ratul\Job\BFIN IT\Versions\Bitss\BITSS-VWAR-Software\VWAR_i\Vwar User Manual.pdf"; DestDir: "{app}"; Flags: ignoreversion
; Use the repository's top-level 'vwar_monitor' folder as the source for the
; native executable rather than a hard-coded absolute path.
Source: "G:\Ratul\Job\BFIN IT\Versions\Bitss\BITSS-VWAR-Software\VWAR_i\vwar_monitor\vwar_monitor.exe"; DestDir: "{app}\vwar_monitor"; DestName: "vwar_monitor.exe"; Flags: ignoreversion

[Icons]
Name: "{commondesktop}\VWAR Scanner"; Filename: "{app}\VWAR.exe"; IconFilename: "{app}\assets\VWAR.ico"
Name: "{userstartup}\VWAR Scanner"; Filename: "{app}\VWAR.exe"; IconFilename: "{app}\assets\VWAR.ico"
[Run]
; ✅ Create a scheduled task to auto-run VWAR at startup with admin rights
Filename: "schtasks"; \
  Parameters: "/Create /TN ""VWARScanner"" /TR """"{app}\VWAR.exe"""" /SC ONLOGON /RL HIGHEST /F"; \
  Flags: runhidden runascurrentuser; \
  StatusMsg: "Registering VWAR to run at startup with administrator access..."

; ✅ Optionally run VWAR right after install
Filename: "{app}\VWAR.exe"; Description: "Launch VWAR Scanner"; \
  Flags: nowait postinstall skipifsilent

[UninstallRun]
; ✅ Remove the scheduled task on uninstall
Filename: "schtasks"; \
  Parameters: "/Delete /TN ""VWARScanner"" /F"; \
  Flags: runhidden runascurrentuser; \
  StatusMsg: "Removing VWAR startup task..."

; [Code]
// function IsVWARRunning(): Boolean;
// begin
  // Result := FindWindowByClassName('TkTopLevel') <> 0;
// end;

// function InitializeSetup(): Boolean;
// begin
  // if IsVWARRunning() then begin
    // MsgBox('VWAR Scanner is currently running. Please close it before installing.', mbError, MB_OK);
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
    MsgBox('VWAR Scanner is currently running. Please close it before installing.', mbError, MB_OK);
    Result := False;
  end else
    Result := True;
end;

function InitializeUninstall(): Boolean;
begin
  if IsVWARProcessRunning() then begin
    MsgBox('VWAR Scanner is currently running. Please close it before uninstalling.', mbError, MB_OK);
    Result := False;
  end else
    Result := True;
end;
