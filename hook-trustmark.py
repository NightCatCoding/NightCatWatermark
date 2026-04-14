# PyInstaller hook for trustmark
# Ensures model files (.ckpt, .yaml) are bundled with the frozen app.

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = collect_data_files('trustmark', include_py_files=False)
hiddenimports = collect_submodules('trustmark')
