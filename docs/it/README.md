# SO-ARM101 × MuJoCo — Tutorial completo del flusso di lavoro (indice)

> 🌐 Languages: [简体中文](../README.md) · [English](../en/README.md) · [Deutsch](../de/README.md) · [Español](../es/README.md) · [Français](../fr/README.md) · **Italiano** · [日本語](../ja/README.md) · [한국어](../ko/README.md) · [Português (BR)](../pt-br/README.md) · [Português (PT)](../pt-pt/README.md) · [繁體中文](../zh-hant/README.md)

> Questo tutorial documenta e riproduce il **flusso di lavoro completo simulazione + robot reale** del SO-ARM101: dalla configurazione dell'ambiente, alla verifica del modello, alla calibrazione del robot reale,
> fino alla teleoperazione da tastiera/braccio leader e alla registrazione e riproduzione dei dati. Tutti i comandi sono stati verificati in una sessione reale + simulazione del 2026-10-15.
>
> Destinatari: utenti del kit Juxi SO-ARM101 e ingegneri interni. Non è richiesta alcuna conoscenza preliminare di MuJoCo o LeRobot.

## Mappa del flusso completo (due binari, un unico set di componenti)

```
                         ┌──────────────── Componenti condivisi ──────────────────────────────┐
                         │  Formato dataset (LeRobotDataset) · Replay · Addestramento futuro  │
                         └────────────────────────────────────────────────────────────────────┘
                                       ▲                       ▲
        ┌── Binario robot reale ──────┘                        └──────────── Binario simulazione ──┐
        │  Controllo: leader (fisico) / tastiera        Controllo: tastiera / leader (fisico)      │
        │  Controllato: follower reale (seriale COM)    Controllato: follower simulato MuJoCo      │
        │  Comando: --robot.type=so101_follower         Comando: --robot.type=so101_mujoco         │
        └──────────────────────────────────────────────────────────────────────────────────────────┘
```

| Cap. | Contenuto | Cosa otterrai |
| --- | --- | --- |
| [01 Preparazione dell'ambiente](01-environment.md) | Ambiente uv, extra delle dipendenze, note per Windows | Un ambiente funzionante |
| [02 Verifica del modello di simulazione](02-sim-model-verification.md) | Caricamento/confronto/rendering con azionamento dei tre modelli MJCF | Certezza sul modello e sul comportamento della simulazione |
| [03 Connessione al robot reale e calibrazione](03-hardware-calibration.md) | Identificazione della porta seriale, controllo iniziale in sola lettura, calibrazione follower/leader | Due bracci riconosciuti dal software |
| [04 Teleoperazione da tastiera](04-keyboard-teleop.md) | Controllo da tastiera di robot reale/simulazione, regolazione della velocità, limitazione di sicurezza | Il modo più rapido di controllo manuale |
| [05 Digital twin del braccio leader](05-leader-digital-twin.md) | Braccio leader fisico che guida il follower simulato, micro-regolazione dello zero | Demo di digital twin e acquisizione dati |
| [06 Registrazione e riproduzione dei dati](06-record-and-replay.md) | Registrazione su robot reale/simulazione, controllo degli episodi, replay, script di ispezione | Un dataset addestrabile |
| [07 Problemi comuni ed esperienze](07-troubleshooting.md) | Tutti gli ostacoli incontrati in questo flusso e le relative soluzioni | Un manuale di troubleshooting |
| [08 Roadmap futura](08-roadmap.md) | Telecamera, scene con oggetti, generazione automatica dei dati, addestramento | Il piano dei prossimi passi |
| [09 Tutorial d'uso completo](09-usage-tutorial.md) | Percorso completo: braccio → registrazione → ispezione → video → addestramento → deployment in simulazione; include l'alternativa con ambiente conda | Da zero a un dataset valido, fino alla policy in azione |

## Tre convenzioni da ricordare

1. **Sistema di unità (allineamento triplo)**: i cinque giunti del corpo usano **−100~100** (proporzione della corsa, 0 = punto medio della corsa), il gripper usa **0~100**
   (0 = chiuso). Robot reale (`use_degrees=false`), simulazione e braccio leader sono tutti allineati a questa convenzione; i dataset registrati hanno la stessa struttura dei dataset reali ufficiali come
   `lerobot/svla_so101_pickplace` (vettore a 6 dimensioni + nomi dei giunti).
2. **Corrispondenza dei ruoli**: l'oggetto controllato (robot reale o simulazione) usa sempre `--robot.*`; il dispositivo di controllo (tastiera/braccio leader) usa sempre `--teleop.*`.
3. **Prefisso dei comandi su questa macchina**: su questa macchina di sviluppo tutti i comandi `uv` richiedono l'impostazione preliminare della directory di cache (motivo in [07](07-troubleshooting.md)):

   ```bash
   export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
   ```

## Ambiente verificato

| Voce | Versione |
| --- | --- |
| Sistema | Windows 11 |
| Python / uv | 3.12.9 / 0.12.5 |
| lerobot | 0.6.2 (questo repository, `.venv` isolato nel progetto, non influisce su conda) |
| MuJoCo | 3.16.0 |
| PyTorch | 2.11.0 (versione CPU) |
| Hardware | SO-ARM101 braccio leader (COM163) + follower (COM172), chip seriale CH343 |
