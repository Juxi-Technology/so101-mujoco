# 02 · Vérification du modèle de simulation (chargement et pilotage MJCF)

## Source des modèles

Les trois modèles MJCF publics du SO-ARM101 ont tous été vérifiés comme utilisables dans ce projet :

| Abréviation | Fichier | Source |
| --- | --- | --- |
| Officiel — nouvelle calibration | `SO101/so101_new_calib.xml` | dépôt officiel TheRobotStudio/SO-ARM100 ; **une copie identique se trouve dans le zip du tutoriel de ce dépôt** (identique octet pour octet) |
| Officiel — ancienne calibration | `SO101/so101_old_calib.xml` | même dépôt (absent du zip, à télécharger) |
| Paquet de description ROS2 | `so_arm101_description/mjcf/so_arm101.xml` | pièce jointe du tutoriel de ce dépôt `SO-ARM101_ROS2.zip` |

Note : la procédure d'extraction du zip était fournie par une version antérieure de `so101_assets.py` et reste consultable ; depuis le 2026-10-16, le robot simulé a migré vers le **modèle SO-ARM100 de mujoco_menagerie** (intégré dans `assets/menagerie_so_arm100/`, les raisons et points clés de la migration figurent dans les notes de conception de [07](07-troubleshooting.md)).

## Vérification du pilotage et du rendu

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
uv run --frozen --with mujoco python examples/so101_mujoco/load_and_drive.py \
    --model "<模型路径>" --out-dir out
```

Le script affiche un résumé structurel (articulations/actionneurs/gains/plages) et génère une vidéo de validation « balayage des six articulations une à une + sinus coordonné » ainsi que des images fixes. Des exemples de résumés structurels sont disponibles dans `reports/` (fournis avec le dépôt) ; les vidéos de référence (`media/`) sont volumineuses et ne sont pas distribuées avec le dépôt — elles peuvent être régénérées à tout moment avec la commande ci-dessus.

## Différences clés entre les trois modèles (mesurées)

| Élément | Officiel — nouvelle calibration | Officiel — ancienne calibration | Paquet de description ROS2 |
| --- | --- | --- | --- |
| Sémantique du zéro | **milieu de course** de l'articulation | position **complètement tendue** à l'horizontale | milieu de course |
| Noms des articulations | `shoulder_pan` | idem | `shoulder_pan_joint` (suffixe) |
| Gain de position | kp=998.22, kv=2.731 | **kp=17.8, kv=0** | kp=998.22 |
| Unité de la pince | hinge en radians | hinge en radians | **normalisée 0~1** |
| Exclusion des autocollisions | aucune | aucune | oui (6 paires) |

**Erreur de suivi mesurée** : la nouvelle calibration et le paquet de description conservent une erreur statique de 0,0005 rad, l'ancienne calibration 0,03 rad (affaissement d'environ 1,7°, kp 56 fois plus faible).
Évaluer la même politique en simulation avec un modèle différent donne une dynamique différente ; notez bien quel modèle a été utilisé.

## Comportements du modèle à retenir

1. **Le sens positif de `shoulder_lift` pointe vers le bas** : dans le couple de commande, le « balancement vers le bas » utilise un angle positif ; vérifiez le signe avant toute correspondance de téléopération ou conversion de données.
2. **Toucher le sol bloque le mouvement** : à la limite de descente, le bout du doigt entre en contact avec le sol et s'arrête (le script intègre une protection de 8 cm au-dessus du sol qui réduit automatiquement l'amplitude).
3. Le modèle officiel n'a ni caméra ni keyframe ; une variante avec caméra `so101_new_calib_camera.xml` existe, utilisable pour l'enregistrement ultérieur de données visuelles.
