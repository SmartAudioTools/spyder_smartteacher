# -*- coding: utf-8 -*-
"""La seance : un paquet ouvert par le pont, le fichier de l'eleve dans l'editeur, le journal a cote.

Sans Qt ni Spyder : le greffon injecte le pont (client.Pont), un ``editeur`` qui sait ``ouvrir(chemin)``,
``fichier_actif()`` et ``enregistrer_actif()``, et deux questions a l'eleve, ``demander_mot_de_passe(erreur)`` et
``demander_eleve()`` (-> ``(nom, prenom)``) ; les deux rendent None si l'eleve renonce.
"""

import os
from pathlib import Path

from spyder_smartteacher.client import PontErreur
from spyder_smartteacher.tp import Session, eleve_depuis_env, nom_fichier


class Seance:
    def __init__(self, pont, editeur, demander_mot_de_passe, demander_eleve, environ=os.environ):
        self.pont, self.editeur = pont, editeur
        self.demander_mot_de_passe, self.demander_eleve, self.environ = demander_mot_de_passe, demander_eleve, environ
        self.session = self.chemin_journal = None

    def _ouvrir_paquet(self, paquet):
        mot_de_passe = None
        while True:
            try:
                return self.pont.ouvrir(paquet, mot_de_passe)
            except PontErreur as erreur:
                if not erreur.mot_de_passe:
                    raise
                mot_de_passe = self.demander_mot_de_passe(str(erreur))
                if mot_de_passe is None:
                    return None

    def ouvrir(self, paquet):
        """``(session, titre)``, ou None si l'eleve renonce (mot de passe, nom).

        Le fichier ``NOM_Prenom_TP_xxxx.py`` et son journal ``.journal`` sont a cote du paquet ; le journal garde
        le fichier lie (deplace par « Enregistrer sous »), qui est rouvert s'il existe encore."""
        paquet = Path(paquet)
        eleve = eleve_depuis_env(self.environ) or self.demander_eleve()
        if not eleve:
            return None
        sujet = self._ouvrir_paquet(paquet)
        if sujet is None:
            return None
        defaut = paquet.with_name(nom_fichier(*eleve, paquet.stem))
        self.chemin_journal = defaut.with_suffix(".journal")
        journal = self.pont.charger_journal(self.chemin_journal) if self.chemin_journal.is_file() else None
        self.session = Session(sujet["etapes"], journal=journal, correcteur=self.pont.corriger)
        if not (self.session.fichier and Path(self.session.fichier).is_file()):
            if not defaut.exists():
                defaut.write_text(sujet["etapes"][0].get("code_initial") or "", encoding="utf-8")
            self.session.fichier = str(defaut)
        self.editeur.ouvrir(self.session.fichier)
        self.sauver()
        return self.session, sujet["titre"]

    def sauver(self):
        self.pont.sauver_journal(self.chemin_journal, self.session.journal)

    def photo(self, confirmer):
        """Le texte de l'onglet actif, enregistre puis relu sur le disque : ce qu'on voit est ce qu'on soumet.

        Un autre fichier que celui du TP se confirme (``confirmer(question)``) ; sans onglet, le fichier lie."""
        lie, actif = self.session.fichier, self.editeur.fichier_actif()
        if actif is None:
            return Path(lie).read_text(encoding="utf-8")
        if Path(actif) != Path(lie) and not confirmer(
                f"Tu envoies {Path(actif).name}, alors que ton fichier du TP est {Path(lie).name}. Continuer ?"):
            return None
        self.editeur.enregistrer_actif()
        return Path(actif).read_text(encoding="utf-8")

    def renomme(self, ancien, nouveau):
        """« Enregistrer sous » dans Spyder : le lien suit le fichier du TP."""
        if self.session and Path(ancien) == Path(self.session.fichier):
            self.session.fichier = str(nouveau)
            self.sauver()
