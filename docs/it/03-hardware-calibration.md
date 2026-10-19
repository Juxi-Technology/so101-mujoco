# 03 · Connessione al robot reale e calibrazione

## Identificazione della porta seriale

Quando si collega la scheda driver con chip CH343 compare subito una porta COM; **il numero cambia a ogni inserimento/rimozione o cambio di porta USB**, quindi verificalo prima di ogni connessione:

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
uv run --frozen python -c "import serial.tools.list_ports as lp; [print(p.device, '|', p.description, '|', p.hwid) for p in lp.comports()]"
```

## Primo passo: controllo iniziale in sola lettura (cablaggio/alimentazione/servo)

**Senza scrivere nulla**, esegui prima un ping su ciascuno dei sei servo e poi leggi tensione e temperatura (lo stato di coppia resta invariato):

```bash
uv run --frozen python examples/so101_mujoco/hardware_check.py --port COM163
```

L'output normale è simile a: sei righe di giunti, temperatura 20~30°C, coppia 0 (braccio libero). **La tensione dipende dal tipo di alimentazione**: con il follower collegato a un
alimentatore esterno è circa 11V, con il leader alimentato solo dalla scheda driver è circa 5V; se riesci a leggere tutti e sei i servo, il cablaggio è corretto. Servo mancanti o modelli
non corrispondenti producono un errore immediato.

## Secondo passo: calibrazione

La calibrazione scrive nell'EEPROM dei servo "l'intervallo di corsa di ogni giunto + il riferimento di posizione centrale" e lo salva in un file locale; **sia il follower sia il leader vanno calibrati una volta ciascuno**.
I file di calibrazione dei due bracci sono memorizzati separatamente e non si influenzano a vicenda:

| Dispositivo | Comando | Posizione del file di calibrazione |
| --- | --- | --- |
| Follower | `uv run --frozen lerobot-calibrate --robot.type=so101_follower --robot.port=COM172 --robot.id=juxi_so101` | `~/.cache/huggingface/lerobot/calibration/robots/so_follower/juxi_so101.json` |
| Leader | `uv run --frozen lerobot-calibrate --teleop.type=so101_leader --teleop.port=COM163 --teleop.id=juxi_leader` | `.../calibration/teleoperators/so_leader/juxi_leader.json` |

`id` può essere qualsiasi nome, ma **teleoperazione e registrazione successive devono usare lo stesso id**, altrimenti verrà richiesta di nuovo la calibrazione.

### Passi fisici (il terminale stampa uno schema)

1. **Porta il braccio nella posizione centrale e premi Invio**: appoggia la base sul bordo del tavolo, braccio superiore verticale verso l'alto, avambraccio orizzontale in avanti,
   rotazione della spalla e polso centrati (il "gripper" del leader è l'impugnatura/grilletto). La posizione assunta in questo istante viene registrata come "riferimento centrale" del braccio.
2. Dopo aver premuto Invio, **percorri lentamente l'intero campo di movimento di ogni giunto** (`wrist_roll` non va percorso: viene gestito automaticamente come giro completo), poi premi Invio per salvare.

Avvertenze:

- Durante la calibrazione del follower la coppia è 0 (il braccio è flaccido): sostienilo con la mano; il leader è già privo di coppia.
- La procedura di calibrazione scrive nell'EEPROM dei servo (fa parte della calibrazione, è normale).
- Risultati di calibrazione misurati in questa sessione (per confronto): corsa dei giunti del follower 1474~2688 conteggi, `wrist_roll` 4095;
  leader 2208~2681 conteggi. Una corsa marcatamente asimmetrica è normale (vedi [05 Micro-regolazione dello zero](05-leader-digital-twin.md) per il motivo).
