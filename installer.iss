[Setup]
AppName=FSI Insight
AppVersion=1.5
AppPublisher=Fractured Systems Integration
AppCopyright=© 2025 Fractured Systems Integration
DefaultDirName={pf}\FSI Insight
DefaultGroupName=FSI Insight
OutputDir=dist
OutputBaseFilename=FSI Insight_v1.5
Compression=lzma
SolidCompression=yes
SetupIconFile=insight.ico
WizardImageFile=fsi_wizard.bmp

[Files]
Source: "C:\Users\zach.FRACTUREDSYSTEM\ITS\dist\FSI Insight.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "insight.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\FSI Insight"; Filename: "{app}\FSI Insight.exe"
Name: "{commondesktop}\FSI Insight"; Filename: "{app}\FSI Insight.exe"; Tasks: desktopicon; IconFilename: "{app}\insight.ico"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"
