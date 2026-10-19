# 02 · Validierung des Simulationsmodells (MJCF laden und ansteuern)

## Modellquellen

Die drei öffentlichen MJCF-Modelle des SO-ARM101 sind in diesem Projekt alle als funktionsfähig verifiziert:

| Kurzname | Datei | Quelle |
| --- | --- | --- |
| Offiziell – neue Kalibrierung | `SO101/so101_new_calib.xml` | Offizielles Repository TheRobotStudio/SO-ARM100; **im Tutorial-Zip dieses Repositories liegt eine identische Kopie bei** (byteweise gleich) |
| Offiziell – alte Kalibrierung | `SO101/so101_old_calib.xml` | Dasselbe Repository (nicht im Zip enthalten, muss heruntergeladen werden) |
| ROS2-Beschreibungspaket | `so_arm101_description/mjcf/so_arm101.xml` | Tutorial-Anhang dieses Repositories `SO-ARM101_ROS2.zip` |

Hinweis: Der Zip-Extraktionsablauf stammt aus einer früheren Version von `so101_assets.py` und bleibt nachvollziehbar erhalten; seit dem 2026-10-16 wurde der Simulationsroboter auf
**das SO-ARM100-Modell aus mujoco_menagerie** umgestellt (vendored unter `assets/menagerie_so_arm100/`; Gründe und Kernpunkte der Migration siehe Designhinweise in [07](07-troubleshooting.md)).

## Ansteuerungs- und Rendering-Validierung

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
uv run --frozen --with mujoco python examples/so101_mujoco/load_and_drive.py \
    --model "<模型路径>" --out-dir out
```

Das Skript gibt eine Strukturzusammenfassung aus (Gelenke/Aktoren/Verstärkungen/Bereiche), rendert ein Validierungsvideo aus „sechs Gelenke nacheinander durchfahren + koordinierte Sinuskurve“ und Standbilder.
Beispiele der Strukturzusammenfassung siehe `reports/` (im Repository enthalten); die Vergleichsvideos (`media/`) sind zu groß und werden nicht mit dem Repository ausgeliefert – mit dem obigen Befehl lassen sie sich jederzeit neu erzeugen.

## Wesentliche Unterschiede der drei Modelle (gemessen)

| Element | Offiziell – neue Kalibrierung | Offiziell – alte Kalibrierung | ROS2-Beschreibungspaket |
| --- | --- | --- | --- |
| Semantik des Nullpunkts | **Mitte des Gelenkstellwegs** | horizontal **vollständig gestreckt** | Mitte des Stellwegs |
| Gelenknamen | `shoulder_pan` | wie links | `shoulder_pan_joint` (Suffix) |
| Positionsverstärkung | kp=998.22, kv=2.731 | **kp=17.8, kv=0** | kp=998.22 |
| Greifereinheit | Bogenmaß, Hinge | Bogenmaß, Hinge | **0~1 normalisiert** |
| Selbstkollisionsausschluss | keiner | keiner | vorhanden (6 Paare) |

**Gemessener Tracking-Fehler**: Neue Kalibrierung und Beschreibungspaket halten im Stillstand eine Abweichung von 0,0005 rad, die alte Kalibrierung 0,03 rad (Absinken um ca. 1,7°, kp um Faktor 56 schwächer).
Wird dieselbe Policy in der Simulation mit einem anderen Modell evaluiert, ergeben sich andere Dynamiken – darauf achten, welche Version aufgezeichnet wurde.

## Modellverhalten, das man sich merken muss

1. **`shoulder_lift` positive Richtung zeigt nach unten**: Beim Ansteuern wird „Absenken“ mit positivem Winkel verwendet; bei Teleoperations-Mapping oder Datenumrechnung zuerst das Vorzeichen prüfen.
2. **Bodenkontakt blockiert**: Am unteren Anschlag berührt die Fingerspitze den Boden und wird gestoppt (das Skript hat einen eingebauten 8-cm-Bodenabstandsschutz, der die Amplitude automatisch begrenzt).
3. Die offiziellen Modelle haben keine Kamera und kein Keyframe; die Variante mit Kamera `so101_new_calib_camera.xml` existiert und kann später für visuelle Daten genutzt werden.
