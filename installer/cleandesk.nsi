!include "MUI2.nsh"

!define APP_NAME "CleanDesk"
!define APP_VERSION "0.1.0"
!define COMPANY_NAME "CleanDesk"
!define INSTALL_DIR "$LOCALAPPDATA\\Programs\\CleanDesk"
!define PROJECT_ROOT ".."

Name "${APP_NAME}"
OutFile "${PROJECT_ROOT}\\dist\\CleanDesk_Setup.exe"
InstallDir "${INSTALL_DIR}"
InstallDirRegKey HKCU "Software\\${COMPANY_NAME}\\${APP_NAME}" "InstallDir"
RequestExecutionLevel user

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

Section "Install"
  SetOutPath "$INSTDIR"
  File "${PROJECT_ROOT}\\dist\\CleanDesk.exe"
  WriteUninstaller "$INSTDIR\\Uninstall.exe"
  WriteRegStr HKCU "Software\\${COMPANY_NAME}\\${APP_NAME}" "InstallDir" "$INSTDIR"

  CreateDirectory "$SMPROGRAMS\\${APP_NAME}"
  CreateShortCut "$SMPROGRAMS\\${APP_NAME}\\${APP_NAME}.lnk" "$INSTDIR\\CleanDesk.exe"
  CreateShortCut "$DESKTOP\\${APP_NAME}.lnk" "$INSTDIR\\CleanDesk.exe"
SectionEnd

Section "Uninstall"
  Delete "$DESKTOP\\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\\${APP_NAME}\\${APP_NAME}.lnk"
  RMDir "$SMPROGRAMS\\${APP_NAME}"

  Delete "$INSTDIR\\CleanDesk.exe"
  Delete "$INSTDIR\\Uninstall.exe"
  RMDir "$INSTDIR"
  DeleteRegKey HKCU "Software\\${COMPANY_NAME}\\${APP_NAME}"
SectionEnd
