# 06 · Datenaufzeichnung und -wiedergabe

## Vorlage für den Aufzeichnungsbefehl

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'

# Realen Roboter aufzeichnen (Leader → realer Follower)
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

# Aufzeichnung in der Simulation (Leader → simulierter Follower)
#   --robot.* ersetzen durch: --robot.type=so101_mujoco
# Aufzeichnung in der Simulation (Tastatursteuerung)
#   --teleop.* ersetzen durch: --teleop.type=so101_keyboard --teleop.rate=150
```

## Parameter im Detail (häufige Stolperfallen)

| Parameter | Beschreibung |
| --- | --- |
| `--dataset.root` | **root ist das Dataset-Verzeichnis selbst** (nicht Elternverzeichnis + repo_id zusammengesetzt); für jede Aufnahme ein neues Verzeichnis verwenden |
| `--dataset.repo_id` | Bei lokaler Aufzeichnung nur ein Bezeichner; erst beim späteren Push zum Hub wird ein echter `用户名/名字` benötigt |
| `--dataset.no_stamp=true` | Kein Zeitstempel-Suffix, Verzeichnis/Name stabil; beim erneuten Aufnehmen mit gleichem Namen muss das alte Verzeichnis zuerst gelöscht werden |
| `--dataset.episode_time_s` | **Obergrenze** einer Episode (Sicherheitsnetz); im normalen Betrieb mit `→` vorzeitig beenden |
| `--dataset.reset_time_s` | Rückstellzeit zwischen Episoden, die nicht aufgezeichnet wird; währenddessen treibt der Leader den Follower weiter in Echtzeit. **Bei der Simulationsaufzeichnung springen die Würfel beim Eintritt in diese Phase automatisch an ihre Ausgangsposition zurück** (siehe unten) |
| `--dataset.video` | Nur bei benötigten Kameradaten aktivieren (visuelle Datasets benötigen true; pyav-Fallback ist verifiziert funktionsfähig) |
| `--dataset.rgb_encoder.vcodec` | Video-Encoder. **Auf diesem Rechner für die Aufzeichnung mit zwei Kameras `h264` verwenden**: `record.py` injiziert das bereits standardmäßig (das Upstream-Standard libsvtav1 scheitert beim gleichzeitigen Öffnen zweier Encoder-Streams mit Speicherzuweisungsfehler und die gesamte Sitzung stürzt ab – siehe [07](07-troubleshooting.md)); bei expliziter Angabe wird nichts injiziert |
| `--dataset.encoder_threads` | Anzahl der Encoding-Threads. **`record.py` injiziert standardmäßig 2**: Standardmäßig alle Kerne auszulasten lässt die Simulationsanzeige während des Speicherns deutlich ruckeln (siehe [07](07-troubleshooting.md)); mit 2 Threads pro Encoder bleibt die Simulation beim Speichern flüssig; bei expliziter Angabe wird nichts injiziert |
| `--dataset.push_to_hub` | Direkter HF-Zugriff von diesem Rechner benötigt einen Proxy; vorerst false lassen und nach der Aufzeichnung manuell pushen |

## Episoden-Steuertasten (global, während der Aufzeichnung durchgehend aktiv)

| Taste | Wirkung |
| --- | --- |
| `→` oder `n` | Aktuelle Episode beenden (**speichern**) |
| `←` oder `r` | Aktuelle Episode verwerfen und **an Ort und Stelle neu aufnehmen** (für eine unzufriedenstellende Episode, ohne Sitzungsneustart) |
| `q` | Gesamte Sitzung beenden und Dataset speichern (**empfohlen**) |
| `Esc` | Wie `q` (trennt zusätzlich die Tastatur-Teleoperation; sauberes Beenden verifiziert, dennoch vorzugsweise `q` verwenden) |

**Empfohlene Vorgehensweise**: Vor Aufnahmebeginn den Leader nahe der Mittelstellung abstellen (damit der Konvergenzabschnitt beim Start, in dem der Simulations-/reale Arm „hinfährt“, nicht mit aufgezeichnet wird);
nach Aufnahmebeginn zuerst eine Sekunde still halten, dann mit der Bewegung beginnen.

## Automatischer Szenen-Reset bei der Simulationsaufzeichnung

Bei der Aufzeichnung am realen Roboter muss man die Würfel in der Phase „Reset the environment“ manuell zurücklegen. In der Simulation
**teleportiert der Aufzeichnungs-Starter (`record.py`) die drei Würfel zu Beginn dieser Phase automatisch an ihre Ausgangsposition** (und setzt die Geschwindigkeit auf null); nach dem Beenden jeder Episode mit `→`
muss man also nur den Leader in die Startpose zurückbringen, die Würfel gehen automatisch zurück, und die nächste Episode startet aus der festen Anfangsszene.
Der reale Follower hat dieses Verhalten nicht (manuelle Platzierung wie gewohnt); `teleoperate.py`/`replay.py` betrifft das ebenfalls nicht.

## Inspektion nach der Aufzeichnung

```bash
uv run --frozen python examples/so101_mujoco/inspect_dataset.py \
    --repo-id local/so101_sim_vision \
    --root examples/so101_mujoco/outputs/datasets/so101_sim_vision
```

Gibt pro Episode die Frame-Anzahl, Dauer, Aktionsamplitude der sechs Gelenke und den Folgefehler aus:

- **Episoden mit action span = 0** sind Leeraufnahmen (die Person hat sich nicht bewegt); löschen und neu aufnehmen;
- **Ein großer |action−obs|-Wert am Anfang** ist der Konvergenzabschnitt (normal); im mittleren und späteren Verlauf meist <10 Einheiten.

## Daten mit Bild in der Simulation aufnehmen (Wrist-Kamera)

Der Simulationsroboter kann die Wrist-Kamera (`sim_cam`) der Szene als Bildbeobachtung ins Dataset aufnehmen:

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

Kernpunkte: `--robot.image_camera=sim_cam` (Kameraname) + `--dataset.video=true` (Bilder werden per Video kodiert, pyav-Fallback ist verifiziert funktionsfähig).
In den Dataset-Features erscheint `observation.images.wrist` (480×640×3). Auflösung und Bildrate können mit
`--robot.image_width/--robot.image_height/--robot.image_fps` angepasst werden.
Beim geöffneten Fenster (`onscreen=true`, Standard) öffnet sich neben dem Hauptansichtsfenster **für jede Kamera ein eigenes Live-Vorschaufenster**
(Wrist / Draufsicht, Beschriftung oben links); während der Aufzeichnung sieht man direkt, ob beide Bildströme in Ordnung sind. Wer das nicht braucht, setzt
`--robot.preview_cameras=false`. Die Vorschaufenster aktualisieren standardmäßig mit **15 Hz** (`--robot.preview_fps` anpassbar) –
sie dienen der Statusanzeige und müssen nicht mit den 50 Hz des Hauptfensters mitlaufen; dadurch ist die Rendering-Last bei 3 Fenstern auf demselben Bildschirm viel geringer.

**Szene und Draufsicht-Kamera (ab 2026-10-16)**: Die Simulationsszene bringt einen Arbeitsbereich mit – Unterlegplatte, dreifarbige Würfel (34 mm), Aufbewahrungsbox (siehe `so101_assets.add_workspace`,
Layout kann mit `preview_workspace.py` gerendert und feinjustiert werden); zusätzlich gibt es eine feste Draufsicht-Kamera `top_cam` (oben im Bild = von Roboterarm weg).
Mit `--robot.top_camera=top_cam` wird das Draufsichtbild als `observation.images.top` aufgezeichnet (beide Kameras gleichzeitig); wenn nur die Wrist-Kamera gewünscht ist, den Parameter weglassen.
Die Videokodierung nach dem Ende einer Episode verarbeitet beide Bildströme gleichzeitig; eine etwas längere Wartezeit ist normal.

## Wiedergabe

```bash
# Wiedergabe in der Simulation (nur im Fenster, Trajektorie erneut ansehen)
uv run --frozen --with mujoco python examples/so101_mujoco/replay.py \
    --dataset.repo_id=local/so101_sim_vision \
    --dataset.root=examples/so101_mujoco/outputs/datasets/so101_sim_vision --dataset.episode=0

# Wiedergabe am realen Roboter (gleicher Mechanismus; darauf achten, dass die Umgebung mit der Aufzeichnung übereinstimmt)
uv run --frozen --with mujoco python examples/so101_mujoco/replay.py \
    --robot.type=so101_follower --robot.port=COM172 --robot.id=juxi_so101 \
    --robot.use_degrees=false --robot.max_relative_target=10 \
    --dataset.repo_id=local/juxi_so101_teleop \
    --dataset.root=examples/so101_mujoco/outputs/datasets/juxi_teleop_run1 --dataset.episode=0
```

> Der offizielle `lerobot-replay`-Einstiegspunkt lädt die Plugins dieses Projekts nicht; direkt verwendet meldet er `invalid choice: 'so101_mujoco'` –
> daher einheitlich den Starter `replay.py` verwenden.

## Dataset-Format und -Speicherort

Datasets sind LeRobotDataset v3: `action` und `observation.state` sind jeweils 6-dimensionale Vektoren
(`shoulder_pan.pos … gripper.pos`), identisch mit den offiziellen realen Datasets und direkt für gemischtes Training geeignet.

```
examples/so101_mujoco/outputs/datasets/
└── juxi_teleop_run1/   Tastatur-Teleoperation am realen Roboter (1 Episode / 2430 Frames / 81 s) ✅ beibehaltene reale Daten

> Bereinigung am 2026-10-16: Die alten Simulationsaufzeichnungen (`sim_run2`, `sim_vision_demo`, `sim_vision_run1/2/3`)
> wurden vollständig gelöscht. **Das offizielle Dataset `so101_sim_vision` (zwei Kameras / 5 Episoden / 10610 Frames / 353,8 s / h264)
> wurde am selben Abend fertig aufgezeichnet ✅**; die Einzelvideos pro Episode liegen unter `outputs/videos/so101_sim_vision/`,
> die Dual-Kamera-Vorschau-Streifen unter `outputs/renders/sim_vision_epN_dual.png`.
```

## Messprotokoll dieser Sitzung (2026-10-15)

| Sitzung | Inhalt | Ergebnis |
| --- | --- | --- |
| Realer Roboter run1 | Tastatur-Teleoperation, Aufzeichnung am realen Roboter | 1 Episode 81 s, Amplitude der sechs Gelenke 75–140 Einheiten, stabil bei 30 Hz |
| Wiedergabe realer Roboter | erneutes Abspielen derselben Episode | 2430 Frames vollständig reproduziert, keine Anomalien |
| Simulation run2 | Leader-Teleoperation, Aufzeichnung in der Simulation | 5 Episoden 157 s, Folgefehler ep1–4 <12 Einheiten |
| Simulations-Wiedergabe ep1 | erneute Wiedergabe im Fenster | Trajektorie entspricht der Bedienung (bestätigt) |

## Zusätzliche Messungen (2026-10-16)

| Sitzung | Inhalt | Ergebnis |
| --- | --- | --- |
| Neuer Leader (COM124) | erneute Kalibrierung (neuer Arm/neue Servos) | ✅ Kalibrierung erfolgreich; `so101_leader_trim` passt die Nullpunktkompensation automatisch an die neue Kalibrierung an |
| Vision run1 | Leader-Teleoperation, Aufzeichnung in der Simulation (mit Bild) | 2 Episoden / 3177 Frames / 106 s @ 29,97 Hz; Folgefehler durchgehend ≤2 Einheiten (nur im ersten Frame 0,5 s Konvergenz); `observation.images.wrist` als Video im Dataset und durch Dekodierung verifiziert ✅ |
| Vision run2 | Fortsetzung mit zwei Kameras (`--resume`) | ep0 (2776 Frames / 92,6 s) verlustfrei; ep1 beim Speichern mit libsvtav1-Encoder-OOM, gesamte Sitzung abgestürzt → Encoder auf h264 umgestellt (`record.py` injiziert standardmäßig) und End-to-End verifiziert (2 Episoden × zwei Encoder-Streams); Reste bereinigt, offizielle Neuaufnahme auf run3 verschoben |
| Vision run3 | offizielle Aufzeichnung mit zwei Kameras (h264) | 1. Sitzung: ep0 (185,2 s / 5554 Frames) + ep1 (72,8 s / 2186 Frames) sauber im Dataset, Inspektion bestanden; während der Encoder-Pause zwischen den Sitzungen mehrfach `→` gedrückt, wodurch ein Absturz bei leerer Episode ausgelöst wurde (Mechanismus und Schutz siehe [07](07-troubleshooting.md)) → restliche Episoden in Folgesitzung aufgezeichnet (Plan: 5 Episoden) |
| Erste offizielle Aufzeichnung (so101_sim_vision) | zwei Kameras (h264 + 2 Threads + Vorschaufenster 15 Hz) | ep0 (82,3 s / 2469 Frames) beim Speichern Speicherzuweisungsfehler des Encoders, gesamte Sitzung abgestürzt (System-Commit nahezu voll, siehe [07](07-troubleshooting.md)) → **automatischer Retry bei Encoding-Fehler** und **Konsolen-Stummschaltung** ergänzt (beides verifiziert, Smoke-Test 26 Punkte bestanden); offizielle Neuaufnahme nach Neustart des Rechners |
| Offizielle Aufzeichnung (so101_sim_vision) ✅ | zwei Kameras, Leader-Teleoperation, 5 Episoden | **5/5 Episoden vollständig im Dataset**: 61,5 / 53,4 / 101,1 / 62,4 / 75,4 s, insgesamt 10610 Frames @29,97 Hz, 0 Ticks über Budget, keine Abstürze; sechs Achsen + Greifer durchgehend mit gültigen Aktionen; Dekodierung beider Videostreams verifiziert |
