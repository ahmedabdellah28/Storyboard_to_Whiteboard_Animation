; ====================================================================
;  Inno Setup Script for Sketch Animation Studio
;  High-Compression Commercial Installer with Modern Wizard
; ====================================================================

#define MyAppName "Sketch Animation Studio"
#define MyAppVersion "0.7.0"
#define MyAppPublisher "Sketch Animation Studio"
#define MyAppURL "https://github.com/daslearning-org/image-to-animation-offline"
#define MyAppExeName "Img2Sketch.exe"

[Setup]
; Unique GUID for Sketch Animation Studio
AppId={{B661F148-0BD1-4317-BE5C-B153C46EA052}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}

; 64-bit Architecture
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes

; Output Configuration
OutputDir=dist\installer
OutputBaseFilename=Setup_SketchAnimationStudio_v{#MyAppVersion}

; High-Efficiency LZMA2 Ultra Compression
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern dynamic

; Privileges
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Copy all bundled application files and directories recursively from PyInstaller dist
Source: "dist\Img2Sketch\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
