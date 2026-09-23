#!/bin/bash
# Lance tous les tests du greffon SmartTeacher, sans serveur d'affichage.
set -e
cd "$(dirname "$0")/.."

PYTHON="${SPYDER_SMARTTEACHER_PYTHON:-/DATA/Python/SmartPython/CachyOS/versions/SmartPythonEditor/bin/python}"

export QT_QPA_PLATFORM=offscreen
# Comme le lanceur de SmartPythonEditor (SmartOS : Commun/scripts/qt_api_env.sh) : PySide6 s'il est dans le venv,
# PyQt6 sinon (Raspberry Pi, sans roue PySide6). Impose, jamais herite : QT_API vaut « auto » ou « qt_api » dans la
# session KDE (QtEnvironment.sh, pour SmartPython), valeurs que qtpy refuse.
QT_API=$("$PYTHON" -c "import PySide6" 2>/dev/null && echo pyside6 || echo pyqt6)
export QT_API
export PYTHONPATH="$PWD:$PYTHONPATH"

"$PYTHON" -m unittest discover -s tests -t . -v "$@"
