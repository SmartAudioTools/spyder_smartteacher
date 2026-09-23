# -*- coding: utf-8 -*-
"""Cote Spyder : lance le pont (pont.py) dans le Python du QCM et lui parle en JSON, une ligne par demande."""

import json
import os
import subprocess
from pathlib import Path

from spyder_smartteacher.pont import MARQUE

PYTHON_DEFAUT = "/DATA/Python/SmartPython/CachyOS/versions/SmartPython/bin/python"
QCM_DEFAUT = "/DATA/Python/SmartTeacher/QCM"
# Propres au processus de Spyder : transmises au pont, elles lui feraient charger une autre liaison Qt (qtpy6 lit
# QT_API, que le lanceur du Raspberry Pi met a pyqt6) ou les modules du venv de Spyder.
NON_TRANSMISES = ("PYTHONPATH", "PYTHONHOME", "QT_API", "QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH")


def python_qcm():
    return os.environ.get("SMARTTEACHER_PYTHON", PYTHON_DEFAUT)


def dossier_qcm():
    return os.environ.get("SMARTTEACHER_QCM", QCM_DEFAUT)


class PontErreur(Exception):
    def __init__(self, message, mot_de_passe=False):
        super().__init__(message)
        self.mot_de_passe = mot_de_passe


class Pont:
    def __init__(self, python=None, dossier=None):
        env = {k: v for k, v in os.environ.items() if k not in NON_TRANSMISES}
        self.processus = subprocess.Popen(
            [python or python_qcm(), str(Path(__file__).with_name("pont.py")), dossier or dossier_qcm()],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding="utf-8",
            env={**env, "QT_QPA_PLATFORM": "offscreen"}, cwd=dossier or dossier_qcm())

    def _appel(self, cmd, **demande):
        try:
            self.processus.stdin.write(json.dumps({"cmd": cmd, **demande}) + "\n")
            self.processus.stdin.flush()
        except (BrokenPipeError, OSError) as erreur:
            raise PontErreur(f"le pont est arrêté ({erreur})") from None
        for ligne in self.processus.stdout:
            if ligne.startswith(MARQUE):
                reponse = json.loads(ligne[len(MARQUE):])
                if "erreur" in reponse:
                    raise PontErreur(reponse["erreur"], reponse.get("mot_de_passe", False))
                return reponse["ok"]
        raise PontErreur(f"le pont s'est arrêté (code {self.processus.wait()})")

    def ouvrir(self, paquet, mot_de_passe=None):
        """{"titre", "etapes": [{id, titre, enonce, points, aide, indices, code_initial}]}."""
        return self._appel("ouvrir", paquet=str(paquet), mot_de_passe=mot_de_passe)

    def corriger(self, id, texte):
        """(fraction des points ou None, messages) : la signature qu'attend Session."""
        fraction, messages = self._appel("corriger", id=id, texte=texte)
        return fraction, messages

    def sauver_journal(self, chemin, journal):
        self._appel("sauver_journal", chemin=str(chemin), journal=journal)

    def charger_journal(self, chemin):
        return self._appel("charger_journal", chemin=str(chemin))

    def fermer(self):
        self.processus.stdin.close()
        self.processus.wait(timeout=10)
        self.processus.stdout.close()
