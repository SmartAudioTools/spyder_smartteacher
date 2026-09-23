#!/bin/bash
# Installation de CE greffon dans le venv Spyder d'une machine SmartOS (mecanisme .pth "editable" : le greffon
# reste dans ce depot, seul un pointeur part dans site-packages). Meme interface que les autres greffons, appele
# par greffon_depot() d'installation_SmartPythonEditor.sh.
#
# Usage : installer_dans_venv.sh <python du venv Spyder> <sans_tests true|false> \
#                                <install_spyder_plugin.py> <spyder_config_set.py> <spyder.ini>
# Les deux derniers arguments ne servent pas ici (aucun reglage de Spyder a poser) : ils sont acceptes pour garder
# l'appel commun a tous les greffons.
#
# Ce que fait le greffon, ses choix et ses limites : README.txt.
# Aucune dependance a ajouter au venv : qtpy et qtawesome y sont deja (Spyder les exige). Le paquet .qcm est lu et
# corrige par le python du QCM (SMARTTEACHER_PYTHON), dans un processus a part : rien du QCM n'entre dans ce venv.
set -u
SPYDER_PYTHON="${1:?python du venv Spyder}"
SANS_TESTS="${2:-true}"
OUTIL_INSTALL="${3:?chemin de install_spyder_plugin.py}"
PLUGIN_DIR="$(cd "$(dirname "$(realpath "${BASH_SOURCE[0]}")")/.." && pwd)"

# PAS de "set -e" : error_handler.sh installe un trap ERR interactif, incompatible avec errexit.

if [ ! -x "$SPYDER_PYTHON" ]; then
  echo "ERREUR : $SPYDER_PYTHON introuvable. Installez d'abord Spyder (./installation_SmartPythonEditor.sh)." >&2
  exit 1
fi

if [ "$SANS_TESTS" = false ]; then
  echo "--- Tests du greffon (logique, pont vers le QCM, panneau, dock construit comme Spyder le fait) ---"
  SPYDER_SMARTTEACHER_PYTHON="$SPYDER_PYTHON" bash "$PLUGIN_DIR/tests/run_all.sh" || {
    echo "ERREUR : tests en echec - installation annulee." >&2; exit 1; }
fi

python3 "$OUTIL_INSTALL" "$PLUGIN_DIR" "$SPYDER_PYTHON" || {
  echo "ERREUR : l'installation du plugin a echoue." >&2; exit 1; }

echo
echo "Plugin 'SmartTeacher' installe. Dans Spyder : menu Fenetre > Panneaux > SmartTeacher, puis « Ouvrir un sujet… »."
echo "Documentation : $PLUGIN_DIR/README.txt"
