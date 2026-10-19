# SO-ARM101 × MuJoCo — Tutoriel de bout en bout (index)

> 🌐 Languages: [简体中文](../README.md) · [English](../en/README.md) · [Deutsch](../de/README.md) · [Español](../es/README.md) · **Français** · [Italiano](../it/README.md) · [日本語](../ja/README.md) · [한국어](../ko/README.md) · [Português (BR)](../pt-br/README.md) · [Português (PT)](../pt-pt/README.md) · [繁體中文](../zh-hant/README.md)

> Ce tutoriel documente et reproduit le **flux de travail complet simulation + robot réel** du SO-ARM101 : depuis la mise en place de l'environnement, la vérification du modèle et la calibration du matériel réel,
> jusqu'à la téléopération au clavier/bras maître, l'enregistrement et la relecture des données. Toutes les commandes ont été validées lors d'une session réelle + simulation le 2026-10-15.
>
> Public visé : utilisateurs du kit Juxi SO-ARM101 et ingénieurs internes. Aucune connaissance préalable de MuJoCo ou LeRobot n'est requise.

## Carte du parcours complet (deux pistes, des composants partagés)

```
                         ┌──────────────── 共用组件 ────────────────┐
                         │  数据集格式(LeRobotDataset) · 回放 · 未来训练  │
                         └──────────────────────────────────────────┘
                                      ▲                    ▲
        ┌── 真机轨 ──────────────────┘                    └──────────── 仿真轨 ──┐
        │  操控: 主动臂(实体) / 键盘                                      操控: 键盘 / 主动臂(实体) │
        │  被控: 真机从动臂 (COM 串口)                                    被控: MuJoCo 仿真从动臂   │
        │  命令: --robot.type=so101_follower                            命令: --robot.type=so101_mujoco │
        └───────────────────────────────────────────────────────────────────────┘
```

| Chapitre | Contenu | Ce que vous obtenez |
| --- | --- | --- |
| [01 Préparation de l'environnement](01-environment.md) | environnement uv, extras de dépendances, points d'attention Windows | un environnement opérationnel |
| [02 Vérification du modèle de simulation](02-sim-model-verification.md) | chargement/comparaison/rendu piloté des trois modèles MJCF | la confiance dans le modèle et le comportement de la simulation |
| [03 Connexion au robot réel et calibration](03-hardware-calibration.md) | identification des ports série, premier contrôle en lecture seule, calibration du bras esclave/maître | deux bras reconnus par le logiciel |
| [04 Téléopération au clavier](04-keyboard-teleop.md) | pilotage clavier du robot réel/simulé, réglage de la vitesse, limitation de vitesse de sécurité | le moyen de contrôle manuel le plus rapide |
| [05 Jumeau numérique du bras maître](05-leader-digital-twin.md) | le bras maître physique pilote le bras esclave simulé, ajustement fin du zéro | démonstration de jumeau numérique et acquisition de données |
| [06 Enregistrement et relecture de données](06-record-and-replay.md) | enregistrement réel/simulation, contrôle des épisodes, relecture, script de contrôle qualité | un jeu de données exploitable pour l'entraînement |
| [07 Problèmes fréquents et retours d'expérience](07-troubleshooting.md) | tous les pièges rencontrés dans ce parcours et leurs solutions | un manuel de dépannage |
| [08 Feuille de route](08-roadmap.md) | caméras, scènes avec objets, génération automatique de données, entraînement | les prochaines étapes prévues |
| [09 Tutoriel d'utilisation complet](09-usage-tutorial.md) | chaîne complète : démarrage du bras → enregistrement → contrôle qualité → visionnage des vidéos → entraînement → déploiement en simulation ; inclut une alternative avec environnement conda | de zéro à un jeu de données conforme, puis à une politique en action |

## Trois conventions à retenir impérativement

1. **Système d'unités (aligné sur les trois acteurs)** : les cinq articulations du corps utilisent **−100~100** (proportion de course, 0 = milieu de course), la pince utilise **0~100**
   (0 = fermée). Le robot réel (`use_degrees=false`), la simulation et le bras maître suivent tous cette convention ; les jeux de données enregistrés sont structurellement identiques aux jeux de données réels officiels tels que `lerobot/svla_so101_pickplace` (vecteur à 6 dimensions + noms des articulations).
2. **Correspondance des rôles** : l'objet piloté (robot réel ou simulation) est toujours configuré avec `--robot.*` ; le dispositif de commande (clavier/bras maître) est toujours configuré avec `--teleop.*`.
3. **Préfixe de commande sur cette machine** : sur ce poste de développement, toutes les commandes `uv` nécessitent de définir d'abord le répertoire de cache (raison dans [07](07-troubleshooting.md)) :

   ```bash
   export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
   ```

## Environnement de test

| Élément | Version |
| --- | --- |
| Système | Windows 11 |
| Python / uv | 3.12.9 / 0.12.5 |
| lerobot | 0.6.2 (ce dépôt, `.venv` isolé dans le projet, sans impact sur conda) |
| MuJoCo | 3.16.0 |
| PyTorch | 2.11.0 (version CPU) |
| Matériel | bras maître SO-ARM101 (COM163) + bras esclave (COM172), puce série CH343 |
