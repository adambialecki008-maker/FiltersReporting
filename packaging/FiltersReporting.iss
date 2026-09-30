#define MyAppName "FiltersReporting"
#define MyAppVersion "1.00"
#define MyAppPublisher "FiltersReporting"
#define MyAppExeName "FiltersReporting.exe"

[Setup]
AppId={{7D5B09AC-FA47-4FE1-AF69-17930F7972D8}

AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}

DefaultDirName={localappdata}\Programs\FiltersReporting
DefaultGroupName=FiltersReporting

DisableProgramGroupPage=yes
DisableDirPage=no

PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

UsePreviousAppDir=no

OutputDir=..\release
OutputBaseFilename=FiltersReporting-v1.00-Setup

SetupIconFile=FiltersReporting_Setup.ico

Compression=lzma2
SolidCompression=yes

WizardStyle=modern

UninstallDisplayName=FiltersReporting
UninstallDisplayIcon={app}\FiltersReporting.ico

VersionInfoVersion=1.0.0.0
VersionInfoDescription=FiltersReporting Setup
VersionInfoProductName=FiltersReporting
VersionInfoProductVersion=1.00

CloseApplications=yes
RestartApplications=no


[Languages]
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"


[Tasks]
Name: "desktopicon"; \
    Description: "Utwórz skrót na pulpicie"; \
    GroupDescription: "Dodatkowe skróty:"; \
    Flags: unchecked


[Files]
Source: "..\dist\FiltersReporting\*"; \
    DestDir: "{app}\FiltersReporting"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

Source: "..\dist\FiltersReportingCollector\*"; \
    DestDir: "{app}\FiltersReportingCollector"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

Source: "..\packaging\FiltersReporting.ico"; \
    DestDir: "{app}"; \
    Flags: ignoreversion


[Icons]
Name: "{autoprograms}\FiltersReporting"; \
    Filename: "{app}\FiltersReporting\FiltersReporting.exe"; \
    WorkingDir: "{app}\FiltersReporting"; \
    IconFilename: "{app}\FiltersReporting.ico"

Name: "{autodesktop}\FiltersReporting"; \
    Filename: "{app}\FiltersReporting\FiltersReporting.exe"; \
    WorkingDir: "{app}\FiltersReporting"; \
    IconFilename: "{app}\FiltersReporting.ico"; \
    Tasks: desktopicon


[Run]
Filename: "{app}\FiltersReporting\FiltersReporting.exe"; \
    Description: "Uruchom FiltersReporting"; \
    WorkingDir: "{app}\FiltersReporting"; \
    Flags: nowait postinstall skipifsilent


[UninstallDelete]
; Po odinstalowaniu usuń cały katalog instalacyjny.
; Dzięki temu nie zostają stare pliki po poprzednich buildach.
Type: filesandordirs; Name: "{app}"


[Code]

var
    DeleteUserData: Boolean;


procedure KillApplication(
    const ProcessName: String
);
var
    ResultCode: Integer;
begin
    Exec(
        ExpandConstant('{cmd}'),
        '/C taskkill /F /IM "' +
        ProcessName +
        '" >nul 2>&1',
        '',
        SW_HIDE,
        ewWaitUntilTerminated,
        ResultCode
    );
end;


procedure DeleteRuntimeData;
var
    RuntimeDirectory: String;
begin
    RuntimeDirectory :=
        ExpandConstant(
            '{localappdata}\FiltersReporting'
        );

    if DirExists(RuntimeDirectory) then
    begin
        DelTree(
            RuntimeDirectory,
            True,
            True,
            True
        );
    end;
end;


function PrepareToInstall(
    var NeedsRestart: Boolean
): String;
begin
    KillApplication(
        'FiltersReporting.exe'
    );

    KillApplication(
        'FiltersReportingCollector.exe'
    );

    Result := '';
end;


procedure CurUninstallStepChanged(
    CurUninstallStep: TUninstallStep
);
var
    Answer: Integer;
begin
    if CurUninstallStep = usUninstall then
    begin
        KillApplication(
            'FiltersReporting.exe'
        );

        KillApplication(
            'FiltersReportingCollector.exe'
        );

        Answer := MsgBox(
            'Czy chcesz również usunąć wszystkie dane użytkownika '
            + 'FiltersReporting?'
            + #13#10
            + #13#10
            + 'Usunięte zostaną:'
            + #13#10
            + '- baza danych i historia'
            + #13#10
            + '- konfiguracja filtrów'
            + #13#10
            + '- ustawienia aplikacji i SMTP'
            + #13#10
            + '- raporty'
            + #13#10
            + '- logi'
            + #13#10
            + '- certyfikaty OPC UA'
            + #13#10
            + #13#10
            + 'Tej operacji nie można cofnąć.'
            + #13#10
            + #13#10
            + 'Wybierz "Nie", jeśli planujesz ponownie '
            + 'zainstalować lub zaktualizować program.',
            mbConfirmation,
            MB_YESNO or MB_DEFBUTTON2
        );

        DeleteUserData :=
            Answer = IDYES;
    end;

    if CurUninstallStep = usPostUninstall then
    begin
        if DeleteUserData then
        begin
            DeleteRuntimeData;
        end;
    end;
end;