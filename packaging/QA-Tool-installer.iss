#define MyAppName "QA-Tool"
#define MyAppVersion "3.7.2"
#define MyAppPublisher "QA-Tool"
#define MyAppExeName "QA-Tool.exe"

[Setup]
AppId={{A7D3E5F1-9C2B-4B6E-8F0A-1D2C3E4F5A6B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=QA-Tool-Setup-{#MyAppVersion}
SetupIconFile=..\assets\logo.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName} {#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
WizardSizePercent=110
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} {#MyAppVersion} 安装程序
ShowLanguageDialog=no

[Languages]
Name: "chinesesimp"; MessagesFile: "ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务:"
Name: "startmenu"; Description: "创建开始菜单快捷方式"; GroupDescription: "附加任务:"; Flags: unchecked

[Files]
Source: "..\build\QA-Tool.dist\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\{#MyAppExeName}"
Name: "{userprograms}\{#MyAppName}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startmenu; IconFilename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "立即运行 {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
var
  Esp32Page: TWizardPage;
  Esp32Check: TNewCheckBox;
  Esp32Desc: TNewStaticText;

procedure InitializeWizard;
begin
  Esp32Page := CreateCustomPage(wpSelectTasks, 'ESP-32 硬件拓展', '选择是否安装 ESP-32 硬件拓展功能。');
  Esp32Check := TNewCheckBox.Create(Esp32Page);
  Esp32Check.Parent := Esp32Page.Surface;
  Esp32Check.Left := 8;
  Esp32Check.Top := 8;
  Esp32Check.Width := Esp32Page.SurfaceWidth - 16;
  Esp32Check.Checked := True;
  Esp32Check.Caption := '安装 ESP-32 硬件拓展';
  Esp32Desc := TNewStaticText.Create(Esp32Page);
  Esp32Desc.Parent := Esp32Page.Surface;
  Esp32Desc.Left := 28;
  Esp32Desc.Top := 36;
  Esp32Desc.Width := Esp32Page.SurfaceWidth - 44;
  Esp32Desc.AutoSize := False;
  Esp32Desc.WordWrap := True;
  Esp32Desc.Caption := '勾选后启用设备监控与固件管理功能（支持 ESP32 系列采集与执行设备）。';
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  F: string;
  Txt: string;
  L: TStringList;
begin
  if CurStep = ssPostInstall then
  begin
    F := ExpandConstant('{app}\_internal\user_config.json');
    if not Esp32Check.Checked then
    begin
      L := TStringList.Create;
      try
        L.LoadFromFile(F);
        Txt := L.Text;
        StringChange(Txt, '"esp32_extension": true', '"esp32_extension": false');
        L.Text := Txt;
        L.SaveToFile(F);
      finally
        L.Free;
      end;
    end;
  end;
end;
