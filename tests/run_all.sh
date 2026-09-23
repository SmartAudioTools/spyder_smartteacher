#!/bin/bash
# Lance tous les tests du greffon SmartTeacher, sans serveur d'affichage.
set -e
cd "$(dirname "$0")/.."

PYTHON="${SPYDER_SMARTTEACHER_PYTHON:-/DATA/Python/SmartPython/CachyOS/versions/SmartPythonEditor/bin/python}"

export QT_QPA_PLATFORM=offscreen
export PYTHONPATH="$PWD:$PYTHONPATH"

"$PYTHON" -m unittest discover -s tests -t . -v "$@"
