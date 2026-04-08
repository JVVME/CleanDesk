# -*- mode: python ; coding: utf-8 -*-

import pathlib
import sys

spec_path = globals().get("__file__")
if spec_path:
    project_root = pathlib.Path(spec_path).resolve().parent
else:
    project_root = pathlib.Path.cwd().resolve()
icon_path = project_root / "cleandesk" / "resources" / "icon.png"
datas = [
    (str(project_root / "cleandesk" / "resources" / "icon.png"), "cleandesk/resources"),
    (
        str(project_root / "cleandesk" / "resources" / "default_rules.json"),
        "cleandesk/resources",
    ),
]

hiddenimports = [
    "pystray._win32",
    "PIL",
    "PIL.Image",
    "plyer.platforms.win.notification",
]

block_cipher = None

a = Analysis(
    ["cleandesk_launcher.py"],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="CleanDesk",
    icon=str(icon_path),
    console=False,
    disable_windowed_traceback=False,
)
