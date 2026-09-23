spyder_smartteacher - le sujet d'un TP dans un dock de SmartPythonEditor
=======================================================================

CE QUE LE GREFFON AJOUTE
  Un panneau "SmartTeacher" (menu Fenetre > Panneaux). L'eleve y ouvre un sujet .qcm exporte par SmartTeacher ;
  le panneau est dispose comme le lecteur .qcm en mode « une question par ecran » : en tete, le titre, la barre
  d'avancement, Precedent / Suivant, « Non traitee » (l'etape voisine encore a faire), Terminer et le total ; dessous,
  une etape (numero, statut et bareme ou note, enonce, aide et indices vus, boutons, retour de la correction).
  Les boutons :
    Soumettre             photographie le fichier de l'eleve et le fait noter par les tests de l'etape ;
    Aide                  gratuite ; elle dit OU chercher dans le cours, jamais ce qu'on y trouve ;
    Indice                apres un delai, contre un malus ;
    Marquer comme traitee pour avancer sans soumettre ;
    Terminer              corrige les etapes marquees sur leur photo, les autres sur le fichier actuel, et fige le TP.
  L'eleve code dans l'editeur de Spyder, dans UN SEUL fichier pour tout le TP (jamais un fichier par etape) ;
  F5, la console et l'explorateur de variables servent comme d'habitude.

UTILISATION
  "Ouvrir un sujet..." (barre du panneau) : choisir le .qcm, donner le mot de passe s'il est protege.
    - Le fichier de l'eleve, NOM_Prenom_TP_<sujet>.py, est cree a cote du .qcm avec le code de depart de la
      premiere etape (jamais recrase s'il existe), puis ouvert dans l'editeur.
    - Le journal (etapes soumises, notes, aides vues) est enregistre a cote, chiffre avec le mot de passe du sujet : NOM_Prenom_TP_<sujet>.journal.
      Rouvrir le sujet reprend la ou l'eleve en etait, et rouvre son fichier.
  "Choisir mon fichier..." : lier le TP a un fichier deja commence. Un "Enregistrer sous" dans Spyder deplace le
    lien avec le fichier.
  Soumettre envoie l'onglet ACTIF, enregistre puis relu sur le disque : ce qu'on voit est ce qu'on soumet. Si ce
  n'est pas le fichier du TP, une confirmation nomme les deux fichiers.

VARIABLES D'ENVIRONNEMENT
  ELEVE_NOM, ELEVE_PRENOM  nom et prenom tels que tapes (poste de l'eleve) ; a defaut, le panneau les demande.
  SMARTTEACHER_PYTHON      le Python du QCM (defaut : .../versions/SmartPython/bin/python).
  SMARTTEACHER_QCM         le dossier QCM de SmartTeacher (defaut : /DATA/Python/SmartTeacher/QCM).

ARCHITECTURE
  tp.py        la logique d'un TP (Session : etapes, statuts, aides, indices, journal), sans Qt.
  pont.py      tourne dans le Python du QCM, processus separe : ouvre le paquet, corrige, chiffre le journal.
               Le venv de Spyder n'a ni qtpy6 ni les modules du QCM, et deux liaisons Qt dans un meme processus
               entrent en conflit : rien du QCM n'est importe dans Spyder.
  client.py    cote Spyder : parle au pont en JSON, une ligne par demande.
  seance.py    relie le paquet, le fichier de l'eleve et son journal a l'editeur, sans Qt.
  spyder/      le panneau (qtpy, sur PySide6 comme Spyder), le widget du dock et le greffon.
  Les choix et leurs raisons : SmartTeacher/QCM/Notes/"QCM - Choix de developpement.txt".

TESTS
  bash tests/run_all.sh     (hors affichage, dans le venv de SmartPythonEditor ; SPYDER_SMARTTEACHER_PYTHON pour
                             un autre Python). Le dock y est construit par la meme sequence d'appels que Spyder,
                             avec une configuration de Spyder jetable (SPYDER_CONFDIR).
  Installation sur SmartOS : outils_smartos/installer_dans_venv.sh (joue les tests si sans_tests=false).

LIMITES CONNUES
  - Si le pont meurt (Python du QCM absent, plantage), il faut relancer Spyder.
  - Les images inserees dans le texte d'un enonce ne s'affichent pas encore.
  - Le projet Monkey n'a pas encore d'aides ni d'indices : les boutons restent grises.
