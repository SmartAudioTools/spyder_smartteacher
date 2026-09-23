#!/bin/bash
# Lance tous les tests du greffon SmartTeacher, sans serveur d'affichage.
set -e
cd "$(dirname "$0")/.."

PYTHON="${SPYDER_SMARTTEACHER_PYTHON:-/DATA/Python/SmartPython/CachyOS/versions/SmartPythonEditor/bin/python}"

export QT_QPA_PLATFORM=offscreen
# Comme le lanceur de SmartPythonEditor (install.sh du fork) : qtpy sur PySide6, la liaison de qtpy6 et du QCM.
# Impose, pas seulement par defaut : un QT_API herite du shell (constate : QT_API=qt_api) empechait qtpy de charger.
export QT_API=pyside6
export PYTHONPATH="$PWD:$PYTHONPATH"

"$PYTHON" -m unittest discover -s tests -t . -v "$@"
