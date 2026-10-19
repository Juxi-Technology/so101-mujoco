# 09 · Tutoriel d'utilisation complet (démarrage du bras → jeu de données → visionnage des vidéos → entraînement → déploiement)

> Manuel opérationnel de bout en bout : suivez-le une fois et vous passerez de « brancher le bras maître » à « une politique entraînée qui travaille toute seule en simulation ».
> Prérequis : l'environnement est installé selon [01](01-environment.md) et le bras maître est calibré selon [03](03-hardware-calibration.md)
> (sur cette machine : `juxi_leader` / COM124). Tous les pièges liés à l'enregistrement sont regroupés dans [07](07-troubleshooting.md).

## 0 · Préparation unique

```bash
# 本机所有 uv 命令都要先设（跨盘缓存特例，见 07）
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
```

Branchez le bras maître et vérifiez le port série (**le numéro peut changer à chaque branchement**) :

```bash
uv run --frozen python -c "from serial.tools import list_ports; print([p.device for p in list_ports.comports()])"
```

Libérez de l'espace sur le bureau : l'enregistrement ouvre **3 fenêtres** (vue principale + `wrist camera - live` + `top camera - live`).

## 1 · Échauffement en téléopération (recommandé)

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/teleoperate.py \
    --robot.type=so101_mujoco \
    --teleop.type=so101_leader_trim --teleop.port=COM124 --teleop.id=juxi_leader \
    --teleop.use_degrees=false
```

Bougez le bras maître pour vérifier que le bras simulé suit ; avant de quitter (Ctrl-C), placez le bras maître **près de la pose médiane** pour éviter un grand segment de convergence au lancement de l'enregistrement.

## 2 · Enregistrement (commande principale)

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/record.py \
    --robot.image_camera=sim_cam --robot.top_camera=top_cam \
    --teleop.type=so101_leader_trim --teleop.port=COM124 --teleop.id=juxi_leader \
    --teleop.use_degrees=false \
    --dataset.repo_id=local/so101_sim_vision \
    --dataset.root=examples/so101_mujoco/outputs/datasets/so101_sim_vision \
    --dataset.num_episodes=5 --dataset.episode_time_s=600 --dataset.reset_time_s=10 \
    --dataset.single_task="put the cube in the box" \
    --dataset.video=true --dataset.push_to_hub=false --play_sounds=false --dataset.no_stamp=true
```

Points clés (pour les autres paramètres, voir le tableau des paramètres de [06](06-record-and-replay.md)) :

| Élément | Description |
| --- | --- |
| `--dataset.root` | **root est le répertoire du jeu de données lui-même**, changez de répertoire à chaque session (un répertoire existant du même nom empêche le démarrage) |
| Valeurs par défaut injectées automatiquement | encodage vidéo `h264`, threads d'encodage `2` — `record.py` affiche deux lignes d'information au démarrage ; passer explicitement `--dataset.rgb_encoder.vcodec=...` / `--dataset.encoder_threads=...` les remplace (raison dans 07) |
| Fenêtres d'aperçu | activées par défaut (15 Hz, `--robot.preview_cameras=false` pour les désactiver ; `--robot.preview_fps` réglable) |
| `--dataset.video=true` | les images des deux caméras sont intégrées (`observation.images.wrist / top`) ; pour ne garder que la caméra de poignet, retirez `top_camera` |

## 3 · Opérations pendant l'enregistrement

| Touche | Action |
| --- | --- |
| `→` ou `n` | terminer l'épisode en cours et sauvegarder |
| `←` ou `r` | abandonner l'épisode en cours et réenregistrer sur place |
| `q` | terminer toute la session et sauvegarder le jeu de données |

- après la fin d'un épisode, **les cubes se replacent automatiquement** ; il vous suffit de ramener le bras maître à la pose de départ ; attendez de voir `Recording episode N` avant de commencer les mouvements de l'épisode suivant.
- pendant la phase de sauvegarde (quelques dizaines de secondes), la console affiche `[record.py] reset done; saving the episode + encoding videos now` —
  pendant ce temps, **les appuis sur les touches sont ignorés en toute sécurité** (une frappe accidentelle n'abîme aucun épisode) ; attendez l'apparition de la ligne `Recording episode` suivante pour agir.
- en cas d'échec d'encodage, un **retry automatique** sert de filet de sécurité (message `video encode failed ... retrying once` puis nouvelle tentative automatique après 3 secondes) ; les épisodes déjà sauvegardés ne sont jamais perdus.

## 4 · Contrôle qualité

```bash
uv run --frozen python examples/so101_mujoco/inspect_dataset.py \
    --repo-id local/so101_sim_vision \
    --root examples/so101_mujoco/outputs/datasets/so101_sim_vision
```

Comment lire la sortie :

- **les épisodes dont l'action span est entièrement à 0 (ou la pince à 0)** sont des enregistrements vides/invalides ; supprimez-les et réenregistrez ;
- **un `max |act-obs|` élevé au début de chaque épisode** correspond au segment de convergence, c'est normal ; dans la partie médiane et finale, il doit être inférieur à ~10 unités.

## 5 · Regarder les vidéos

```bash
uv run --frozen python examples/so101_mujoco/export_videos.py \
    --root examples/so101_mujoco/outputs/datasets/so101_sim_vision
```

Fichiers produits :

- `examples/so101_mujoco/outputs/videos/<数据集名>/epN_top.mp4`, `epN_wrist.mp4` — **une vidéo lisible d'un double-clic par épisode et par caméra** ;
- `examples/so101_mujoco/outputs/renders/<数据集名>_epN_dual.png` — une planche par épisode (rangée du haut : vue du dessus, rangée du bas : poignet, 6 frames échantillonnées uniformément), pour un contrôle visuel rapide (`--no-strips` pour l'ignorer).

Le jeu de données contient aussi les vidéos brutes empaquetées (plusieurs épisodes concaténés dans l'ordre dans un même fichier) :
`outputs/datasets/<数据集名>/videos/observation.images.{top,wrist}/chunk-000/file-000.mp4`.

## 6 · Relecture (facultatif)

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/replay.py \
    --dataset.repo_id=local/so101_sim_vision \
    --dataset.root=examples/so101_mujoco/outputs/datasets/so101_sim_vision --dataset.episode=0
```

## 7 · Entraînement

```bash
uv run --frozen lerobot-train \
    --policy.type=act \
    --policy.push_to_hub=false \
    --dataset.repo_id=local/so101_sim_vision \
    --dataset.root=examples/so101_mujoco/outputs/datasets/so101_sim_vision \
    --output_dir=examples/so101_mujoco/outputs/train/act_so101_sim_vision \
    --steps=100000 --batch_size=8 --save_freq=20000 --log_freq=200 \
    --num_workers=4 --wandb.enable=false --policy.device=cpu
```

| Point clé | Description |
| --- | --- |
| `--policy.type` | type de politique, **commencez par `act`** (le mieux adapté à cette taille de données/cette tâche) ; `ls src/lerobot/policies/` montre les autres choix (diffusion / smolvla / pi0, etc.) |
| `--policy.push_to_hub=false` | **obligatoire** — par défaut, il veut pousser vers HuggingFace Hub et quitte avec une erreur si `repo_id` n'est pas configuré ; pour pousser, remplacez par `--policy.repo_id=你的用户名/模型名` (nécessite d'abord `hf auth login`) |
| `--policy.device=cpu` | `cpu` sur cette machine sans GPU dédié ; sur une machine avec carte NVIDIA, supprimez ce paramètre (cuda utilisé automatiquement) |
| Produits | `output_dir/checkpoints/<步数>/` et `checkpoints/last/pretrained_model/` — le déploiement pointe vers le second ; le `train_config.json` pour reprendre l'entraînement s'y trouve aussi |
| Reprise | après une interruption, ajoutez à la commande d'origine : `--resume=true --config_path=<output_dir>/checkpoints/last/pretrained_model/train_config.json` |

**Vitesse attendue sur cette machine** : en CPU pur, environ **2 secondes/pas** (batch 2, bi-caméra 480p ; smoke test de 12 pas : loss passée de 70 à 22, direction normale).
Cette machine convient donc à une validation de la chaîne en petit nombre de pas — le `outputs/train/smoke_act` fourni avec le tutoriel est justement un produit de 12 pas ;
**pour l'entraînement officiel (ACT, de l'ordre de 100 000 pas en général), préférez une machine avec GPU, les commandes sont identiques.**

> Rappel de dépendance : l'entraînement nécessite l'extra `training` (accelerate, etc.). Si vous voyez `accelerate is required but not installed`,
> ajoutez `--extra training` à la commande d'installation de [01](01-environment.md) puis réessayez.

## 8 · Déploiement (laisser la politique travailler seule en simulation)

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/rollout.py \
    --policy.path=examples/so101_mujoco/outputs/train/act_so101_sim_vision/checkpoints/last/pretrained_model \
    --strategy.type=base \
    --robot.image_camera=sim_cam --robot.top_camera=top_cam \
    --task="put the cube in the box" --duration=30
```

| Point clé | Description |
| --- | --- |
| Paramètres caméra | `--robot.image_camera/--robot.top_camera` **doivent être identiques à ceux de l'enregistrement du jeu de données** (sim_cam + top_cam), sinon la politique ne reçoit pas les images sur lesquelles elle a été entraînée |
| `--task` | identique à `--dataset.single_task` lors de l'enregistrement |
| `--duration` | nombre de secondes avant fin automatique (le bras est renvoyé à sa pose initiale avant la déconnexion) ; `Ctrl-C` permet aussi d'arrêter en cours de route |
| Pour tester d'abord la chaîne | utilisez le modèle de démonstration fourni : `--policy.path=examples/so101_mujoco/outputs/train/smoke_act/checkpoints/last/pretrained_model` (12 pas d'entraînement, mouvements quasi aléatoires, uniquement pour valider la chaîne) |
| Déploiement en CPU pur | l'inférence de la politique présente parfois des pics de 0,5 s, avec le message `Control loop is running slower ... than the target FPS` — ça tourne en simulation mais avec des à-coups ; pas de problème sur GPU (smoke de 20 s exécuté de bout en bout, fin normale) |
| Déploiement sur robot réel | remplacez `--robot.*` par le robot réel : `--robot.type=so101_follower --robot.port=COMxx --robot.id=juxi_so101 --robot.use_degrees=false` (pensez à libérer de l'espace sur la table) |
| Autres modes | `--strategy.type=sentry / highlight / dagger / episodic` : enregistrement pendant l'exécution / sauvegarde par touche sur tampon circulaire / correction humaine dans la boucle / enregistrement par épisodes, voir `lerobot-rollout --help` |

## Annexe A · Passer à un environnement conda (facultatif)

Ce dépôt utilise par défaut un **`.venv` isolé dans le projet, géré par uv** (voir [01](01-environment.md)) ; les commandes d'exécution portent toutes
le préfixe `uv run --frozen --with mujoco`. Si vous préférez conda, **remplacez l'étape de « création de l'environnement » par les trois commandes ci-dessous**,
puis **retirez le préfixe uv de toutes les commandes** (`python examples/...` s'exécute directement), et `UV_CACHE_DIR` n'est plus nécessaire
(c'est un cas particulier du cache uv inter-disques, sans rapport avec conda) :

```bash
# 一次性：在仓库根目录建好环境（python 版本对齐 01 的 3.12）
conda create -n lerobot-sim python=3.12 -y
conda activate lerobot-sim
pip install -e .            # 安装本仓库 lerobot 及其依赖（含 torch，Windows 上 pip 默认就是 CPU 版）
pip install "mujoco==3.16"  # uv 路线用 --with mujoco 临时提供，conda 路线装成常驻依赖
```

Ensuite, par exemple, l'enregistrement devient :

```bash
python examples/so101_mujoco/record.py --robot.image_camera=sim_cam ...
```

Deux points d'attention :

1. **Alignement des versions** : `pip install -e .` laisse pip résoudre les versions, qui ne correspondent pas forcément exactement à `uv.lock` ;
   pour obtenir une combinaison strictement identique à l'environnement testé actuel, installez dans l'environnement conda selon le fichier de verrouillage avec uv :

   ```bash
   uv pip sync uv.lock --python "$(conda run -n lerobot-sim python -c 'import sys; print(sys.executable)')"
   pip install "mujoco==3.16"
   ```

2. Le cache de calibration du bras maître se trouve dans `~/.cache/huggingface/lerobot/calibration/`, indépendamment de l'environnement utilisé ; changer d'environnement ne nécessite pas de recalibrer.

## Annexe B · Aide-mémoire des pièges fréquents

| Symptôme | En bref |
| --- | --- |
| Le port série ne s'ouvre pas | listez d'abord les ports, le numéro a pu changer (étape 0) |
| La console reste silencieuse plusieurs dizaines de secondes pendant la sauvegarde | encodage en cours, c'est normal ; dès que le message `saving the episode...` apparaît, ne touchez plus aux touches |
| L'image saccade parfois pendant l'enregistrement | concurrence des ressources d'encodage dans la fenêtre de sauvegarde ; la boucle de contrôle n'est pas affectée (fiez-vous aux chiffres de cadence), détails dans 07 |
| Un crash, peut-on récupérer ? | les épisodes sauvegardés ne sont jamais perdus ; reprenez avec `record.py --resume=true ... --dataset.num_episodes=N` |
| `lerobot-train` renvoie `'repo_id' argument missing` | par défaut il veut pousser vers le Hub : ajoutez `--policy.push_to_hub=false` (pour pousser, configurez `--policy.repo_id` et faites d'abord `hf auth login`) |
| La politique ne bouge pas ou bouge n'importe comment au déploiement | vérifiez d'abord que `--robot.image_camera/--robot.top_camera` et `--task` correspondent à l'enregistrement ; vérifiez ensuite si l'entraînement n'a porté que sur très peu de pas |

Tous les pièges et solutions (y compris mémoire saturée, OOM d'encodage, épisodes vides, etc.) dans [07 · Problèmes fréquents](07-troubleshooting.md).
