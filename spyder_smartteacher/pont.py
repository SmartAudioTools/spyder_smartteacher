# -*- coding: utf-8 -*-
"""Le pont : tourne dans le Python du QCM, jamais dans Spyder.

    <python du QCM> pont.py <dossier de modele.py>

Spyder est en PyQt5, modele.py en PySide6 (qtpy6) : les deux liaisons ne cohabitent pas dans un processus. Ce
programme ouvre le paquet .qcm une fois, puis repond ligne a ligne : une demande JSON par ligne sur stdin, une
reponse par ligne sur stdout, precedee de MARQUE (ce que modele.py ou Qt ecriraient d'autre y est ignore).
La reponse est {"ok": resultat} ou {"erreur": message, "mot_de_passe": vrai si c'est lui qui bloque}.
Les solutions et les tests restent ici : le greffon ne recoit que ce que l'eleve peut voir.
"""

import json
import os
import sys

MARQUE = "\x1ePONT "


class MotDePasse(Exception):
    pass


def titre(enonce):
    """La premiere ligne de l'enonce, sans sa mise en forme (« **Deplacements** » -> « Deplacements »)."""
    return (enonce.strip().splitlines() or [""])[0].strip("*# \t")


class Serveur:
    def __init__(self):
        from modele import MOT_DE_PASSE, charger, sauver
        from voir import mot_de_passe_en_cause
        self.MOT_DE_PASSE, self.charger, self.sauver, self.en_cause = MOT_DE_PASSE, charger, sauver, mot_de_passe_en_cause
        self.feuilles, self.mot_de_passe = {}, None

    def ouvrir(self, paquet, mot_de_passe=None):
        """Comme voir.ouvrir, sans fenetre : le mot de passe donne, sinon aucun, sinon celui des entrainements."""
        for essai in [mot_de_passe] if mot_de_passe else [None, self.MOT_DE_PASSE]:
            try:
                p = self.charger(paquet, essai)
                break
            except Exception as erreur:  # noqa: BLE001 - trie comme voir.ouvrir ce qui vient du mot de passe
                if not self.en_cause(erreur):
                    raise
        else:
            raise MotDePasse(f"{paquet} : mot de passe refusé")
        self.mot_de_passe = essai
        self.feuilles = {f.id: f for q in p.questions() for f in q.feuilles() if f.type == "code"}
        return {"titre": p.titre, "etapes": [
            {"id": f.id, "titre": titre(f.enonce), "enonce": f.enonce, "points": f.points, "aide": f.aide,
             "indices": [{"texte": i.texte, "delai": i.delai, "malus": i.malus} for i in f.indices],
             "code_initial": f.code_initial} for f in self.feuilles.values()]}

    def corriger(self, id, texte):
        """(fraction ou None, messages) : Code.corriger sur la photo, sous le nom de fichier qu'attendent les tests."""
        if id not in self.feuilles:
            raise KeyError(f"étape inconnue : {id}")
        fraction, message = self.feuilles[id].corriger(texte)
        return [fraction, [message] if message else []]

    def sauver_journal(self, chemin, journal):
        self.sauver(journal, chemin, self.mot_de_passe)

    def charger_journal(self, chemin):
        return self.charger(chemin, self.mot_de_passe)


def main():
    sys.path.insert(0, sys.argv[1])
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    serveur = Serveur()
    for ligne in sys.stdin:
        demande = json.loads(ligne)
        try:
            reponse = {"ok": getattr(serveur, demande.pop("cmd"))(**demande)}
        except MotDePasse as erreur:
            reponse = {"erreur": str(erreur), "mot_de_passe": True}
        except Exception as erreur:  # noqa: BLE001 - toute erreur est rapportee, le pont continue
            reponse = {"erreur": f"{type(erreur).__name__} : {erreur}"}
        sys.stdout.write(MARQUE + json.dumps(reponse) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
