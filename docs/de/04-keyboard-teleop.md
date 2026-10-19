# 04 · Tastatur-Teleoperation

Gelenke per Tastatur „schrittweise“ verfahren, um den realen oder simulierten Arm manuell zu steuern – die schnellste Steuerungsmethode, wenn kein Leader-Arm vorhanden ist, und zugleich ein Mittel zur Aufzeichnung von Demonstrationsdaten.

## Befehl

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'

# Realer Follower
uv run --frozen --with mujoco python examples/so101_mujoco/teleoperate.py \
    --robot.type=so101_follower --robot.port=COM172 --robot.id=juxi_so101 \
    --robot.use_degrees=false --robot.max_relative_target=5 \
    --teleop.type=so101_keyboard --teleop.rate=150

# Simulierter Follower (MuJoCo-Fenster öffnet sich automatisch)
uv run --frozen --with mujoco python examples/so101_mujoco/teleoperate.py \
    --teleop.rate=150
```

(In `teleoperate.py` sind standardmäßig `--robot.type=so101_mujoco --teleop.type=so101_keyboard` eingestellt.)

## Tasten (wirken beim Gedrückthalten, globale Überwachung – unabhängig vom fokussierten Fenster)

| Taste | Aktion | Taste | Aktion |
| --- | --- | --- | --- |
| `w` / `s` | shoulder_lift hoch / runter | `a` / `z` | shoulder_pan links / rechts |
| `e` / `d` | elbow_flex strecken / beugen | `t` / `g` | wrist_flex + / − |
| `y` / `h` | wrist_roll + / − | `u` / `j` | Greifer öffnen / schließen |

Die Tasten sind **bewusst so gewählt, dass sie die Aufzeichnungs-Steuertasten** (`n/r/q`, Pfeiltasten, `Esc`) **nicht belegen**, sodass Teleoperation und Aufzeichnung gleichzeitig laufen können.

## Wichtige Parameter

| Parameter | Wirkung | Empfohlener Wert |
| --- | --- | --- |
| `--teleop.rate` | Zielgeschwindigkeit beim Gedrückthalten (Einheiten/Sekunde) | Standard 60 ist eher langsam; am realen Roboter fühlt sich **150** passend an |
| `--robot.max_relative_target` | Maximale Bewegung des Gelenks pro Steuerzyklus (sichere Geschwindigkeitsbegrenzung) | Realer Roboter **5** (60-Hz-Teleoperation) / **10** (30-Hz-Aufzeichnung) |
| `--robot.use_degrees=false` | Weganteils-System (−100~100) statt Gradsystem verwenden | **Am realen Roboter zwingend**, sonst passen die Einheiten nicht (Simulation ist standardmäßig konsistent) |

## Verhalten

- **Während der Teleoperation nicht tippen**: Die Tastaturüberwachung ist **global und schluckt keine Tasten** – in jedem Fenster auf dem Computer lösen die belegten Tasten
  (`w a s z e d t g y h u j`, auch Pinyin in Chatfeldern) gleichzeitig den Arm aus. Im Leader-Arm-Modus gibt es dieses Problem nicht.
- **Der Arm bewegt sich beim Verbinden**: Der reale Follower bekommt zuerst Drehmoment (wird steif) und fährt dann zur „Mittelstellung“ (Ziel vor dem Tastendruck);
  der simulierte Arm konvergiert direkt zur Mittelstellung. Platz in Reichweite freihalten.
- **Beenden**: `Ctrl-C` im Terminal (oder `Esc` drücken; die Tastaturüberwachung trennt sich und beendet sauber). Danach **verliert der reale Roboter das Drehmoment und wird weich** –
  kurz festhalten, das ist normales Verhalten.
- **Die vielen `clamped to be safe`-WARNUNGEN im Startlog** sind normale Ausgaben des Geschwindigkeitsbegrenzers beim „Aufholen“; nach Erreichen der Position hören sie automatisch auf.
