#ifndef AppVersion
  #define AppVersion "0.3.0-alpha.2"
#endif
#ifndef SourceDir
  #define SourceDir "..\dist\StarForge"
#endif
#ifndef OutputDir
  #define OutputDir "..\dist"
#endif

[Setup]
AppId={{E2E50D71-5EA6-4E54-BE57-58E2B9F9A796}
AppName=StarForge
AppVersion={#AppVersion}
AppPublisher=Eclipse Content Engine
AppPublisherURL=https://github.com/eclipse-content-engine/StarForge
AppSupportURL=https://github.com/eclipse-content-engine/StarForge/issues
DefaultDirName={localappdata}\Programs\StarForge
DefaultGroupName=StarForge
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
OutputDir={#OutputDir}
OutputBaseFilename=StarForge-{#AppVersion}-Windows-Setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\StarForge.exe

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\StarForge"; Filename: "{app}\StarForge.exe"
Name: "{autodesktop}\StarForge"; Filename: "{app}\StarForge.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Run]
Filename: "{app}\StarForge.exe"; Description: "Launch StarForge"; Flags: nowait postinstall skipifsilent
