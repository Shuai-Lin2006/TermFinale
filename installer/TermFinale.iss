; TermFinale Windows 安装包（Inno Setup 6）
#define MyAppName "TermFinale"
#define MyAppVersion "0.6.3"
#define MyAppPublisher "Lan"
#define MyAppExeName "TermFinale.exe"

[Setup]
AppId={{8F3C2B1A-6D4E-4A7B-9C21-TERMFINALE01}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\TermFinale
DefaultGroupName=TermFinale
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=TermFinale-{#MyAppVersion}-win-x64-setup
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务："; Flags: unchecked

[Files]
Source: "..\dist\TermFinale\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\TermFinale"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\TermFinale"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 TermFinale"; Flags: nowait postinstall skipifsilent
