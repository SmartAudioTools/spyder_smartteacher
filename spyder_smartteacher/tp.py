# -*- coding: utf-8 -*-
"""La logique du TP, sans Qt ni Spyder : nom du fichier de l'eleve, etapes, aide, indices, soumission, note.

Le dock (widgets/) n'en est que l'affichage, et le greffon (plugin.py) le branche sur l'editeur de Spyder.
Les choix sont consignes dans /DATA/Python/SmartTeacher/QCM/Notes/QCM - Choix de développement.txt.
"""

import os
import re
import time

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


# --- la session ----------------------------------------------------------------------------------------------

A_FAIRE, TRAITEE, SOUMISE, CORRIGEE = "à faire", "traitée", "soumise", "corrigée"


class TPFini(Exception):
    """L'action demandee n'est plus possible : etape soumise (gelee), ou TP termine."""


class Session:
    """Les etapes du TP (donnees simples lues dans le paquet par le pont) et leur etat, qui est tout le journal.

    ``correcteur(id, texte)`` -> ``(fraction des points ou None, messages)`` : la correction existante
    (Code.corriger), appelee par le pont. ``horloge`` : time.time, remplacable pour les tests des delais."""

    def __init__(self, etapes, journal=None, correcteur=None, horloge=None):
        self.etapes, self.correcteur, self.horloge = etapes, correcteur, horloge or time.time
        self.journal = journal or {"fichier": None, "fin": None, "final": None, "etapes": {}}
        for e in etapes:
            self.journal["etapes"].setdefault(e["id"], {
                "statut": A_FAIRE, "photo": None, "fraction": None, "messages": [], "repli": False,
                "aidee": False, "debloques": 0, "ouverte": None})

    def _e(self, i):
        return self.journal["etapes"][self.etapes[i]["id"]]

    # -- lecture

    @property
    def fichier(self):
        return self.journal["fichier"]

    @fichier.setter
    def fichier(self, chemin):
        self.journal["fichier"] = chemin

    @property
    def fini(self):
        return self.journal["fin"] is not None

    def statut(self, i):
        return self._e(i)["statut"]

    def messages(self, i):
        return self._e(i)["messages"]

    def repli(self, i):
        """Corrigee sur le fichier final, faute de photo."""
        return self._e(i)["repli"]

    def modifiable(self, i):
        return not self.fini and self.statut(i) != SOUMISE

    def note(self, i):
        """La formule de Question._clore : points x max(0, fraction - malus des indices debloques)."""
        e, etape = self._e(i), self.etapes[i]
        if e["fraction"] is None:
            return None
        malus = sum(ind["malus"] for ind in etape["indices"][:e["debloques"]])
        return round(etape["points"] * max(0, e["fraction"] - malus), 2)

    def total(self):
        """(points obtenus, points du TP) ; une etape sans note compte zero."""
        return (round(sum(self.note(i) or 0 for i in range(len(self.etapes))), 2),
                sum(e["points"] for e in self.etapes))

    # -- aide et indices

    def ouvrir(self, i):
        """L'etape est affichee : la premiere fois, le delai des indices commence."""
        if self._e(i)["ouverte"] is None:
            self._e(i)["ouverte"] = self.horloge()

    def voir_aide(self, i):
        self._e(i)["aidee"] = True
        return self.etapes[i]["aide"]

    def attente_indice(self, i):
        """Secondes avant le prochain indice (0 : disponible), None s'il n'y en a plus."""
        e, indices = self._e(i), self.etapes[i]["indices"]
        if e["debloques"] >= len(indices):
            return None
        self.ouvrir(i)
        return max(0, round(indices[e["debloques"]]["delai"] - (self.horloge() - e["ouverte"])))

    def debloquer_indice(self, i):
        """Le texte de l'indice suivant, ou None s'il n'est pas encore disponible (ou qu'il n'y en a plus)."""
        if self.attente_indice(i) != 0 or not self.modifiable(i):
            return None
        self._e(i)["debloques"] += 1
        return self.etapes[i]["indices"][self._e(i)["debloques"] - 1]["texte"]

    def indices_vus(self, i):
        return [ind["texte"] for ind in self.etapes[i]["indices"][:self._e(i)["debloques"]]]

    # -- photo, correction, fin

    def _corriger(self, i, texte):
        fraction, messages = self.correcteur(self.etapes[i]["id"], texte)
        self._e(i).update(fraction=fraction, messages=messages or [])

    def soumettre(self, i, texte):
        """La photo est corrigee tout de suite ; la note est gelee."""
        if not self.modifiable(i):
            raise TPFini(self.etapes[i]["id"])
        self._e(i).update(statut=SOUMISE, photo=texte)
        self._corriger(i, texte)

    def marquer(self, i, texte):
        """La photo est gardee, corrigee seulement a la fin."""
        if not self.modifiable(i):
            raise TPFini(self.etapes[i]["id"])
        self._e(i).update(statut=TRAITEE, photo=texte)

    def terminer(self, texte_final):
        """Corrige les photos des etapes traitees, et le fichier final pour celles qui n'en ont pas."""
        if self.fini:
            raise TPFini("fin")
        for i in range(len(self.etapes)):
            e = self._e(i)
            if e["statut"] == TRAITEE:
                self._corriger(i, e["photo"])
            elif e["statut"] == A_FAIRE:
                e["repli"] = True
                self._corriger(i, texte_final)
            else:
                continue
            e["statut"] = CORRIGEE
        self.journal.update(fin=self.horloge(), final=texte_final)  # le professeur peut recorriger le repli
