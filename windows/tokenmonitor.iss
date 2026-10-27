; TokenMonitor .NET/WPF per-user installer

#define MyAppName "TokenMonitor"
#define MyAppVersion "2.4.4"
#define MyAppPublisher "Alessandro Goncalves"
#define MyAppURL "https://github.com/aleinconnext/tokenmonitor"

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={localappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=..\dist
OutputBaseFilename=TokenMonitor-{#MyAppVersion}-win
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
PrivilegesRequired=lowest
DisableDirPage=no
Uninstallable=yes

[Files]
Source: "..\windows-dotnet\bin\Release\net8.0-windows\win-x64\publish\TokenMonitor.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Token Monitor"; Filename: "{app}\TokenMonitor.exe"
Name: "{userdesktop}\Token Monitor"; Filename: "{app}\TokenMonitor.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na area de trabalho"; Flags: unchecked

[Run]
Filename: "{app}\TokenMonitor.exe"; Description: "Executar o TokenMonitor"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
