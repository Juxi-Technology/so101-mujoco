# 08 · Feuille de route

## Réalisé (directement exécutable dans ce dépôt)

| Capacité | État |
| --- | --- |
| Chargement/pilotage/vérification du rendu des modèles de simulation (3 MJCF) | ✅ |
| Téléopération au clavier (simulation / robot réel) | ✅ validé sur robot réel |
| Jumeau numérique du bras maître (bras physique → bras simulé, avec ajustement fin du zéro) | ✅ validé sur robot réel |
| Enregistrement de données (robot réel / simulation) + contrôle des épisodes + script de contrôle qualité | ✅ validé sur robot réel |
| Relecture de données (robot réel / simulation, mécanisme officiel) | ✅ validé sur robot réel |
| Tests de fumée automatisés (sans matériel, `smoke_test.py`) | ✅ 26 tests réussis |
| Jeu de données visuel bi-caméra `so101_sim_vision` (5 épisodes / 10610 frames / 353.8s) | ✅ |
| Entraînement (ACT) et déploiement de politique en simulation (`lerobot-train` / `lerobot-rollout`) | ✅ validé par test de fumée (voir [09](09-usage-tutorial.md)) |

## Prochaines étapes (par ordre de valeur)

### Phase 2 · Caméra intégrée à la scène (en cours)

**Déjà réalisé** :
- support (STEP→STL) et caméra (volume de remplacement construit d'après la fiche technique HBVCAM-F2170HD V22, 25×30×5.2mm) assemblés dans la simulation, poses ajustées par comparaison avec le robot réel via `adjust_mount.py` / `adjust_camera.py` ;
- élément `<camera>` intégré (`sim_cam`, fovy initial 49°), **la chaîne d'enregistrement visuel en simulation est opérationnelle** :
  `--robot.image_camera=sim_cam` produit un jeu de données vidéo `observation.images.wrist` (tests de fumée [5] tous réussis).

**Mise à jour du 2026-10-16** : la visée/fovy de la caméra a été réglée de façon satisfaisante (`adjust_camera.py` ajoute une **fenêtre d'image en temps réel live view**, réglage reprenable, réouverture automatique en cas de fermeture accidentelle ; et correction du bug « direction de l'objectif opposée à l'image » causé par la direction de visée d'une caméra MuJoCo = **−Z de l'élément**, détails dans [07](07-troubleshooting.md)). Le jeu de données visuel a été officiellement enregistré avec le bras maître nouvellement calibré (vidéo wrist incluse, erreur de suivi ≤ 2 unités) ✅ ;
les anciens enregistrements expérimentaux ont été nettoyés le 2026-10-16, le jeu de données officiel est unifié sous `so101_sim_vision` (bi-caméra).
**Le même jour, le robot simulé a migré vers le modèle SO-ARM100 de mujoco_menagerie** (2026-10-16) : la pince de l'ancien modèle du tutoriel ne peut pas saisir ; la pince du nouveau modèle reprend la collision CAO du robot réel et saisit de façon stable un cube de 34 mm en test ; les chaînes enregistrement/téléopération/bi-caméra/espace de travail sont toutes conservées, en attente d'une vérification par téléopération sur robot réel (notamment le signe de la direction wrist_roll).
**Restant à faire** : une fois la HBVCAM réelle connectée, faire un réglage fin par comparaison « prise de vue réelle vs rendu simulé » ;
optionnel : remplacer le volume de remplacement par le STL du corps de caméra. La configuration des caméras côté robot réel (`--robot.cameras` OpenCV) sera faite ensuite.

### Phase 3 · Scène et passage à l'échelle (en cours)

- ✅ Espace de travail intégré à la scène (2026-10-16) : plateau + cubes de trois couleurs (34mm, saisissables) + bac de rangement + caméra fixe de vue du dessus `top_cam`
  (définie dans `so101_assets.add_workspace`, outil de rendu et de vérification de l'apport `preview_workspace.py`) ; **la chaîne d'enregistrement bi-caméra (wrist+top) est opérationnelle** (`--robot.top_camera=top_cam`) ;
- **Génération automatique de données** : politiques scriptées/RL exécutées en lots toute la nuit en simulation (sans humain dans la boucle), c'est la source du « gain d'efficacité de plusieurs dizaines de fois » ;
- Randomisation du domaine visuel (textures/éclairage/oscillation caméra) en préparation du sim2real.

### Phase 4 · Entraînement et déploiement

- ✅ **Chaîne entraînement/déploiement testée** (2026-10-16) : `lerobot-train` (ACT, smoke CPU de 12 pas — environ 2 s/pas, loss en baisse normale,
  checkpoints écrits comme prévu) et `lerobot-rollout --strategy.type=base` (exécution réelle de la politique 20 s en simulation,
  retour automatique du bras à la pose initiale avant la fin) sont opérationnels ; commandes complètes, points clés et reprise d'entraînement dans [09](09-usage-tutorial.md) sections 7/8,
  le checkpoint de démonstration fourni avec le tutoriel `outputs/train/smoke_act` permet de tester directement la chaîne de déploiement ;
- l'entraînement officiel se fait sur une **machine avec GPU** (ACT / SmolVLA ; cette machine en CPU pur ne convient qu'à la validation de la chaîne en petit nombre de pas) ;
  il suffit de copier le jeu de données ou de le pousser vers un dépôt HF privé ;
- le déploiement sur robot réel passe aussi par `lerobot-rollout` (remplacer `--robot.*` par la configuration `so101_follower`).

### Long terme · sim2real

Entraînement mixte données simulées + quelques données réelles → évaluation à coût nul sur le robot réel (le taux de réussite des politiques peut être évalué de façon reproductible en simulation).
Attention : transférer directement des données purement simulées sur le robot réel (transfert zero-shot) est la voie la plus difficile ; commencez par une « boucle courte » (entraînement sur données réelles → déploiement réel),
puis ajoutez progressivement la simulation.

## Positionnement en une phrase

Pour les équipes disposant déjà d'un bras physique : la simulation = **bac à sable de développement + support de démonstration + amplificateur de données** ;
pour les clients potentiels : la simulation = **un outil d'expérience permettant de parcourir tout le flux avant l'achat**.
