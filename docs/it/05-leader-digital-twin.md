# 05 · Digital twin del braccio leader (braccio fisico che guida il braccio simulato)

Trascina con la mano il **braccio leader fisico** e fai sì che il **follower simulato nella finestra MuJoCo** lo segua in tempo reale rispecchiandone i movimenti: è il modo corretto per una demo di
digital twin e per l'acquisizione di dati in simulazione.

## Prerequisiti

Braccio leader calibrato (vedi [03](03-hardware-calibration.md)); la porta seriale è `COM163` a titolo di esempio.

## Comando

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
uv run --frozen --with mujoco python examples/so101_mujoco/teleoperate.py \
    --robot.type=so101_mujoco \
    --teleop.type=so101_leader_trim --teleop.port=COM163 --teleop.id=juxi_leader \
    --teleop.use_degrees=false
```

- `--robot.type=so101_mujoco`: l'oggetto controllato è il braccio simulato, la finestra si apre automaticamente;
- `--teleop.*`: il dispositivo di controllo è il braccio leader fisico (sola lettura, nessuna coppia applicata, rischio zero per il leader);
- `--teleop.use_degrees=false`: **obbligatorio**. Allinea le unità emesse dal leader (proporzione della corsa) a quelle del braccio simulato.

Sostituendo `--robot.type` con `so101_follower --robot.port=COM172 --robot.id=juxi_so101 --robot.max_relative_target=5`
si ottiene il classico utilizzo del kit "braccio leader fisico → follower reale"; la stessa calibrazione del leader vale per entrambi i casi.

## Cosa fare se lo zero è sfalsato: micro-regolazione automatica del centro (`so101_leader_trim`)

**Sintomo**: il braccio leader viene portato nella "posizione centrale a occhio", ma il braccio simulato è sfalsato di alcuni gradi.

**Principio**: lo zero normalizzato di lerobot è il **punto medio dell'intervallo registrato durante la spazzata di calibrazione**, `(min+max)/2`; la "posa centrale" al momento di premere Invio
durante la calibrazione viene invece registrata come valore grezzo 2048. Se la corsa meccanica di un giunto è asimmetrica, i due "punti medi" differiscono sempre di una quantità fissa
(misura sul servo n. 1: intervallo registrato 776~3457, punto medio 2116, differenza di 68 conteggi rispetto a 2048 ≈ **5.6°**).
**Questa differenza non si elimina ricalibrando** (l'asimmetria della corsa è determinata dalla struttura meccanica) e va compensata nel software.

**Soluzione**: il plugin `so101_leader_trim` calcola automaticamente dal file di calibrazione la compensazione di ogni giunto secondo la formula e la sottrae in tempo reale;
dopo una nuova calibrazione si adatta da solo, senza parametri manuali:

```
补偿ᵢ = (2048 − minᵢ) / (maxᵢ − minᵢ) × 200 − 100
```

Valori effettivi misurati su questa macchina (vengono stampati nel log di avvio):

| Giunto | Compensazione (unità) |
| --- | --- |
| shoulder_pan | −5.11 |
| shoulder_lift | −0.92 |
| elbow_flex | +2.54 |
| wrist_flex | +0.69 |

Gli altri giunti hanno uno scostamento <0.05 e non richiedono compensazione; il gripper (0~100) e la modalità in gradi non partecipano alla regolazione fine.

> Nota per gli sviluppatori: il `name` di questo plugin deve restare `"so_leader"`: `name` è la chiave della directory usata per cercare il file di calibrazione;
> un nome di tipo personalizzato impedisce di trovare il file e attiva per errore la procedura di ricalibrazione.
