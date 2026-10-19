# 06 · Enregistrement et relecture de données

## Modèle de commande d'enregistrement

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'

# 录真机（主动臂 → 真机从动臂）
uv run --frozen --with mujoco python examples/so101_mujoco/record.py \
    --robot.type=so101_follower --robot.port=COM172 --robot.id=juxi_so101 \
    --robot.use_degrees=false --robot.max_relative_target=10 \
    --teleop.type=so101_leader_trim --teleop.port=COM163 --teleop.id=juxi_leader \
    --teleop.use_degrees=false \
    --dataset.repo_id=local/juxi_so101_teleop \
    --dataset.root=examples/so101_mujoco/outputs/datasets/real_run1 \
    --dataset.num_episodes=5 --dataset.episode_time_s=600 --dataset.reset_time_s=10 \
    --dataset.single_task="pick up the cube" \
    --dataset.video=false --dataset.push_to_hub=false --play_sounds=false --dataset.no_stamp=true

# 录仿真（主动臂 → 仿真从动臂）
#   把 --robot.* 换成: --robot.type=so101_mujoco
# 录仿真（键盘控制）
#   把 --teleop.* 换成: --teleop.type=so101_keyboard --teleop.rate=150
```

## Paramètres clés (les pièges à éviter)

| Paramètre | Description |
| --- | --- |
| `--dataset.root` | **root est le répertoire du jeu de données lui-même** (pas un répertoire parent concaténé avec repo_id) ; changez de répertoire à chaque enregistrement |
| `--dataset.repo_id` | en enregistrement local, ce n'est qu'un identifiant ; un vrai `用户名/名字` ne sera nécessaire que lors d'un futur push vers le Hub |
| `--dataset.no_stamp=true` | pas de suffixe d'horodatage, le répertoire/le nom reste stable ; pour réenregistrer sous le même nom, supprimez d'abord l'ancien répertoire |
| `--dataset.episode_time_s` | **limite supérieure** d'un épisode (sécurité) ; en usage normal, terminez plus tôt avec `→` |
| `--dataset.reset_time_s` | temps de remise en position non enregistré entre les épisodes ; pendant ce temps, le bras maître continue de piloter le bras esclave en temps réel. **En enregistrement simulé, les cubes sont automatiquement téléportés à leur position initiale au début de cette phase** (voir ci-dessous) |
| `--dataset.video` | à activer uniquement si des données caméra sont nécessaires (obligatoire à true pour les jeux de données visuels ; le repli sur pyav a été vérifié fonctionnel) |
| `--dataset.rgb_encoder.vcodec` | encodeur vidéo. **Sur cette machine, l'enregistrement bi-caméra utilise `h264`** : `record.py` l'injecte désormais par défaut (l'encodeur amont par défaut libsvtav1 provoque un échec d'allocation mémoire et un crash de toute la session lorsqu'il ouvre deux encodages simultanément — voir [07](07-troubleshooting.md)) ; si vous le passez explicitement, il n'est plus injecté |
| `--dataset.encoder_threads` | nombre de threads d'encodage. **`record.py` injecte 2 par défaut** : utiliser tous les cœurs rend la simulation visiblement saccadée pendant la sauvegarde (voir [07](07-troubleshooting.md)) ; en limitant chaque encodage à 2 threads, la simulation reste fluide pendant la sauvegarde ; si vous le passez explicitement, il n'est plus injecté |
| `--dataset.push_to_hub` | sur cette machine, la connexion directe à HF nécessite un proxy ; gardez false pour l'instant et poussez manuellement après l'enregistrement |

## Touches de contrôle des épisodes (globales, actives pendant tout l'enregistrement)

| Touche | Action |
| --- | --- |
| `→` ou `n` | terminer l'épisode en cours (**sauvegarde**) |
| `←` ou `r` | abandonner l'épisode en cours et **réenregistrer sur place** (à utiliser si un épisode ne convient pas, sans redémarrer la session) |
| `q` | terminer toute la session et sauvegarder le jeu de données (**recommandé**) |
| `Esc` | identique à `q` (déconnecte aussi la téléopération au clavier ; la sortie propre a été vérifiée, mais préférez `q`) |

**Conseil d'utilisation** : avant de lancer l'enregistrement, placez le bras maître près de la pose médiane (pour éviter d'enregistrer le segment de convergence où le bras simulé/réel « se précipite » au premier instant) ; après le lancement, restez immobile une seconde avant de commencer à bouger.

## Réinitialisation automatique de la scène en enregistrement simulé

Lors d'un enregistrement sur robot réel, la phase « Reset the environment » vous demande de replacer manuellement les cubes. En simulation, le lanceur d'enregistrement (`record.py`) **téléporte automatiquement les trois cubes à leur position d'origine** au début de cette phase (en remettant aussi leur vitesse à zéro) ; ainsi, après avoir terminé chaque épisode avec `→`, il vous suffit de ramener le bras maître à la pose de départ, les cubes se replacent automatiquement et l'épisode suivant commence avec une scène initiale fixe. Le bras esclave réel n'a pas ce comportement (placement manuel comme d'habitude) ; `teleoperate.py`/`replay.py` ne sont pas concernés non plus.

## Contrôle qualité après enregistrement

```bash
uv run --frozen python examples/so101_mujoco/inspect_dataset.py \
    --repo-id local/so101_sim_vision \
    --root examples/so101_mujoco/outputs/datasets/so101_sim_vision
```

Affiche, pour chaque épisode, le nombre de frames, la durée, l'amplitude des actions des six articulations et l'erreur de suivi :

- **les épisodes avec action span = 0** sont des enregistrements vides (personne n'a bougé) ; supprimez-les et réenregistrez ;
- **un |action−obs| élevé au début** correspond au segment de convergence (normal) ; dans la partie médiane et finale, il est généralement < 10 unités.

## Enregistrer des données « avec images » en simulation (caméra wrist)

Le robot simulé permet d'enregistrer dans le jeu de données la caméra de poignet de la scène (`sim_cam`) comme observation d'image :

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/record.py \
    --robot.image_camera=sim_cam --robot.top_camera=top_cam \
    --teleop.type=so101_leader_trim --teleop.port=COM124 --teleop.id=juxi_leader \
    --teleop.use_degrees=false \
    --dataset.repo_id=local/so101_sim_vision \
    --dataset.root=examples/so101_mujoco/outputs/datasets/so101_sim_vision \
    --dataset.num_episodes=5 --dataset.episode_time_s=600 --dataset.reset_time_s=10 \
    --dataset.single_task="pick up the cube" \
    --dataset.video=true --dataset.push_to_hub=false --play_sounds=false --dataset.no_stamp=true
```

Points clés : `--robot.image_camera=sim_cam` (nom de la caméra) + `--dataset.video=true` (les images passent par l'encodage vidéo ; le repli sur pyav a été vérifié fonctionnel). La caractéristique `observation.images.wrist` (480×640×3) apparaît dans les features du jeu de données. La résolution et la fréquence d'images se règlent avec `--robot.image_width/--robot.image_height/--robot.image_fps`.
Lorsque la fenêtre est ouverte (`onscreen=true`, par défaut), en plus de la fenêtre de vue principale, **une fenêtre d'aperçu en temps réel est ouverte pour chaque caméra** (poignet / vue du dessus, avec une étiquette en haut à gauche de la fenêtre) ; pendant l'enregistrement, vous pouvez voir directement si les deux flux sont corrects ; si vous n'en voulez pas, ajoutez `--robot.preview_cameras=false`. Les fenêtres d'aperçu se rafraîchissent par défaut à **15 Hz** (`--robot.preview_fps` réglable) — ce sont des affichages d'état qui n'ont pas besoin de suivre les 50 Hz de la fenêtre principale, ce qui réduit beaucoup la charge de rendu avec 3 fenêtres à l'écran.

**Scène et caméra de vue du dessus (depuis le 2026-10-16)** : la scène simulée intègre un espace de travail — plateau, cubes de trois couleurs (34 mm), bac de rangement (voir `so101_assets.add_workspace`, la disposition peut être affinée par rendu avec `preview_workspace.py`) ; plus une caméra fixe de vue du dessus `top_cam` (le haut de l'image = direction opposée au bras robotique). Ajouter `--robot.top_camera=top_cam` enregistre la vue du dessus dans `observation.images.top` (enregistrement simultané des deux caméras) ; pour ne garder que la caméra de poignet, retirez ce paramètre. L'encodage vidéo après la fin d'un épisode traite les deux flux simultanément ; un temps d'attente un peu plus long est normal.

## Relecture

```bash
# 仿真空回放（窗口里看轨迹重演）
uv run --frozen --with mujoco python examples/so101_mujoco/replay.py \
    --dataset.repo_id=local/so101_sim_vision \
    --dataset.root=examples/so101_mujoco/outputs/datasets/so101_sim_vision --dataset.episode=0

# 真机回放（同款机制，注意周围环境与录制时一致）
uv run --frozen --with mujoco python examples/so101_mujoco/replay.py \
    --robot.type=so101_follower --robot.port=COM172 --robot.id=juxi_so101 \
    --robot.use_degrees=false --robot.max_relative_target=10 \
    --dataset.repo_id=local/juxi_so101_teleop \
    --dataset.root=examples/so101_mujoco/outputs/datasets/juxi_teleop_run1 --dataset.episode=0
```

> Le point d'entrée officiel `lerobot-replay` ne charge pas les plugins de ce projet ; l'utiliser directement renvoie `invalid choice: 'so101_mujoco'` —
> passez donc toujours par le lanceur `replay.py`.

## Format et emplacement du jeu de données

Le jeu de données est au format LeRobotDataset v3 : `action` et `observation.state` sont tous deux des vecteurs à 6 dimensions
(`shoulder_pan.pos … gripper.pos`), identiques aux jeux de données réels officiels, et peuvent être directement mélangés pour l'entraînement.

```
examples/so101_mujoco/outputs/datasets/
└── juxi_teleop_run1/   真机键盘遥操（1 回合 / 2430 帧 / 81s）✅ 保留的真机数据

> 2026-10-16 清理：旧的仿真录制（`sim_run2`、`sim_vision_demo`、`sim_vision_run1/2/3`）
> 已全部删除。**正式数据集 `so101_sim_vision`（双相机 / 5 回合 / 10610 帧 / 353.8s / h264）
> 已于当晚录成 ✅**；每回合单机视频导出在 `outputs/videos/so101_sim_vision/`，
> 双相机预览拼图在 `outputs/renders/sim_vision_epN_dual.png`。
```

## Journal des tests de cette session (2026-10-15)

| Session | Contenu | Résultat |
| --- | --- | --- |
| run1 robot réel | enregistrement du robot réel en téléopération au clavier | 1 épisode de 81 s, amplitude des six articulations 75~140 unités, stable à 30 Hz |
| relecture robot réel | relecture du même épisode | 2430 frames reproduites intégralement, aucune anomalie |
| run2 simulation | enregistrement simulé en téléopération bras maître | 5 épisodes, 157 s, erreur de suivi des ep1~4 < 12 unités |
| relecture simulation ep1 | rejeu dans la fenêtre | trajectoire conforme aux manipulations (confirmé) |

## Tests complémentaires (2026-10-16)

| Session | Contenu | Résultat |
| --- | --- | --- |
| Nouveau bras maître (COM124) | recalibration (nouveau bras/nouveaux servomoteurs) | ✅ calibration réussie ; la compensation de zéro de `so101_leader_trim` s'adapte automatiquement à la nouvelle calibration |
| run1 vision | enregistrement simulé en téléopération bras maître (avec images) | 2 épisodes / 3177 frames / 106 s @ 29.97Hz ; erreur de suivi ≤ 2 unités sur toute la durée (seulement 0,5 s de convergence à la première frame) ; vidéo `observation.images.wrist` intégrée au jeu de données et vérifiée par décodage ✅ |
| run2 vision | reprise d'enregistrement bi-caméra (`--resume`) | ep0 (2776 frames / 92.6 s) intact ; lors de la sauvegarde de ep1, l'encodeur libsvtav1 a provoqué une OOM et le crash de toute la session → encodeur changé pour h264 (injecté par défaut par `record.py`) et test de bout en bout réussi (2 épisodes × double encodage) ; les résidus ont été nettoyés, le réenregistrement officiel passe au run3 |
| run3 vision | enregistrement officiel bi-caméra (h264) | 1re session : ep0 (185.2 s / 5554 frames) + ep1 (72.8 s / 2186 frames) intacts et contrôle qualité réussi ; pendant la pause d'encodage entre sessions, des appuis répétés sur `→` ont déclenché un crash sur épisode vide (mécanisme et protection dans [07](07-troubleshooting.md)) → reprise de session pour enregistrer les épisodes restants (plan de 5 épisodes) |
| Premier essai d'enregistrement officiel (so101_sim_vision) | bi-caméra (h264 + 2 threads + fenêtres d'aperçu à 15 Hz) | lors de la sauvegarde de ep0 (82.3 s / 2469 frames), échec d'allocation mémoire de l'encodeur et crash de toute la session (commit système presque saturé, voir [07](07-troubleshooting.md)) → ajout d'un **retry automatique en cas d'échec d'encodage** et de la **mise en sourdine de la console** (tous deux vérifiés efficaces, 26 tests de fumée passés) ; réenregistrement officiel après redémarrage de la machine |
| Enregistrement officiel (so101_sim_vision) ✅ | téléopération bras maître bi-caméra, 5 épisodes | **5/5 épisodes tous intégrés** : 61.5 / 53.4 / 101.1 / 62.4 / 75.4 s, soit 10610 frames @29.97Hz, 0 tick hors budget, aucun crash ; actions valides sur les six axes + pince pendant toute la durée ; vérification par décodage des deux flux vidéo réussie |
