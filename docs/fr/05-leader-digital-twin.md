# 05 · Jumeau numérique du bras maître (le bras physique pilote le bras simulé)

Déplacez à la main le **bras maître physique** pour que le **bras esclave simulé dans la fenêtre MuJoCo** le suive en miroir en temps réel — la bonne façon de faire une démonstration de jumeau numérique ou de l'acquisition de données en simulation.

## Prérequis

Le bras maître est calibré (voir [03](03-hardware-calibration.md)) ; le port série est `COM163` dans cet exemple.

## Commande

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
uv run --frozen --with mujoco python examples/so101_mujoco/teleoperate.py \
    --robot.type=so101_mujoco \
    --teleop.type=so101_leader_trim --teleop.port=COM163 --teleop.id=juxi_leader \
    --teleop.use_degrees=false
```

- `--robot.type=so101_mujoco` : l'objet piloté est le bras simulé, la fenêtre s'ouvre automatiquement ;
- `--teleop.*` : le dispositif de commande est le bras maître physique (lecture seule, jamais de couple appliqué, aucun risque pour le bras maître) ;
- `--teleop.use_degrees=false` : **obligatoire**. Aligne les unités émises par le bras maître (système proportionnel à la course) sur celles du bras simulé.

Remplacer `--robot.type` par `so101_follower --robot.port=COM172 --robot.id=juxi_so101 --robot.max_relative_target=5` donne le jeu classique du kit « bras maître physique → bras esclave réel » ; la même calibration du bras maître s'applique.

## Que faire si le zéro est décalé : ajustement automatique du centre (`so101_leader_trim`)

**Symptôme** : le bras maître est placé à la « position médiane visuelle », mais le bras simulé est décalé de quelques degrés.

**Principe** : le zéro de normalisation de lerobot = **le milieu de la plage enregistrée lors du balayage de calibration** `(min+max)/2` ; or la « pose médiane » au moment de la validation de la calibration est enregistrée comme valeur brute 2048. Dès qu'une articulation a une course mécanique asymétrique, les deux « milieux » diffèrent toujours d'une quantité fixe (mesure sur le servomoteur n° 1 : plage enregistrée 776~3457, milieu 2116, soit 68 counts d'écart avec 2048 ≈ **5,6°**).
**Cet écart ne disparaît pas en recalibrant** (l'asymétrie de course est déterminée par la structure mécanique) ; il doit être compensé dans le logiciel.

**Solution** : le plugin `so101_leader_trim` calcule automatiquement la compensation de chaque articulation à partir du fichier de calibration selon la formule, et la soustrait en temps réel ; après une recalibration, il s'adapte automatiquement, sans réglage manuel :

```
补偿ᵢ = (2048 − minᵢ) / (maxᵢ − minᵢ) × 200 − 100
```

Valeurs effectives mesurées sur cette machine (affichées dans les logs de démarrage) :

| Articulation | Compensation (unités) |
| --- | --- |
| shoulder_pan | −5.11 |
| shoulder_lift | −0.92 |
| elbow_flex | +2.54 |
| wrist_flex | +0.69 |

Les autres articulations ont un écart < 0,05 et ne nécessitent pas de compensation ; la pince (0~100) et le mode en degrés ne participent pas à l'ajustement.

> Note pour les développeurs : le `name` de ce plugin doit rester `"so_leader"` — `name` est la clé de répertoire utilisée pour retrouver le fichier de calibration ;
> un nom de type personnalisé empêcherait de trouver le fichier de calibration et déclencherait à tort le processus de recalibration.
