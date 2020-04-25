# -*- mode: python ; coding: utf-8 -*-

# This spec file is used with pyinstaller to generate a stand-alone unix executable that
# has needed dependencies bundled internally, so can be moved and run independently

block_cipher = None


a = Analysis(['MasterBiasMaker.py'],
             pathex=['/Users/richard/DropBox/dropbox/EWHO/Application Development/MasterBiasMaker'],
             binaries=[],
             datas=[('MainWindow.ui', '.'),
              ('ConsoleWindow.ui', '.'),
            ('PreferencesWindow.ui', '.')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='MasterBiasMaker',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True )
