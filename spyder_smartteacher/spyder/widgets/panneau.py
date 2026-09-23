# -*- coding: utf-8 -*-
"""Le panneau du dock : les etapes, l'enonce, Aide / Indice / Soumettre / Marquer comme traitee / Terminer.

Simple affichage d'une Session (tp.py) : aucune decision n'est prise ici. Le greffon fournit deux fonctions,
``photo()`` (enregistre le fichier de l'eleve dans l'editeur et rend son texte lu sur le disque, ou None si
l'eleve renonce) et ``apres_action()`` (enregistre le journal) ; ``confirmer(question)`` est remplacable pour les
tests. Ne depend que de qtpy : il se teste hors de Spyder.
"""

from qtpy.QtCore import Qt, QTimer
from qtpy.QtWidgets import (QHBoxLayout, QLabel, QListWidget, QMessageBox, QPushButton, QSplitter, QTextBrowser,
                            QVBoxLayout, QWidget)



def _nombre(x):
    return f"{x:g}"


class PanneauTP(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.session = None
        self.photo = lambda: None
        self.apres_action = lambda: None

        self.titre = QLabel()
        self.titre.setWordWrap(True)
        self.liste = QListWidget()
        self.enonce = QTextBrowser()
        self.enonce.setOpenExternalLinks(True)
        self.retour = QTextBrowser()  # aide, indices vus, messages de la correction
        self.total = QLabel()

        self.bouton_aide = QPushButton("Aide")
        self.bouton_indice = QPushButton("Indice")
        self.bouton_soumettre = QPushButton("Soumettre")
        self.bouton_marquer = QPushButton("Marquer comme traitée")
        self.bouton_terminer = QPushButton("Terminer le TP")
        self.bouton_soumettre.setToolTip("Enregistre ton fichier et le fait corriger maintenant : la note est "
                                         "définitive.")
        self.bouton_marquer.setToolTip("Garde une photo de ton fichier pour cette étape, corrigée à la fin du TP. "
                                       "Tu peux la remplacer tant que le TP n'est pas terminé.")

        boutons = QHBoxLayout()
        for b in (self.bouton_aide, self.bouton_indice, self.bouton_soumettre, self.bouton_marquer):
            boutons.addWidget(b)
        bas = QHBoxLayout()
        bas.addWidget(self.total, 1)
        bas.addWidget(self.bouton_terminer)

        separateur = QSplitter(Qt.Vertical)
        for w in (self.liste, self.enonce, self.retour):
            separateur.addWidget(w)
        separateur.setSizes([150, 300, 150])
        disposition = QVBoxLayout(self)
        disposition.addWidget(self.titre)
        disposition.addWidget(separateur, 1)
        disposition.addLayout(boutons)
        disposition.addLayout(bas)

        self.liste.currentRowChanged.connect(self._afficher)
        self.bouton_aide.clicked.connect(self._aide)
        self.bouton_indice.clicked.connect(self._indice)
        self.bouton_soumettre.clicked.connect(self._soumettre)
        self.bouton_marquer.clicked.connect(self._marquer)
        self.bouton_terminer.clicked.connect(self._terminer)
        self.minuterie = QTimer(self, interval=1000)
        self.minuterie.timeout.connect(self.rafraichir)
        for b in (self.bouton_aide, self.bouton_indice, self.bouton_soumettre, self.bouton_marquer,
                  self.bouton_terminer):
            b.setEnabled(False)  # jusqu'au chargement d'un sujet

    def confirmer(self, question):
        return QMessageBox.question(self, "SmartTeacher", question) == QMessageBox.Yes

    # -- chargement et affichage

    def charger(self, session, titre):
        self.session = session
        self.titre.setText(f"<b>{titre}</b>")
        self.liste.blockSignals(True)
        self.liste.clear()
        self.liste.addItems([""] * len(session.etapes))
        self.liste.blockSignals(False)
        for i in range(len(session.etapes)):
            self._ligne(i)
        self.liste.setCurrentRow(0)
        self._afficher(0)  # setCurrentRow n'emet rien si la ligne 0 etait deja courante
        self.minuterie.start()

    @property
    def i(self):
        return self.liste.currentRow()

    def _ligne(self, i):
        s, etape = self.session, self.session.etapes[i]
        titre = etape.get("titre") or etape["enonce"].strip().splitlines()[0]
        note = s.note(i)
        texte = f"{i + 1}. {titre} — {s.statut(i)}"
        if note is not None:
            texte += f" — {_nombre(note)} / {_nombre(etape['points'])}"
        self.liste.item(i).setText(texte)

    def _afficher(self, i):
        if self.session is None or i < 0:
            return
        self.session.ouvrir(i)
        self.enonce.setMarkdown(self.session.etapes[i]["enonce"])
        self._retour()
        self.rafraichir()

    def _retour(self, erreur=None):
        s, i, morceaux = self.session, self.i, []
        e = s.journal["etapes"][s.etapes[i]["id"]]
        if e["aidee"] and s.etapes[i]["aide"]:
            morceaux.append(f"**Aide** : {s.etapes[i]['aide']}")
        morceaux += [f"**Indice {n}** : {texte}" for n, texte in enumerate(s.indices_vus(i), 1)]
        if s.repli(i):
            morceaux.append("*Étape ni soumise ni marquée : corrigée sur ton fichier final.*")
        morceaux += s.messages(i)
        if erreur:
            morceaux.append(f"**Erreur** : {erreur}")
        self.retour.setMarkdown("\n\n".join(morceaux))

    def rafraichir(self):
        """Etat des boutons, compte a rebours de l'indice, total ; appele chaque seconde."""
        if self.session is None or self.i < 0:
            return
        s, i = self.session, self.i
        modifiable = s.modifiable(i)
        self.bouton_aide.setEnabled(bool(s.etapes[i]["aide"]))
        attente = s.attente_indice(i) if modifiable else None
        self.bouton_indice.setEnabled(attente == 0)
        self.bouton_indice.setText("Indice" if not attente else f"Indice (dans {attente} s)")
        self.bouton_soumettre.setEnabled(modifiable)
        self.bouton_marquer.setEnabled(modifiable)
        self.bouton_terminer.setEnabled(not s.fini)
        obtenus, sur = s.total()
        self.total.setText(f"Total : {_nombre(obtenus)} / {_nombre(sur)}" + ("" if s.fini else " (étapes corrigées)"))

    # -- actions

    def _fin_action(self, erreur=None):
        for i in range(self.liste.count()):
            self._ligne(i)
        self._retour(erreur)
        self.rafraichir()
        self.apres_action()

    def _aide(self):
        self.session.voir_aide(self.i)
        self._fin_action()

    def _indice(self):
        if self.session.debloquer_indice(self.i) is not None:
            self._fin_action()

    def _photo_puis(self, action, question=None):
        """Prend la photo et la passe a ``action`` ; une erreur (pont arrete…) s'affiche au lieu de tout casser."""
        if question and not self.confirmer(question):
            return
        texte = self.photo()
        if texte is None:
            return
        try:
            action(texte)
        except Exception as erreur:  # le pont peut s'arreter ; l'eleve doit le voir, pas perdre le dock
            self._fin_action(erreur=str(erreur))
        else:
            self._fin_action()

    def _soumettre(self):
        i = self.i
        self._photo_puis(lambda texte: self.session.soumettre(i, texte),
                         f"Soumettre l'étape {i + 1} ? Elle sera corrigée maintenant et ne pourra plus être "
                         "modifiée.")

    def _marquer(self):
        i = self.i
        self._photo_puis(lambda texte: self.session.marquer(i, texte))

    def _terminer(self):
        self._photo_puis(self.session.terminer,
                         "Terminer le TP ? Les étapes marquées sont corrigées sur leur photo, les autres sur ton "
                         "fichier actuel. Plus rien ne pourra être modifié.")
