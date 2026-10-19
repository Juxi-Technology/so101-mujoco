# 05 · Digitaler Zwilling des Leader-Arms (physischer Arm steuert simulierten Arm)

Den **physischen Leader-Arm** von Hand bewegen und den **simulierten Follower im MuJoCo-Fenster** in Echtzeit spiegeln lassen – die richtige Art, eine Digital-Twin-Demo
oder Simulationsdaten zu erfassen.

## Voraussetzungen

Der Leader-Arm ist kalibriert (siehe [03](03-hardware-calibration.md)), serieller Port hier beispielhaft `COM163`.

## Befehl

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
uv run --frozen --with mujoco python examples/so101_mujoco/teleoperate.py \
    --robot.type=so101_mujoco \
    --teleop.type=so101_leader_trim --teleop.port=COM163 --teleop.id=juxi_leader \
    --teleop.use_degrees=false
```

- `--robot.type=so101_mujoco`: Das gesteuerte Objekt ist der Simulationsarm, das Fenster öffnet sich automatisch;
- `--teleop.*`: Das Steuergerät ist der physische Leader-Arm (reines Lesen, nie Drehmoment, null Risiko für den Leader);
- `--teleop.use_degrees=false`: **Zwingend**. Damit stimmen die vom Leader ausgegebenen Einheiten (Weganteils-System) mit dem Simulationsarm überein.

Ändert man `--robot.type` zu `so101_follower --robot.port=COM172 --robot.id=juxi_so101 --robot.max_relative_target=5`,
ergibt das das übliche Kit-Spiel „physischer Leader → realer Follower“; dieselbe Leader-Kalibrierung ist gültig.

## Was tun, wenn der Nullpunkt versetzt ist: automatische Mittenkorrektur (`so101_leader_trim`)

**Symptom**: Der Leader steht „sichtbar in der Mitte“, der simulierte Arm weicht aber um einige Grad ab.

**Prinzip**: Der Normalisierungs-Nullpunkt von lerobot = **Mittelpunkt des bei der Kalibrierung durchfahrenen Bereichs** `(min+max)/2`; die beim Kalibrier-Enter eingenommene
„Mittelstellung“ wird jedoch als Rohwert 2048 gespeichert. Solange der mechanische Stellweg eines Gelenks asymmetrisch ist, weichen die beiden „Mittelpunkte“ immer um einen festen Betrag ab
(gemessen an Servo 1: aufgezeichneter Bereich 776–3457, Mittelpunkt 2116, Differenz zu 2048 = 68 Counts ≈ **5,6°**).
**Diese Abweichung lässt sich durch erneute Kalibrierung nicht beseitigen** (die Asymmetrie des Stellwegs ist durch die Mechanik vorgegeben) und muss in der Software kompensiert werden.

**Lösung**: Das Plugin `so101_leader_trim` berechnet die Kompensation jedes Gelenks automatisch nach Formel aus der Kalibrierungsdatei und zieht sie in Echtzeit ab;
nach erneuter Kalibrierung folgt sie automatisch, ohne manuelles Nachjustieren:

```
Kompensationᵢ = (2048 − minᵢ) / (maxᵢ − minᵢ) × 200 − 100
```

Am Rechner gemessene wirksame Werte (werden im Startlog ausgegeben):

| Gelenk | Kompensation (Einheiten) |
| --- | --- |
| shoulder_pan | −5.11 |
| shoulder_lift | −0.92 |
| elbow_flex | +2.54 |
| wrist_flex | +0.69 |

Die übrigen Gelenke weichen um <0,05 ab und benötigen keine Kompensation; Greifer (0~100) und Gradmodus nehmen am Feintuning nicht teil.

> Entwicklernotiz: Das `name` dieses Plugins muss `"so_leader"` bleiben – `name` ist der Suchverzeichnis-Schlüssel der Kalibrierungsdatei;
> ein eigener Typname führt dazu, dass die Kalibrierungsdatei nicht gefunden wird und fälschlich der erneute Kalibrierungsablauf ausgelöst wird.
