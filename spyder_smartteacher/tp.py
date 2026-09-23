# -*- coding: utf-8 -*-
"""La logique du TP, sans Qt ni Spyder : nom du fichier de l'eleve, etapes, aide, indices, soumission, note.

Le dock (widgets/) n'en est que l'affichage, et le greffon (plugin.py) le branche sur l'editeur de Spyder.
Les choix sont consignes dans /DATA/Python/SmartTeacher/QCM/Notes/QCM - Choix de développement.txt.
"""

import os
import re

# Provisoires : a renommer si le poste de l'eleve fournit d'autres variables.
VAR_NOM, VAR_PRENOM = "SMARTTEACHER_NOM", "SMARTTEACHER_PRENOM"


def _propre(texte):
    """Lettres (accents compris) et chiffres gardes ; tout le reste, « _ » compris (le separateur), devient « - »."""
    return re.sub(r"(?:[^\w-]|_)+", "-", texte.strip()).strip("-")


def nom_fichier(nom, prenom, tp):
    """``NOM_Prenom_TP_xxxx.py``."""
    prenom = "-".join(p[:1].upper() + p[1:].lower() for p in _propre(prenom).split("-") if p)
    return f"{_propre(nom).upper()}_{prenom}_TP_{_propre(tp)}.py"


def eleve_depuis_env(environ=os.environ):
    """``(nom, prenom)`` lus dans l'environnement, ou None s'il en manque un."""
    nom, prenom = environ.get(VAR_NOM, "").strip(), environ.get(VAR_PRENOM, "").strip()
    return (nom, prenom) if nom and prenom else None
