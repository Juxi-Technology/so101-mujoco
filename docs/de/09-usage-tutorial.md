# 09 · Vollständiges Nutzungstutorial (Arm starten → Dataset → Videos ansehen → Training → Deployment)

> Ein End-to-End-Betriebshandbuch: Einmal durchgehen und vom „Leader-Arm anstecken“ bis „die trainierte Policy arbeitet selbstständig in der Simulation“.
> Voraussetzungen: Umgebung ist nach [01](01-environment.md) eingerichtet, Leader-Arm nach [03](03-hardware-calibration.md) kalibriert
> (auf diesem Rechner `juxi_leader` / COM124). Alle Fallstricke rund um die Aufzeichnung sind in [07](07-troubleshooting.md) gesammelt.

## 0 · Einmalige Vorbereitung

```bash
# Auf diesem Rechner muss vor allen uv-Befehlen gesetzt werden (Sonderfall laufwerksübergreifender Cache, siehe 07)
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
```

Leader-Arm anstecken und seriellen Port prüfen (**kann sich bei jedem Ein-/Ausstecken ändern**):

```bash
uv run --frozen python -c "from serial.tools import list_ports; print([p.device for p in list_ports.comports()])"
```

Auf dem Bildschirm Platz freihalten: Die Aufzeichnung öffnet **3 Fenster** (Hauptansicht + `wrist camera - live` + `top camera - live`).

## 1 · Teleoperations-Aufwärmrunde (empfohlen)

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/teleoperate.py \
    --robot.type=so101_mujoco \
    --teleop.type=so101_leader_trim --teleop.port=COM124 --teleop.id=juxi_leader \
    --teleop.use_degrees=false
```

Den Leader bewegen und prüfen, ob der simulierte Arm folgt; vor dem Beenden (Ctrl-C) den Leader **nahe der Mittelstellung** abstellen, damit beim Aufnahmestart kein großer Konvergenzabschnitt entsteht.

## 2 · Aufzeichnung (Kernbefehl)

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

Kernpunkte (übrige Parameter siehe Parametertabelle in [06](06-record-and-replay.md)):

| Punkt | Beschreibung |
| --- | --- |
| `--dataset.root` | **root ist das Dataset-Verzeichnis selbst**, für jede Sitzung ein neues Verzeichnis (existiert es bereits, wird der Start abgelehnt) |
| Automatisch injizierte Standardwerte | Video-Encoder `h264`, Encoder-Threads `2` – `record.py` gibt beim Start zwei Hinweise aus; explizit übergebenes `--dataset.rgb_encoder.vcodec=...` / `--dataset.encoder_threads=...` überschreibt (Gründe siehe 07) |
| Vorschaufenster | standardmäßig an (15 Hz, mit `--robot.preview_cameras=false` abschaltbar; `--robot.preview_fps` anpassbar) |
| `--dataset.video=true` | Bilder beider Kameras landen im Dataset (`observation.images.wrist / top`); wenn nur die Wrist-Kamera gewünscht ist, `top_camera` weglassen |

## 3 · Bedienung während der Aufzeichnung

| Taste | Wirkung |
| --- | --- |
| `→` oder `n` | Aktuelle Episode beenden und speichern |
| `←` oder `r` | Aktuelle Episode verwerfen, an Ort und Stelle neu aufnehmen |
| `q` | Gesamte Sitzung beenden, Dataset speichern |

- Nach dem Ende einer Episode **gehen die Würfel automatisch zurück**; du musst nur den Leader in die Startpose zurückziehen; beginne die nächste Episode erst, wenn `Recording episode N` erscheint.
- In der Speicherphase (einige zehn Sekunden) gibt die Konsole `[record.py] reset done; saving the episode + encoding videos now` aus –
  während dieser Zeit **werden Tasten sicher ignoriert** (Fehldrücke beschädigen keine Episode); erst wenn die nächste Zeile `Recording episode` erscheint, wieder bedienen.
- Bei Encoding-Fehlern gibt es **einen automatischen Retry als Fangnetz** (nach `video encode failed ... retrying once` wird nach 3 Sekunden automatisch erneut versucht); bereits gespeicherte Episoden gehen nie verloren.

## 4 · Inspektion

```bash
uv run --frozen python examples/so101_mujoco/inspect_dataset.py \
    --repo-id local/so101_sim_vision \
    --root examples/so101_mujoco/outputs/datasets/so101_sim_vision
```

Wie die Ausgabe zu lesen ist:

- **Episoden, deren action span durchgehend 0 ist (oder deren Greifer 0 ist)**, sind Leer-/ungültige Aufnahmen; löschen und neu aufnehmen;
- **Ein großer `max |act-obs|`-Wert am Anfang jeder Episode** ist der Konvergenzabschnitt, normal; im mittleren und späteren Verlauf sollte er unter ~10 Einheiten liegen.

## 5 · Videos ansehen

```bash
uv run --frozen python examples/so101_mujoco/export_videos.py \
    --root examples/so101_mujoco/outputs/datasets/so101_sim_vision
```

Ergebnisse:

- `examples/so101_mujoco/outputs/videos/<数据集名>/epN_top.mp4`, `epN_wrist.mp4` – **pro Episode und Kamera ein per Doppelklick abspielbares Video**;
- `examples/so101_mujoco/outputs/renders/<数据集名>_epN_dual.png` – pro Episode ein Bildstreifen (obere Reihe Draufsicht, untere Reihe Wrist, 6 gleichmäßig entnommene Frames) zur schnellen Sichtprüfung (`--no-strips` zum Überspringen).

Im Dataset liegen außerdem die ursprünglich gepackten Videos (mehrere Episoden der Reihe nach in einer Datei):
`outputs/datasets/<数据集名>/videos/observation.images.{top,wrist}/chunk-000/file-000.mp4`.

## 6 · Wiedergabe (optional)

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/replay.py \
    --dataset.repo_id=local/so101_sim_vision \
    --dataset.root=examples/so101_mujoco/outputs/datasets/so101_sim_vision --dataset.episode=0
```

## 7 · Training

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

| Punkt | Beschreibung |
| --- | --- |
| `--policy.type` | Policy-Typ, **mit `act` beginnen** (passt am besten zu Datenumfang/Aufgabe); `ls src/lerobot/policies/` zeigt weitere Optionen (diffusion / smolvla / pi0 usw.) |
| `--policy.push_to_hub=false` | **Zwingend** – standardmäßig wird ein Push zum HuggingFace Hub versucht; ohne konfigurierte `repo_id` bricht es mit Fehler ab; zum Pushen `--policy.repo_id=你的用户名/模型名` setzen (vorher `hf auth login`) |
| `--policy.device=cpu` | Dieser Rechner ohne dedizierte GPU verwendet `cpu`; auf Rechnern mit NVIDIA-GPU den Parameter weglassen (verwendet automatisch cuda) |
| Artefakte | `output_dir/checkpoints/<步数>/` und `checkpoints/last/pretrained_model/` – für das Deployment auf letzteres zeigen; die `train_config.json` für die Fortsetzung liegt ebenfalls darin |
| Fortsetzung | Nach Unterbrechung dem ursprünglichen Befehl hinzufügen: `--resume=true --config_path=<output_dir>/checkpoints/last/pretrained_model/train_config.json` |

**Geschwindigkeitserwartung auf diesem Rechner**: reine CPU etwa **2 Sekunden/Schritt** (Batch 2, 480p Dual-Kamera; gemessener 12-Schritte-Smoke: Loss von 70 auf 22 gefallen, Richtung normal).
Daher eignet sich dieser Rechner zur Verifikation der Kette mit kleinen Schrittzahlen – das mitgelieferte `outputs/train/smoke_act` ist das Ergebnis von 12 Schritten;
**für offizielles Training (ACT üblicherweise in der Größenordnung von 100.000 Schritten) wird ein Rechner mit GPU empfohlen, die Befehle sind identisch.**

> Abhängigkeitshinweis: Training benötigt das `training`-Extra (accelerate usw.). Bei `accelerate is required but not installed`
> gemäß Installationsbefehl in [01](01-environment.md) `--extra training` ergänzen und erneut versuchen.

## 8 · Deployment (die Policy in der Simulation selbst arbeiten lassen)

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/rollout.py \
    --policy.path=examples/so101_mujoco/outputs/train/act_so101_sim_vision/checkpoints/last/pretrained_model \
    --strategy.type=base \
    --robot.image_camera=sim_cam --robot.top_camera=top_cam \
    --task="put the cube in the box" --duration=30
```

| Punkt | Beschreibung |
| --- | --- |
| Kameraparameter | `--robot.image_camera/--robot.top_camera` **müssen mit der Aufzeichnung des Datasets übereinstimmen** (sim_cam + top_cam), sonst bekommt die Policy nicht die Bilder, mit denen sie trainiert wurde |
| `--task` | Identisch mit `--dataset.single_task` bei der Aufzeichnung |
| `--duration` | Nach wie vielen Sekunden automatisch beenden (vor dem Beenden wird der Arm in die Ausgangspose zurückgebracht und getrennt); auch `Ctrl-C` zwischendurch stoppt |
| Kette zuerst testen | Das mitgelieferte Demo-Modell verwenden: `--policy.path=examples/so101_mujoco/outputs/train/smoke_act/checkpoints/last/pretrained_model` (12 Schritte Training, Aktionen fast zufällig, nur zur Verifikation der Kette) |
| Reines CPU-Deployment | Policy-Inferenz hat gelegentlich 0,5-s-Spitzen, meldet `Control loop is running slower ... than the target FPS` – läuft in der Simulation, ruckelt aber; auf GPU kein Problem (gemessener 20-s-Smoke lief durchgehend und beendete sich ordnungsgemäß) |
| Deployment am realen Roboter | `--robot.*` durch realen Roboter ersetzen: `--robot.type=so101_follower --robot.port=COMxx --robot.id=juxi_so101 --robot.use_degrees=false` (Platz auf dem Tisch freihalten) |
| Andere Modi | `--strategy.type=sentry / highlight / dagger / episodic`: Aufzeichnen während des Laufs / Ringpuffer mit Tastenspeicherung / Human-in-the-Loop-Korrektur / episodenbasierte Aufzeichnung, siehe `lerobot-rollout --help` |

## Anhang A · Auf conda-Umgebung umstellen (optional)

Dieses Repository verwendet standardmäßig eine **von uv verwaltete projektinterne `.venv`** (siehe [01](01-environment.md)), alle Ausführungsbefehle benötigen
das Präfix `uv run --frozen --with mujoco`. Wer conda gewohnt ist, **ersetzt den Schritt „Umgebung erstellen“ durch die folgenden drei**
und **entfernt danach bei allen Befehlen das uv-Präfix** (`python examples/...` direkt ausführen); `UV_CACHE_DIR` ist dann ebenfalls nicht mehr nötig
(das ist der uv-Sonderfall mit laufwerksübergreifendem Cache, unabhängig von conda):

```bash
# Einmalig: Umgebung im Repository-Wurzelverzeichnis erstellen (Python-Version wie in 01: 3.12)
conda create -n lerobot-sim python=3.12 -y
conda activate lerobot-sim
pip install -e .            # lerobot dieses Repositories und seine Abhängigkeiten installieren (inkl. torch; unter Windows installiert pip standardmäßig die CPU-Version)
pip install "mujoco==3.16"  # Beim uv-Weg wird mujoco per --with mujoco temporär bereitgestellt, beim conda-Weg als dauerhafte Abhängigkeit installiert
```

Danach wird z. B. die Aufzeichnung zu:

```bash
python examples/so101_mujoco/record.py --robot.image_camera=sim_cam ...
```

Zwei Hinweise:

1. **Versionsabgleich**: `pip install -e .` löst Versionen selbst auf und stimmt möglicherweise nicht exakt mit `uv.lock` überein;
   für eine exakt zum aktuell gemessenen Umfeld passende Kombination mit uv gemäß Lock-Datei in die conda-Umgebung installieren:

   ```bash
   uv pip sync uv.lock --python "$(conda run -n lerobot-sim python -c 'import sys; print(sys.executable)')"
   pip install "mujoco==3.16"
   ```

2. Der Kalibrierungscache des Leader-Arms liegt unter `~/.cache/huggingface/lerobot/calibration/`, unabhängig davon, welche Umgebung verwendet wird; beim Umgebungswechsel ist keine erneute Kalibrierung nötig.

## Anhang B · Schnellreferenz häufiger Fallstricke

| Symptom | In einem Satz |
| --- | --- |
| Serieller Port lässt sich nicht öffnen | Zuerst Ports auflisten, die Nummer kann sich geändert haben (Schritt 0) |
| Konsole bleibt beim Speichern einige zehn Sekunden still | Es wird kodiert, das ist normal; sobald `saving the episode...` erscheint, keine Tasten drücken |
| Bild ruckelt gelegentlich während der Aufzeichnung | Ressourcenkonkurrenz der Kodierung im Speicherfenster; die Regelschleife selbst ist nicht betroffen (maßgeblich sind die Cadence-Zahlen), Details siehe 07 |
| Kann nach einem Absturz noch gerettet werden? | Bereits gespeicherte Episoden gehen nie verloren; mit `record.py --resume=true ... --dataset.num_episodes=N` weiter aufnehmen |
| `lerobot-train` meldet `'repo_id' argument missing` | Standardmäßig wird ein Hub-Push versucht: `--policy.push_to_hub=false` ergänzen (zum Pushen `--policy.repo_id` konfigurieren und vorher `hf auth login`) |
| Policy bewegt sich beim Deployment nicht oder unkontrolliert | Zuerst prüfen, ob `--robot.image_camera/--robot.top_camera` und `--task` mit der Aufzeichnung übereinstimmen; dann prüfen, ob nur sehr wenige Schritte trainiert wurden |

Alle Fallstricke und Lösungen (inkl. knapper Speicher, Encoding-OOM, leere Episoden usw.) siehe [07 · Häufige Probleme](07-troubleshooting.md).
