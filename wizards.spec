# -*- mode: python -*-
import PyInstaller

block_cipher = None


a = Analysis(
    ["wizards.py", "wizards.spec"],
    pathex=["/home/pudding/Projects/dinos"],
    binaries=None,
    datas=[("*.png", "."), ("*.txt", "."), ("tiles.data",'.')],
    hiddenimports=PyInstaller.utils.hooks.collect_submodules("pkg_resources"),
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
# image_tree = Tree("/src/dinosmustdie/", prefix="resource")
#shader_tree = Tree("/src/drawing", prefix="drawing")

# a.datas += image_tree
#a.datas += shader_tree

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="giant_wizards_v1",
    debug=False,
    strip=False,
    upx=True,
    console=True,
    exclude_binaries=0,
)
# dist = COLLECT(exe, a.binaries, a.zipfiles, a.datas, name="Dinosaurs Must Die!")
# dist = COLLECT(exe, a.binaries, a.zipfiles, a.datas, name="Dinosaurs Must Die!")
