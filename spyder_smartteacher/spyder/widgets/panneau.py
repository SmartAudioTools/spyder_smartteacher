# -*- coding: utf-8 -*-
"""Le panneau du dock, dispose comme le lecteur .qcm en mode « question » (modele.Paquet) : une entete (titre, barre
d'avancement, navigation, Terminer, total), puis une etape par ecran (numero et bareme, enonce, aide et indices vus,
Soumettre / Marquer comme traitee / Aide / Indice, retour de la correction).

Simple affichage d'une Session (tp.py) : aucune decision n'est prise ici. Le greffon fournit deux fonctions,
``photo()`` (enregistre le fichier de l'eleve dans l'editeur et rend son texte lu sur le disque, ou None si
l'eleve renonce) et ``apres_action()`` (enregistre le journal) ; ``confirmer(question)`` est remplacable pour les
tests. Ne depend que de qtpy : il se teste hors de Spyder. Le lecteur n'est pas importe (autre Python, autre venv :
voir pont.py) ; ses couleurs et ses libelles sont repris ici.
"""

from qtpy.QtCore import Qt, QTimer
from qtpy.QtWidgets import (QHBoxLayout, QLabel, QMessageBox, QProgressBar, QPushButton,
                            QScrollArea, QVBoxLayout, QWidget)

from spyder_smartteacher.tp import A_FAIRE


def _nombre(x):
    return f"{x:g}"


def _points(p):
    return f"{p:g} point" + ("s" if p >= 2 else "")  # modele.points_txt


def _texte():
    """Un texte Markdown qui passe a la ligne, selectionnable, liens ouverts dans le navigateur."""
    t = QLabel()
    t.setTextFormat(Qt.MarkdownText)
    t.setWordWrap(True)
    t.setOpenExternalLinks(True)
    t.setTextInteractionFlags(Qt.TextBrowserInteraction)
    return t


# Les couleurs claires du lecteur, quel que soit le theme de Spyder (sombre par defaut : texte blanc sur #19232D,
# difficile a lire pour un enonce). Fond : modele.fond_sujet sous la palette claire de Breeze, a mi-chemin entre
# la fenetre (#eff0f1) et les champs (#fcfcfc). Feuille locale au panneau : elle l'emporte sur celle de Spyder.
STYLE = """
#panneauTP, #panneauTP QWidget { background: #f5f6f6; color: #232627; }
#panneauTP QScrollArea { border: none; border-top: 1px solid #c0c0c0; }  /* separe l'entete de l'etape */
#panneauTP QPushButton { background: #fcfcfc; border: 1px solid #b0b0b0; border-radius: 3px; padding: 3px 8px; }
#panneauTP QPushButton:hover { border-color: #3daee9; }
#panneauTP QPushButton:pressed { background: #e3e5e7; }
#panneauTP QPushButton:disabled { background: #f0f0f0; color: #a0a0a0; border-color: #d0d0d0; }
"""


class PanneauTP(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.session, self.i = None, 0
        self.photo = lambda: None
        self.apres_action = lambda: None
        self.setObjectName("panneauTP")
        self.setAttribute(Qt.WA_StyledBackground)  # sans quoi une sous-classe de QWidget ignore son fond
        self.setStyleSheet(STYLE)

        # -- entete : titre et avancement, navigation et Terminer, total
        self.titre = _texte()
        self.barre_avancement = QProgressBar()  # modele.barre("avancement réponses", "vert")
        self.barre_avancement.setRange(0, 100)
        self.barre_avancement.setFormat("avancement réponses")
        self.barre_avancement.setAlignment(Qt.AlignCenter)
        self.barre_avancement.setFixedSize(180, 22)
        self.barre_avancement.setStyleSheet(
            "QProgressBar { border: 1px solid #a0a0a0; border-radius: 4px; background: #f2f2f2; color: #707070;"
            " font-style: italic; } QProgressBar::chunk { background: #92d050; border-radius: 3px; }")
        haut = QHBoxLayout()
        haut.addWidget(self.titre, 1)
        haut.addWidget(self.barre_avancement, 0, Qt.AlignTop)

        self.precedent, self.suivant = QPushButton("Précédent"), QPushButton("Suivant")
        self.prec_libre, self.suiv_libre = QPushButton("◀ Non traitée"), QPushButton("Non traitée ▶")
        self.bouton_terminer = QPushButton("Terminer")
        police = self.bouton_terminer.font()
        police.setBold(True)  # comme dans le lecteur : le seul bouton sans retour se distingue
        self.bouton_terminer.setFont(police)
        navigation = QHBoxLayout()
        navigation.addWidget(self.precedent)
        navigation.addWidget(self.suivant)
        navigation.addSpacing(18)  # deux groupes : l'etape voisine, puis la voisine encore a traiter
        navigation.addWidget(self.prec_libre)
        navigation.addWidget(self.suiv_libre)
        navigation.addStretch()
        navigation.addWidget(self.bouton_terminer)
        self.total = QLabel()

        entete = QVBoxLayout()
        entete.setContentsMargins(9, 9, 9, 9)
        entete.addLayout(haut)
        entete.addLayout(navigation)
        entete.addWidget(self.total)

        # -- l'etape courante
        self.rang, self.gris = QLabel(), QLabel()
        tete = QHBoxLayout()
        tete.addWidget(self.rang)
        tete.addStretch()
        tete.addWidget(self.gris)
        self.enonce, self.zone_aide, self.retour = _texte(), _texte(), _texte()
        self.bouton_soumettre = QPushButton("Soumettre")
        self.bouton_marquer = QPushButton("Marquer comme traitée")
        self.bouton_aide, self.bouton_indice = QPushButton("Aide (gratuite)"), QPushButton("Indice")
        self.bouton_soumettre.setToolTip("Enregistre ton fichier et le fait corriger maintenant : la note est "
                                         "définitive.")
        self.bouton_marquer.setToolTip("Garde une photo de ton fichier pour cette étape, corrigée à la fin du TP. "
                                       "Tu peux la remplacer tant que le TP n'est pas terminé.")
        self.bouton_aide.setToolTip("Une piste pour démarrer, sans perdre de points.")
        barre = QHBoxLayout()
        barre.addWidget(self.bouton_soumettre)
        barre.addWidget(self.bouton_marquer)
        barre.addStretch()  # l'aide et l'indice a l'ecart des boutons qui rendent la copie
        barre.addWidget(self.bouton_aide)
        barre.addWidget(self.bouton_indice)

        page = QWidget()
        d = QVBoxLayout(page)
        d.setContentsMargins(9, 6, 9, 10)
        d.addLayout(tete)
        for w in (self.enonce, self.zone_aide):
            d.addWidget(w)
        d.addLayout(barre)
        d.addWidget(self.retour)
        d.addStretch()
        defilement = QScrollArea()
        defilement.setWidget(page)
        defilement.setWidgetResizable(True)

        disposition = QVBoxLayout(self)
        disposition.setContentsMargins(0, 0, 0, 0)
        disposition.setSpacing(0)
        disposition.addLayout(entete)
        disposition.addWidget(defilement, 1)

        self.precedent.clicked.connect(lambda: self.aller(self.i - 1))
        self.suivant.clicked.connect(lambda: self.aller(self.i + 1))
        self.prec_libre.clicked.connect(lambda: self.aller(self._voisine(-1)))
        self.suiv_libre.clicked.connect(lambda: self.aller(self._voisine(1)))
        self.bouton_aide.clicked.connect(self._aide)
        self.bouton_indice.clicked.connect(self._indice)
        self.bouton_soumettre.clicked.connect(self._soumettre)
        self.bouton_marquer.clicked.connect(self._marquer)
        self.bouton_terminer.clicked.connect(self._terminer)
        self.minuterie = QTimer(self, interval=1000)
        self.minuterie.timeout.connect(self.rafraichir)
        for b in self.findChildren(QPushButton):
            b.setEnabled(False)  # jusqu'au chargement d'un sujet

    def confirmer(self, question):
        return QMessageBox.question(self, "SmartTeacher", question) == QMessageBox.Yes

    # -- chargement et navigation

    def charger(self, session, titre):
        self.session = session
        self.titre.setText(f"### {titre}")
        self.aller(0)
        self.minuterie.start()

    def aller(self, i):
        if self.session is None or i is None or not 0 <= i < len(self.session.etapes):
            return
        self.i = i
        self.session.ouvrir(i)
        self.rang.setText(f"<b>Étape n°{i + 1}</b>")
        self.enonce.setText(self.session.etapes[i]["enonce"])
        self._etape()

    def _voisine(self, sens):
        """Rang de l'etape suivante (``sens`` = 1) ou precedente (-1) encore a faire, ou None."""
        fin = len(self.session.etapes) if sens > 0 else -1
        return next((n for n in range(self.i + sens, fin, sens) if self.session.statut(n) == A_FAIRE), None)

    def _etape(self, erreur=None):
        """Ce qui change quand l'etape change d'etat : bareme ou note, aide et indices vus, retour."""
        s, i = self.session, self.i
        etape, note = s.etapes[i], s.note(i)
        points = _points(etape["points"]) if note is None else f"{_nombre(note)} / {_nombre(etape['points'])}"
        self.gris.setText(f"<small style='color:gray'>{s.statut(i)} — {points}</small>")
        vus = [f"**Aide** : {etape['aide']}"] if s.journal["etapes"][etape["id"]]["aidee"] and etape["aide"] else []
        vus += [f"**Indice {n}** : {texte}" for n, texte in enumerate(s.indices_vus(i), 1)]
        self.zone_aide.setText("\n\n".join(vus))
        self.zone_aide.setVisible(bool(vus))
        retour = ["*Étape ni soumise ni marquée : corrigée sur ton fichier final.*"] if s.repli(i) else []
        retour += s.messages(i) + ([f"**Erreur** : {erreur}"] if erreur else [])
        self.retour.setText("\n\n".join(retour))
        self.retour.setVisible(bool(retour))
        self.rafraichir()

    def rafraichir(self):
        """Etat des boutons, compte a rebours de l'indice, avancement, total ; appele chaque seconde."""
        if self.session is None:
            return
        s, i, n = self.session, self.i, len(self.session.etapes)
        modifiable = s.modifiable(i)
        self.precedent.setEnabled(i > 0)
        self.suivant.setEnabled(i < n - 1)
        self.prec_libre.setEnabled(self._voisine(-1) is not None)
        self.suiv_libre.setEnabled(self._voisine(1) is not None)
        self.bouton_aide.setEnabled(bool(s.etapes[i]["aide"]))
        attente = s.attente_indice(i) if modifiable else None
        self.bouton_indice.setEnabled(attente == 0)
        self.bouton_indice.setText("Indice" if not attente else f"Indice (dans {attente} s)")
        self.bouton_soumettre.setEnabled(modifiable)
        self.bouton_marquer.setEnabled(modifiable)
        self.bouton_terminer.setEnabled(not s.fini)
        self.barre_avancement.setValue(round(100 * sum(s.statut(k) != A_FAIRE for k in range(n)) / n))
        obtenus, sur = s.total()
        self.total.setText(f"Total : {_nombre(obtenus)} / {_nombre(sur)}" + ("" if s.fini else " (étapes corrigées)"))

    # -- actions

    def _fin_action(self, erreur=None):
        self._etape(erreur)
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
