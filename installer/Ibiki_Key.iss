#define MyAppName "Ibiki Key"
#define MyAppVersion "0.4.0 Alpha Live Dashboard"
#define MyAppPublisher "Team Nikaido"
#define MyAppExeName "IbikiKey.exe"

[Setup]
AppId={{5E753BA6-B324-42F7-BF4D-417898615C28}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Team Nikaido\Ibiki Key
DefaultGroupName=Ibiki Key
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=Ibiki_Key-0.4.0-Alpha-Live-Dashboard-Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\assets\ibiki-key.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
CloseApplications=yes

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos:"; Flags: unchecked
Name: "startup"; Description: "Iniciar Ibiki Key con Windows"; GroupDescription: "Inicio:"; Flags: unchecked

[Files]
Source: "..\dist\Ibiki_Key_Portable\*"; DestDir: "{app}"; Excludes: "portable.flag"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Ibiki Key"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Ibiki Key"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userstartup}\Ibiki Key"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--minimized"; Tasks: startup

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir Ibiki Key"; Flags: nowait postinstall skipifsilent
