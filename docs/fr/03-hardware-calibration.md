# 03 · Connexion au robot réel et calibration

## Identifier le port série

Une fois la carte driver à puce CH343 branchée, un port COM apparaît ; **son numéro peut changer à chaque branchement/débranchement ou changement de port USB**, vérifiez-le avant chaque connexion :

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
uv run --frozen python -c "import serial.tools.list_ports as lp; [print(p.device, '|', p.description, '|', p.hwid) for p in lp.comports()]"
```

## Étape 1 : contrôle initial en lecture seule (câblage/alimentation/santé des servomoteurs)

**Sans rien écrire**, commencez par pinguer les six servomoteurs un par un, puis lisez la tension et la température (l'état du couple est conservé tel quel) :

```bash
uv run --frozen python examples/so101_mujoco/hardware_check.py --port COM163
```

Une sortie normale ressemble à ceci : six lignes d'articulations, température 20~30 °C, couple 0 (bras libre). **La tension dépend du mode d'alimentation** : environ 11 V lorsque le bras esclave est alimenté par une source externe, environ 5 V lorsque le bras maître est alimenté uniquement par la carte driver — si les six servomoteurs sont tous lus, le câblage est correct. Un servomoteur manquant ou d'un modèle non conforme provoque une erreur immédiate.

## Étape 2 : calibration

La calibration écrit dans l'EEPROM des servomoteurs « la plage de course + la référence de position médiane » de chaque articulation et l'enregistre dans un fichier local ; **le bras esclave et le bras maître doivent chacun être calibrés une fois**.
Les fichiers de calibration des deux bras sont stockés séparément, sans influence mutuelle :

| Appareil | Commande | Emplacement du fichier de calibration |
| --- | --- | --- |
| Bras esclave | `uv run --frozen lerobot-calibrate --robot.type=so101_follower --robot.port=COM172 --robot.id=juxi_so101` | `~/.cache/huggingface/lerobot/calibration/robots/so_follower/juxi_so101.json` |
| Bras maître | `uv run --frozen lerobot-calibrate --teleop.type=so101_leader --teleop.port=COM163 --teleop.id=juxi_leader` | `.../calibration/teleoperators/so_leader/juxi_leader.json` |

`id` peut être nommé librement, mais **les opérations ultérieures de téléopération/d'enregistrement doivent utiliser le même id**, sinon la calibration sera redemandée.

### Étapes physiques (le terminal affiche un schéma)

1. **Placez le bras en position médiane puis appuyez sur Entrée** : base posée à plat au bord de la table, grand bras vertical vers le haut, avant-bras horizontal vers l'avant, rotation d'épaule et poignet centrés
   (la « pince » du bras maître est une poignée/gâchette). La position à cet instant est enregistrée comme « référence médiane » du bras.
2. Après avoir appuyé sur Entrée, **parcourez lentement toute la plage de mouvement, articulation par articulation** (`wrist_roll` n'a pas besoin d'être balayé, il est traité automatiquement comme un tour complet), puis appuyez à nouveau sur Entrée pour enregistrer.

Points d'attention :

- Pendant la calibration du bras esclave, le couple est à 0 (le bras est mou), guidez-le à la main ; le bras maître n'a de toute façon pas de couple.
- Le processus de calibration écrit dans l'EEPROM des servomoteurs (cela fait partie de la calibration, c'est normal).
- Résultats de calibration mesurés lors de cette session (à titre de comparaison) : course de 1474~2688 counts pour les articulations du bras esclave, `wrist_roll` 4095 ;
  bras maître 2208~2681 counts. Une course nettement asymétrique est normale (voir [05 Ajustement fin du zéro](05-leader-digital-twin.md) pour la raison).
