# SO-ARM101 × MuJoCo – Tutorial für den kompletten Workflow (Index)

> 🌐 Languages: [简体中文](../README.md) · [English](../en/README.md) · **Deutsch** · [Español](../es/README.md) · [Français](../fr/README.md) · [Italiano](../it/README.md) · [日本語](../ja/README.md) · [한국어](../ko/README.md) · [Português (BR)](../pt-br/README.md) · [Português (PT)](../pt-pt/README.md) · [繁體中文](../zh-hant/README.md)

> Dieses Tutorial dokumentiert und reproduziert den **kompletten Workflow aus Simulation + realem Roboter** des SO-ARM101: von der Einrichtung der Umgebung über die Modellvalidierung und die Kalibrierung am realen Gerät
> bis zur Tastatur-/Leader-Teleoperation sowie Datenaufzeichnung und -wiedergabe. Alle Befehle wurden am 2026-10-15 in einer Sitzung mit realem Roboter + Simulation verifiziert.
>
> Zielgruppe: Nutzer des Juxi SO-ARM101-Kits und interne Ingenieure. Vorkenntnisse zu MuJoCo oder LeRobot sind nicht erforderlich.

## Workflow-Karte (zwei Spuren, ein gemeinsamer Komponentensatz)

```
                              ┌────────── Gemeinsame Komponenten ──────────────────────────┐
                              │  Dataset-Format (LeRobotDataset) · Wiedergabe · Training   │
                              └────────────────────────────────────────────────────────────┘
                                        ▲                           ▲
        ┌── Reale Roboter ──────────────┘                           └────────────────── Simulation ─────────────┐
        │  Steuerung: Leader-Arm (physisch) / Tastatur              Steuerung: Tastatur / Leader-Arm (physisch) │
        │  Gesteuert: Follower (COM-Seriell)                        Gesteuert: MuJoCo-Simulations-Follower      │
        │  Befehl: --robot.type=so101_follower                      Befehl: --robot.type=so101_mujoco           │
        └───────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

| Kapitel | Inhalt | Ergebnis |
| --- | --- | --- |
| [01 Umgebung einrichten](01-environment.md) | uv-Umgebung, Dependency-Extras, Windows-Hinweise | Lauffähige Umgebung |
| [02 Validierung des Simulationsmodells](02-sim-model-verification.md) | Laden/Vergleich/Rendering-Ansteuerung der drei MJCF-Modelle | Gewissheit über Modell und Simulationsverhalten |
| [03 Verbindung zum realen Roboter und Kalibrierung](03-hardware-calibration.md) | Serielle Schnittstelle erkennen, schreibgeschützte Erstprüfung, Kalibrierung von Follower/Leader | Zwei von der Software erkannte Arme |
| [04 Tastatur-Teleoperation](04-keyboard-teleop.md) | Realen Roboter/Simulation per Tastatur steuern, Raten-Tuning, sichere Geschwindigkeitsbegrenzung | Schnellste manuelle Steuerungsmethode |
| [05 Digitaler Zwilling des Leader-Arms](05-leader-digital-twin.md) | Physischer Leader-Arm steuert simulierten Follower, Nullpunkt-Feintuning | Digital-Twin-Demo und Datenerfassung |
| [06 Datenaufzeichnung und -wiedergabe](06-record-and-replay.md) | Real/Simulation aufzeichnen, Episodensteuerung, Wiedergabe, Inspektionsskript | Trainierbares Dataset |
| [07 Häufige Probleme und Erfahrungen](07-troubleshooting.md) | Alle in diesem Workflow aufgetretenen Fallstricke und Lösungen | Handbuch zur Fehlerbehebung |
| [08 Weiterer Fahrplan](08-roadmap.md) | Kamera, Objektszenen, automatische Datengenerierung, Training | Nächste Schritte |
| [09 Vollständiges Nutzungstutorial](09-usage-tutorial.md) | Arm starten → Aufzeichnen → Prüfen → Videos ansehen → Training → Simulations-Deployment in einem Durchgang; inkl. conda-Umgebungsalternative | Von null zum brauchbaren Dataset und dann zur Policy im Einsatz |

## Drei Konventionen, die man sich merken muss

1. **Einheitensystem (drei Parteien abgestimmt)**: Die fünf Körpergelenke verwenden **−100~100** (Weganteil, 0 = Mitte des Stellwegs), der Greifer **0~100**
   (0 = geschlossen). Realer Roboter (`use_degrees=false`), Simulation und Leader-Arm sind alle auf diese Konvention abgestimmt; die aufgezeichneten Datasets sind strukturell identisch mit offiziellen realen Datasets wie
   `lerobot/svla_so101_pickplace` (6-dimensionaler Vektor + Gelenknamen).
2. **Rollenentsprechung**: Das gesteuerte Objekt (realer Roboter oder Simulation) wird immer mit `--robot.*` konfiguriert; das Steuergerät (Tastatur/Leader-Arm) immer mit `--teleop.*`.
3. **Befehlpräfix auf diesem Rechner**: Alle `uv`-Befehle auf dieser Entwicklungsmaschine benötigen zuerst ein Cache-Verzeichnis (Grund siehe [07](07-troubleshooting.md)):

   ```bash
   export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
   ```

## Gemessene Umgebung

| Element | Version |
| --- | --- |
| System | Windows 11 |
| Python / uv | 3.12.9 / 0.12.5 |
| lerobot | 0.6.2 (dieses Repository, isolierte projektinterne `.venv`, beeinflusst conda nicht) |
| MuJoCo | 3.16.0 |
| PyTorch | 2.11.0 (CPU-Version) |
| Hardware | SO-ARM101 Leader (COM163) + Follower (COM172), CH343-Seriellchip |
