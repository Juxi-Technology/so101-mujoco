# 02 · Verifica del modello di simulazione (caricamento e azionamento MJCF)

## Origine dei modelli

I tre modelli MJCF pubblici del SO-ARM101 sono stati tutti verificati e sono utilizzabili in questo progetto:

| Abbreviazione | File | Origine |
| --- | --- | --- |
| Ufficiale-nuova calibrazione | `SO101/so101_new_calib.xml` | Repository ufficiale TheRobotStudio/SO-ARM100; **nello zip del tutorial di questo repository è inclusa una copia identica** (byte per byte) |
| Ufficiale-vecchia calibrazione | `SO101/so101_old_calib.xml` | Stesso repository (non presente nello zip, da scaricare) |
| Pacchetto descrittivo ROS2 | `so_arm101_description/mjcf/so_arm101.xml` | Allegato del tutorial `SO-ARM101_ROS2.zip` di questo repository |

Nota: la procedura di estrazione dello zip era fornita dalla prima versione di `so101_assets.py` ed è conservata per consultazione; dal 2026-10-16 il robot simulato è migrato al
**modello SO-ARM100 di mujoco_menagerie** (vendored in `assets/menagerie_so_arm100/`; motivi e punti chiave della migrazione nella nota di progettazione in [07](07-troubleshooting.md)).

## Verifica di azionamento e rendering

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
uv run --frozen --with mujoco python examples/so101_mujoco/load_and_drive.py \
    --model "<模型路径>" --out-dir out
```

Lo script stampa un riepilogo strutturale (giunti/attuatori/guadagni/intervalli) e genera un video di verifica con "spazzata sequenziale dei sei giunti + seno coordinato" e fotogrammi statici.
Un esempio di riepilogo strutturale è in `reports/` (fornito con il repository); i video di confronto (`media/`) sono di grandi dimensioni e non vengono distribuiti con il repository: possono essere rigenerati in qualsiasi momento con il comando qui sopra.

## Differenze chiave tra i tre modelli (misurate)

| Voce | Ufficiale-nuova calibrazione | Ufficiale-vecchia calibrazione | Pacchetto descrittivo ROS2 |
| --- | --- | --- | --- |
| Semantica dello zero | **punto medio della corsa** del giunto | posizione di **estensione completa** orizzontale | punto medio della corsa |
| Nomi dei giunti | `shoulder_pan` | idem | `shoulder_pan_joint` (suffisso) |
| Guadagno di posizione | kp=998.22, kv=2.731 | **kp=17.8, kv=0** | kp=998.22 |
| Unità del gripper | hinge in radianti | hinge in radianti | **normalizzato 0~1** |
| Esclusione delle autocolisioni | no | no | sì (6 coppie) |

**Errore di inseguimento misurato**: la nuova calibrazione e il pacchetto descrittivo hanno un errore di mantenimento da fermo di 0.0005 rad, la vecchia calibrazione 0.03 rad (cedimento di circa 1.7°, kp più debole di 56 volte).
Valutando la stessa policy in simulazione, cambiando modello si ottengono dinamiche diverse: annota sempre quale modello hai usato.

## Comportamenti del modello da ricordare

1. **La direzione positiva di `shoulder_lift` punta verso il basso**: nella coppia di azionamento il "movimento verso il basso" usa angoli positivi; verifica sempre il segno prima di creare mappature di teleoperazione o conversioni di dati.
2. **Toccare il suolo blocca il movimento**: al limite del movimento verso il basso la punta delle dita tocca il terreno e viene fermata (lo script include una protezione di 8 cm dal suolo che riduce automaticamente l'ampiezza).
3. Il modello ufficiale non ha telecamera né keyframe; esiste la variante con telecamera `so101_new_calib_camera.xml`, utilizzabile in seguito per registrare dati visivi.
