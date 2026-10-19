# 01 · Préparation de l'environnement

Opération à effectuer une seule fois. Ce dépôt utilise **un `.venv` isolé au sein du projet, géré par uv** — `uv run` n'utilise que l'environnement de ce répertoire et ne touche pas à votre conda (ce choix est délibéré, voir [07 Problèmes fréquents](07-troubleshooting.md)).

## Installation

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'   # 本机特例，见 07

# CPU 版 torch（本机无独显；有 NVIDIA GPU 的机器去掉 UV_TORCH_BACKEND 并参考 pyproject 注释换 CUDA 版）
UV_TORCH_BACKEND=cpu uv sync --frozen --extra core_scripts --extra feetech --extra pynput-dep --extra training
```

Utilité des quatre extras :

| extra | Ce qu'il fournit | Pour qui |
| --- | --- | --- |
| `core_scripts` | points d'entrée officiels record / teleoperate / calibrate / replay + dépendances pour jeux de données + visualisation | tous |
| `feetech` | `scservo_sdk` (protocole série des servomoteurs STS3215) | opérations liées au robot réel |
| `pynput-dep` | écoute globale du clavier | téléopération au clavier, touches de contrôle des épisodes pendant l'enregistrement |
| `training` | `accelerate` / `wandb`, etc. | entraînement `lerobot-train`, déploiement de politiques (`lerobot-rollout`) |

Ajouter MuJoCo temporairement en cas de besoin (hors fichier de verrouillage, chargé à la demande) :

```bash
uv run --frozen --with mujoco python <脚本>
```

**Vous préférez passer à un environnement conda ?** Les commandes d'exécution n'ont alors plus besoin du préfixe `uv run` — les trois commandes de création de l'environnement et les points d'attention se trouvent dans [09 Tutoriel d'utilisation complet · Annexe A](09-usage-tutorial.md).

## Vérification

```bash
uv run --frozen --with mujoco python -c "import mujoco, scservo_sdk, pynput, lerobot, torch; print('OK')"
uv run --frozen lerobot-calibrate --help | head -3   # 官方入口可用
```

## Problèmes fréquents

- **`uv sync` renvoie `failed to persist temporary file ... os error 17`** : cas particulier Windows lié au répertoire de cache uv situé sur un autre disque sur cette machine ; il suffit d'utiliser le préfixe `UV_CACHE_DIR` ci-dessus, voir [07](07-troubleshooting.md) pour les détails.
- **N'utilisez pas la version de Python du Microsoft Store** : choisissez simplement le Python 3.12 géré automatiquement par uv.
- Le premier `uv run --with mujoco` télécharge une wheel mujoco d'environ 5,6 Mo ; les suivants passent par le cache.
