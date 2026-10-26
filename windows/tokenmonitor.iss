; ----------------------------------------------------------------------
; TokenMonitor-<versão>-win.exe  –  Instalação "um-clique"
; ----------------------------------------------------------------------

#define MyAppName "TokenMonitor"
#define MyAppVersion "2.4.0"                ; ← altere conforme a tag
#define MyAppPublisher "Alessandro Gonçalves"
#define MyAppURL "https://github.com/aleinconnext/tokenmonitor"

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={pf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputBaseFilename={#MyAppName}-{#MyAppVersion}-win
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64
PrivilegesRequired=lowest
DisableDirPage=no
LicenseFile=..\LICENSE

[Files]
; Executável gerado pelo PyInstaller
Source: "..\dist\tokenmonitor\tokenmonitor.exe"; DestDir: "{app}"; Flags: ignoreversion

; GTK-runtime – será extraído em {app}\gtk
Source: "gtk\*"; DestDir: "{app}\gtk"; Flags: recursesubdirs createallsubdirs

; Imagens e banner
Source: "..\docs\*"; DestDir: "{app}\docs"; Flags: recursesubdirs createallsubdirs

; Ícone do programa
Source: "..\packaging\tokenmonitor.svg"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Token Monitor"; Filename: "{app}\tokenmonitor.exe"
Name: "{commondesktop}\Token Monitor"; Filename: "{app}\tokenmonitor.exe"; Tasks: desktopicon

[Run]
; Cria a pasta de configuração em %APPDATA%
Filename: "cmd.exe"; Parameters: "/c md ""%APPDATA%\tokenmonitor"""; Flags: runhidden

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
