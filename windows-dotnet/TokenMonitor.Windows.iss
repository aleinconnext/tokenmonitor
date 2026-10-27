#define MyAppName "TokenMonitor"
#define MyAppVersion "2.4.2"
#define MyAppPublisher "Alessandro Gonçalves"
#define MyAppURL "https://github.com/aleinconnext/tokenmonitor"

[Setup]
AppId={{B61D2F09-6DCE-4F12-9C12-9C2C1D1B8E42}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=..\dist
OutputBaseFilename=TokenMonitor-{#MyAppVersion}-win
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest
DisableDirPage=no
UninstallDisplayIcon={app}\TokenMonitor.exe

[Files]
Source: "bin\Release\net8.0-windows\win-x64\publish\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Token Monitor"; Filename: "{app}\TokenMonitor.exe"
Name: "{userdesktop}\Token Monitor"; Filename: "{app}\TokenMonitor.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos adicionais:"

[Run]
Filename: "{app}\TokenMonitor.exe"; Description: "Executar TokenMonitor"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
