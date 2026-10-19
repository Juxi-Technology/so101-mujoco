# 01 · Umgebung einrichten

Einmalige Aktion. Dieses Repository verwendet **uv zur Verwaltung einer projektintern isolierten `.venv`** – `uv run` nutzt ausschließlich die Umgebung in diesem Verzeichnis
und rührt dein conda nicht an (dieses Design ist Absicht, siehe [07 Häufige Probleme](07-troubleshooting.md)).

## Installation

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'   # Sonderfall dieses Rechners, siehe 07

# CPU-Version von torch (dieser Rechner hat keine dedizierte GPU; bei Maschinen mit NVIDIA-GPU UV_TORCH_BACKEND entfernen und gemäß pyproject-Kommentar die CUDA-Version verwenden)
UV_TORCH_BACKEND=cpu uv sync --frozen --extra core_scripts --extra feetech --extra pynput-dep --extra training
```

Zweck der vier Extras:

| extra | Bereitgestellt | Benötigt von |
| --- | --- | --- |
| `core_scripts` | Offizielle record-/teleoperate-/calibrate-/replay-Einstiegspunkte + Dataset- und Visualisierungsabhängigkeiten | Alle |
| `feetech` | `scservo_sdk` (serielles Protokoll für STS3215-Servos) | Arbeiten mit dem realen Roboter |
| `pynput-dep` | Globale Tastaturüberwachung | Tastatur-Teleoperation, Tasten zur Episodensteuerung bei der Aufzeichnung |
| `training` | `accelerate` / `wandb` usw. | `lerobot-train`-Training, Policy-Deployment (`lerobot-rollout`) |

MuJoCo bei Bedarf temporär ergänzen (nicht in der Lock-Datei, wird bei Bedarf geladen):

```bash
uv run --frozen --with mujoco python <脚本>
```

**Lieber eine conda-Umgebung verwenden?** Dann benötigen die Ausführungsbefehle kein `uv run`-Präfix – die drei Befehle zum Erstellen der Umgebung und die Hinweise stehen in
[09 Vollständiges Nutzungstutorial · Anhang A](09-usage-tutorial.md).

## Überprüfung

```bash
uv run --frozen --with mujoco python -c "import mujoco, scservo_sdk, pynput, lerobot, torch; print('OK')"
uv run --frozen lerobot-calibrate --help | head -3   # Offizieller Einstiegspunkt verfügbar
```

## Häufige Probleme

- **`uv sync` meldet `failed to persist temporary file ... os error 17`**: Sonderfall des uv-Cache-Verzeichnisses über Laufwerksgrenzen auf diesem Rechner;
  das obige `UV_CACHE_DIR`-Präfix verwenden, Details siehe [07](07-troubleshooting.md).
- **Kein Python aus dem Microsoft Store verwenden**: Das von uv automatisch verwaltete Python 3.12 wählen.
- Der erste `uv run --with mujoco` lädt ein etwa 5,6 MB großes mujoco-Wheel herunter, danach wird der Cache genutzt.
