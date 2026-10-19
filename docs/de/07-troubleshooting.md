# 07 · Häufige Probleme und Erfahrungen

Die in diesem Workflow tatsächlich aufgetretenen Fallstricke, nach Symptom sortiert.

## Umgebung

| Symptom | Ursache und Lösung |
| --- | --- |
| `uv sync` meldet `failed to persist temporary file ... os error 17（跨盘）` | Windows-Sonderfall des uv-Cache-Verzeichnisses über Laufwerksgrenzen auf diesem Rechner. Allen uv-Befehlen `export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'` voranstellen |
| Die Konsole zeigt Dutzende Zeilen mit fehlgeschlagenem Laden von `libtorchcodec_core*.dll` | Rauschwarnung: Nach fehlgeschlagenem Laden von torchcodec wird automatisch auf **pyav** zurückgefallen. Gemessen (smoke [5]): pyav **kodiert und dekodiert Video-Datasets normal**, Status- und Video-Datasets sind nicht betroffen |
| `python` öffnet den Microsoft Store | Das von uv verwaltete Python verwenden; nicht die Store-Version |

## Teleoperation

| Symptom | Ursache und Lösung |
| --- | --- |
| Tastatursteuerung „sehr langsam“ | `--teleop.rate` ist mit standardmäßig 60 Einheiten/s konservativ; mit **150** fühlt es sich normal an (voller Stellweg ca. 1,3 s) |
| Das Startlog spammt `clamped to be safe` WARNING | Normale Ausgabe des Geschwindigkeitsbegrenzers beim Aufholen; hört beim Erreichen der Position auf |
| Bei zentriertem Leader weicht der simulierte Arm um einige Grad ab | Fester Offset durch asymmetrischen Kalibrierbereich – mit `so101_leader_trim` automatisch kompensieren ([05](05-leader-digital-twin.md)) |
| Der Arm bewegt sich beim Verbinden plötzlich | Ist Designverhalten: Der reale Roboter bekommt Drehmoment und fährt zur Mittelstellung/Leader-Pose; Platz in Reichweite freihalten |
| Nach dem Beenden mit Ctrl-C wird der Arm weich und sinkt | Normal: Beim Trennen wird das Drehmoment abgeschaltet, kurz festhalten |
| Tippen während Teleoperation/Aufzeichnung treibt den Arm | Tastaturüberwachung **global und schluckt keine Tasten**: In jedem Fenster gelangen belegte Tasten (auch Pinyin-Buchstaben) in die Tastenwarteschlange. Im Tastaturmodus während Teleoperation/Aufzeichnung nicht tippen; der Leader-Modus hat dieses Problem nicht |

## Aufzeichnung

| Symptom | Ursache und Lösung |
| --- | --- |
| Nach dem Beenden mit `q` werden die während der Sitzung gedrückten Buchstaben „auf einmal in die Kommandozeile gespuckt“ | Rückstau-Echo des Windows-Konsolen-Eingabepuffers; der Starter enthält bereits `drain_pending_keys()` zum Leeren (nur ältere Sitzungen zeigen dieses Verhalten) |
| action span einer Episode durchgehend 0 | Leeraufnahme (die Person hat sich nicht bewegt) – vor der Aufnahme kurz bewegen oder die Episode nachträglich löschen |
| Der Fehler in der ersten Sekunde einer Episode ist sehr groß | Konvergenzabschnitt: Beim Aufnahmestart steht der Follower noch in der Ausgangspose, der Leader bereits woanders; den Leader vorher nahe der Mittelstellung abstellen vermeidet das |
| `--dataset.root` als Elternverzeichnis konfiguriert, Dataset „verschwunden“ | **root ist das Dataset-Verzeichnis selbst**; für jede Aufnahme ein neues root verwenden |
| Unterschied zwischen `Esc` und `q` | `q` stoppt nur die Aufzeichnung; `Esc` trennt zusätzlich die Tastatur-Teleoperation. Beide beenden sauber (behoben); `q` verwenden |
| Beim Speichern `ValueError: You must add one or several frames...`, der Prozess beendet sich mit Fehler | Im **Zwischenraum** zwischen Episoden wurde `→`/`n` zu oft gedrückt (häufigster Fall: Speichern + zweispurige Videokodierung pausiert einige zehn Sekunden, die Konsole wirkt eingefroren, mehrmals gedrückt) → das Flag bleibt bis zum Beginn der nächsten Episode erhalten und wird dort verbraucht → **0-Frame-Leer-Episode**, Upstream stürzt beim Speichern einer leeren Episode ab (bekannte Grenze von lerobot). **Bereits gespeicherte Episoden sind nicht betroffen, die Daten sind intakt**; Sitzung neu starten und weiter aufnehmen. **Schutz ergänzt** (2026-10-16): `record.py` löscht zu Beginn jeder Episode die im Zwischenraum liegengebliebenen `→`/`←`-Flags (Tasten wirken während der Aufzeichnung weiterhin normal); vor dem Speichern wird `saving the episode + encoding videos now...` ausgegeben; Regressionstest `smoke_test.py` [7] |
| Beim Aufnahmestart `KeyError: 'wrist'` (bei Datasets mit Bildern) | Das erste Kamerabild war noch nicht gerendert, als die Aufzeichnungsschleife die Beobachtung las; **behoben** (2026-10-16): `connect()` des Roboter-Plugins wartet jetzt, bis das erste Bild bereit ist |
| Skripte mit Video melden `BrokenProcessPool` / `Invalid argument: '<stdin>'` | Die Videokodierung läuft über einen **Multiprocessing-Pool**, Kindprozesse müssen das Einstiegsmodul anhand des Dateipfads neu importieren – wird das Aufzeichnungsskript mit `python - <<EOF` (stdin) ausgeführt, stürzt es ab. Skript als echte `.py`-Datei speichern und ausführen (der echte Einstieg `record.py` ist nicht betroffen) |
| Beim Speichern einer Episode meldet der Encoder `SvtMalloc[fatal]: allocate memory failed ... av.error.MemoryError: [Errno 12] ... 'avcodec_open2(libsvtav1)'`, die gesamte Sitzung beendet sich | Der Upstream-Standardencoder **libsvtav1** scheitert beim gleichzeitigen Öffnen zweier Encoder-Streams (wrist+top) an einer einmaligen großen Speicherzuweisung (unter Last von Simulation + Vorschaufenstern wahrscheinlicher; am 2026-10-16 reproduziert). **Behoben**: `record.py` injiziert standardmäßig `--dataset.rgb_encoder.vcodec=h264` (zweispurige h264-Kodierung verifiziert; explizit übergebener vcodec überschreibt). Bereits gespeicherte Episoden sind verlustfrei; ein Absturz kann `tmp*/` und verwaiste Parquet-Dateien im Dataset-Verzeichnis hinterlassen (wie bei run2 bereinigen) |
| Während der Aufzeichnung ruckelt das Bild (besonders nach `→`), die Bedienung ist aber nicht verzögert | Es ruckelt das **Speicher-/Encoding-Fenster**: Die Encoder-Prozesse lasten standardmäßig alle CPU-Kerne aus (zwei Videostreams gleichzeitig), während der Simulations-Thread noch 5 Bilder rendert (bei integrierter Grafik deutlicher). Die Regelschleife selbst ist nicht betroffen – maßgeblich sind die Cadence-Zahlen (durchgehend 29,97 Hz, 0 Ticks über Budget). **Entschärft** (2026-10-16): `record.py` setzt standardmäßig `--dataset.encoder_threads=2` (2 Threads pro Encoder); die Aktualisierung der Kameravorschaufenster wurde auf 15 Hz gesenkt (`--robot.preview_fps`). Je kürzer die Episode, desto größer der Anteil des Speicherfensters und desto stärker das Ruckeln; ganz vermeiden lässt es sich mit `--dataset.streaming_encoding=true` (Kodierung während der Aufnahme, vom Upstream empfohlen, noch nicht gemessen) |
| Beim Speichern einer Episode meldet der Encoder **Speicherzuweisungsfehler**, die gesamte Sitzung beendet sich (svtav1 `SvtMalloc`, x264 `malloc ... failed`, `avcodec_open2`-Fehler gehören alle dazu) | Das Commit-Memory des Systems liegt auf diesem Rechner dauerhaft nahe am Limit (Messung am 2026-10-16: **105,9 GB / 119,7 GB**, Rechner seit 29 Tagen durchgehend an). Bei jedem Speichern werden 2 Encoder-Prozesse neu gestartet (jeder lädt torch/av, großer Commit-Spitzenwert); starten sie am Rand des Limits gleichzeitig, geht es schief. **Entschärft**: `record.py` versucht bei Encoding-Fehlern jetzt **automatisch einmal erneut** (transiente Fehler führen nicht mehr zum Verlust einer Episode), und die Log-Flut während des Speicherns ist stummgeschaltet (`av.logging.set_libav_level` + HF-Fortschrittsbalken). **Grundlösung = Rechner neu starten** (angesammeltes Commit-Memory / Kernel-Leck beseitigen; Userspace-Prozesse belegen nur 27 GB, der Rest liegt im Kernel/Treiber und lässt sich nicht beenden); Selbstprüfung: `Get-Counter '\Memory\Committed Bytes'` gegen `'\Memory\Commit Limit'` |

## Hardware

| Symptom | Ursache und Lösung |
| --- | --- |
| COM-Portnummer anders als beim letzten Mal | Die Nummer ändert sich beim Ein-/Ausstecken oder Portwechsel; jedes Mal zuerst die Ports auflisten ([03](03-hardware-calibration.md)) |
| Die schreibgeschützte Prüfung meldet fehlende Servos | Verkabelung/Stromversorgung; zuerst Treiberboard und Pin-Belegung prüfen, nicht vorschnell kalibrieren |
| `shoulder_lift`-Richtung entgegen der Intuition (Simulation) | Die positive Richtung dieses Modells zeigt nach unten; vor dem Mapping das Vorzeichen prüfen ([02](02-sim-model-verification.md)) |

## Designhinweise (warum es so gemacht ist)

- **MuJoCo schreibt Mesh-Vertexdaten um**: Nach dem Laden eines `<mesh>` speichert `mjModel.mesh_vert` die Vertices im **Koordinatensystem des Meshes selbst**
  (Ursprung auf den Vertex-Schwerpunkt verschoben, Achsen umsortiert), nicht mehr in den Originalkoordinaten der Datei – wer daraus direkt Bounding-Boxen berechnet oder CAD-Maße ableitet,
  erhält falsche Ergebnisse (die Darstellung ist nicht betroffen). Für echte CAD-Geometrie die Originaldatei parsen (Vorgehen in `preview_mount.py` /
  `step_to_stl.py`). Einmal darauf hereingefallen: echte Halterungsmaße 54,3 × 35,0 × 75,0 mm.
- **Die Blickrichtung einer MuJoCo-Kamera ist die −Z ihrer Koordinaten**: Das `<camera>`-Element schaut nicht in seine eigene +Z-Richtung (Richtung der Objektivwölbung). In der ersten
  Kameraversion war das Objektiv in +Z gebaut und das Element mit identity ausgerichtet → das Bild wurde tatsächlich von der Rückseite der Platine „rückwärts“ gesehen, **Objektivrichtung und Bildrichtung
  waren genau entgegengesetzt** (die Ursache dafür, dass beim Einstellen „die Drehrichtung nicht zum Bild passte“; am 2026-10-16 mit Rot-/Blauplatten-Vergleichsrendering lokalisiert).
  Fix: Kameraelement um 180° um Y gedreht (`view.quat = RPY(0,180,0)`, einheitlich an drei Stellen: preview_mount / adjust_camera / Roboter-Plugin);
  `adjust_camera.py` hat ein neues Echtzeitfenster „sim_cam live view“, Kamera-Einstellung mit sofortiger Sicht (WYSIWYG).
- **Der Greifer des offiziellen Tutorial-MJCF ist ein „Schnabel“-Punktkontaktgreifer**: Die beiden Zahnspitzen schließen bis auf ~2,3 mm Punktkontakt, es gibt praktisch keine nutzbare Greiffläche.
  Systematische Physikexperimente (2026-10-16, Hunderte Kombinationen) ergaben: Ein Würfel an beliebiger Position nahe der Zahnöffnung wird beim Schließen über ~100°
  weggeschoben/keilförmig herausgedrückt und kann nicht gegriffen werden (gilt für 16–34-mm-Würfel; mechanischer Stellweg und Drehmoment sind für sich genommen normal). **Hinweis: nicht durch „ergänzende Kollisionsplättchen“
  reparieren** – es wurde versucht, den beiden Backen Zahnplatten hinzuzufügen (verbessert das Greifen deutlich), aber das ist **Geometrie, die am realen Roboter nicht existiert**; eine trainierte Policy würde sich darauf verlassen
  und sim2real verfälschen, daher wieder entfernt. Die richtige Lösung ist, **die Greifergeometrie des offiziellen Modells durch die des realen Roboters zu ersetzen** (z. B.
  SO-ARM101 aus mujoco_menagerie oder eigene CAD-Rekonstruktion), während die physikalischen Parameter mit dem realen Roboter übereinstimmen sollten.
- **Die offiziellen Standardkontaktparameter sind zu „weich“ und verursachen physikalisches Durchdringen**: Die `solref`-Zeitkonstante beträgt standardmäßig 20 ms; bei schnellen/dünnen Kontakten
  (Würfel fällt auf dünne Greiferfläche, Schließbewegung) durchdringen sich die Objekte, „bevor Kraft entsteht“ – Symptom: „der Würfel fällt direkt durch die Greiferfläche“.
  Fix (2026-10-16): Kontaktparameter gehärtet – `harden_mesh_contacts` härtet nach dem Kompilieren `solref` aller Mesh-Kollisionskörper auf denselben Wert wie die Zahnflächen in menagerie (0,01 s), Würfelkontakte ebenso. Reine Physiktreue-Korrektur, keine Geometrie hinzugefügt.
- **Der Simulationsroboter wurde auf das SO-ARM100-Modell aus mujoco_menagerie migriert** (2026-10-16): Das MJCF aus dem ursprünglichen Tutorial-Zip ist ein Kinematik-Demostück, dessen Greifer nicht greifen kann;
  das menagerie-Modell orientiert sich am CAD des realen Roboters – der Greifer hat spezielle Kollisionszahnflächen und harte Kontaktparameter,
  an allen vier Zahnpositionen (flach→tief) stoppt, greift und hebt es einen 34-mm-Würfel (gemessen). Kernpunkte der Migration: Modell vendored unter
  `assets/menagerie_so_arm100/` (Apache-2.0, mit LICENSE); Gelenk-Mapping und Einheiten/Vorzeichen in `MODEL_JOINT`
  (Gelenk für Gelenk anhand von Weltbewegungsmessungen gegen das alte Modell abgeglichen; wrist_roll-Vorzeichen noch durch Teleoperation am realen Roboter zu bestätigen); die Modellbasis um +90° um Z gedreht, damit die
  Arbeitsfront nach +x zeigt; die Halterung wurde seitlich am Fixed_Jaw (Servo 6) befestigt (zuerst per parsender Suche lokalisiert, am 2026-10-16 vom Nutzer anhand eines Fotos des realen Roboters
  mit `adjust_mount.py --model menagerie` manuell feinjustiert: `[0.1, -0.7, 24.7]mm`, `RPY [0.34, -27.20, 89.51]°`). Die alten Tutorial-Modelle und -Werkzeuge bleiben unverändert erhalten und können jederzeit zum Vergleich herangezogen werden.
- **Warum eine uv-Projektumgebung statt conda**: `.venv` liegt im selben Verzeichnis wie das Projekt, Versionen werden durch `uv.lock` fixiert, Verzeichnis löschen genügt zum Aufräumen,
  und sie ist vollständig von den conda-Umgebungen des Rechners isoliert; `uv run` installiert nie etwas in eine aktivierte conda-Umgebung. Die conda-Umgebung `lerobot` dieses Rechners
  zeigt auf eine **andere Repo-Kopie** (`lerobot-main`); beide stören sich nicht.
- **Warum alle Plugins in `examples/so101_mujoco/` liegen**: Anbindung über den offiziellen Registrierungsmechanismus (`register_subclass`),
  **null Änderungen am lerobot-Quellcode**; für Upstream-Updates genügt ein erneutes Sync.
