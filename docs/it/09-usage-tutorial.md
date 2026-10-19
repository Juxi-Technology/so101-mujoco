# 09 · Tutorial d'uso completo (braccio → dataset → video → addestramento → deployment)

> Manuale operativo tutto-in-uno: segui il percorso una volta e passi da "collegare il braccio leader" a "la policy addestrata lavora da sola in simulazione".
> Prerequisiti: ambiente installato secondo [01](01-environment.md), braccio leader calibrato secondo [03](03-hardware-calibration.md)
> (su questa macchina `juxi_leader` / COM124). Tutti gli ostacoli legati alla registrazione sono raccolti in [07](07-troubleshooting.md).

## 0 · Preparazione una tantum

```bash
# tutti i comandi uv di questa macchina richiedono questa impostazione preliminare (caso speciale della cache su altro disco, vedi 07)
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
```

Collega il braccio leader e verifica la porta seriale (**il numero può cambiare a ogni collegamento**):

```bash
uv run --frozen python -c "from serial.tools import list_ports; print([p.device for p in list_ports.comports()])"
```

Lascia spazio sulla scrivania: la registrazione apre **3 finestre** (vista principale + `wrist camera - live` + `top camera - live`).

## 1 · Riscaldamento con teleoperazione (consigliato)

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/teleoperate.py \
    --robot.type=so101_mujoco \
    --teleop.type=so101_leader_trim --teleop.port=COM124 --teleop.id=juxi_leader \
    --teleop.use_degrees=false
```

Muovi il braccio leader e verifica che il braccio simulato segua; prima di uscire (Ctrl-C) porta il braccio leader **vicino alla posa centrale**, così all'avvio della registrazione non ci sarà un lungo segmento di convergenza.

## 2 · Registrazione (comando principale)

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/record.py \
    --robot.image_camera=sim_cam --robot.top_camera=top_cam \
    --teleop.type=so101_leader_trim --teleop.port=COM124 --teleop.id=juxi_leader \
    --teleop.use_degrees=false \
    --dataset.repo_id=local/so101_sim_vision \
    --dataset.root=examples/so101_mujoco/outputs/datasets/so101_sim_vision \
    --dataset.num_episodes=5 --dataset.episode_time_s=600 --dataset.reset_time_s=10 \
    --dataset.single_task="put the cube in the box" \
    --dataset.video=true --dataset.push_to_hub=false --play_sounds=false --dataset.no_stamp=true
```

Punti chiave (per gli altri parametri vedi la tabella in [06](06-record-and-replay.md)):

| Voce | Descrizione |
| --- | --- |
| `--dataset.root` | **root è la directory del dataset stessa**; cambia directory a ogni sessione (se esiste già una directory con lo stesso nome l'avvio viene rifiutato) |
| Valori predefiniti iniettati automaticamente | Codec video `h264`, thread di codifica `2`: `record.py` stampa due righe di avviso all'avvio; passando esplicitamente `--dataset.rgb_encoder.vcodec=...` / `--dataset.encoder_threads=...` si sovrascrive (motivo in 07) |
| Finestre di anteprima | Attive per default (15Hz, disattivabili con `--robot.preview_cameras=false`; regolabili con `--robot.preview_fps`) |
| `--dataset.video=true` | Le immagini delle due telecamere entrano nel dataset (`observation.images.wrist / top`); se vuoi solo la telecamera del polso, ometti `top_camera` |

## 3 · Operazioni durante la registrazione

| Tasto | Funzione |
| --- | --- |
| `→` o `n` | Termina l'episodio corrente e lo salva |
| `←` o `r` | Scarta l'episodio corrente e registra di nuovo sul posto |
| `q` | Termina l'intera sessione e salva il dataset |

- Al termine dell'episodio **i cubi tornano automaticamente al loro posto**: devi solo riportare il braccio leader nella posa iniziale; inizia i movimenti dell'episodio successivo quando vedi `Recording episode N`.
- Durante la fase di salvataggio (decine di secondi) la console stampa `[record.py] reset done; saving the episode + encoding videos now`:
  in questo periodo **i tasti vengono ignorati in sicurezza** (una pressione accidentale non danneggia alcun episodio); ricomincia a operare quando compare la riga successiva `Recording episode`.
- In caso di errore di codifica c'è un **retry automatico di sicurezza** (stampa `video encode failed ... retrying once` e riprova automaticamente dopo 3 secondi); gli episodi già salvati non vanno mai persi.

## 4 · Ispezione

```bash
uv run --frozen python examples/so101_mujoco/inspect_dataset.py \
    --repo-id local/so101_sim_vision \
    --root examples/so101_mujoco/outputs/datasets/so101_sim_vision
```

Come leggere l'output:

- **Gli episodi con action span tutto 0 (o gripper 0)** sono registrazioni vuote/non valide: eliminale e registra di nuovo;
- **Un `max |act-obs|` grande all'inizio di ogni episodio** è il segmento di convergenza, normale; nella parte centrale e finale dovrebbe essere inferiore a ~10 unità.

## 5 · Guardare i video

```bash
uv run --frozen python examples/so101_mujoco/export_videos.py \
    --root examples/so101_mujoco/outputs/datasets/so101_sim_vision
```

Prodotti:

- `examples/so101_mujoco/outputs/videos/<数据集名>/epN_top.mp4`, `epN_wrist.mp4` — **un video riproducibile con doppio clic per ogni episodio e ogni telecamera**;
- `examples/so101_mujoco/outputs/renders/<数据集名>_epN_dual.png` — un collage per episodio (riga superiore vista dall'alto, riga inferiore polso, 6 frame campionati uniformemente), per un controllo visivo rapido (`--no-strips` per saltarlo).

Nel dataset sono presenti anche i video originali impacchettati (più episodi concatenati in ordine nello stesso file):
`outputs/datasets/<数据集名>/videos/observation.images.{top,wrist}/chunk-000/file-000.mp4`.

## 6 · Riproduzione (opzionale)

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/replay.py \
    --dataset.repo_id=local/so101_sim_vision \
    --dataset.root=examples/so101_mujoco/outputs/datasets/so101_sim_vision --dataset.episode=0
```

## 7 · Addestramento

```bash
uv run --frozen lerobot-train \
    --policy.type=act \
    --policy.push_to_hub=false \
    --dataset.repo_id=local/so101_sim_vision \
    --dataset.root=examples/so101_mujoco/outputs/datasets/so101_sim_vision \
    --output_dir=examples/so101_mujoco/outputs/train/act_so101_sim_vision \
    --steps=100000 --batch_size=8 --save_freq=20000 --log_freq=200 \
    --num_workers=4 --wandb.enable=false --policy.device=cpu
```

| Punto chiave | Descrizione |
| --- | --- |
| `--policy.type` | Tipo di policy, **parti da `act`** (il più adatto a questa scala di dati/attività); `ls src/lerobot/policies/` mostra le altre opzioni (diffusion / smolvla / pi0 ecc.) |
| `--policy.push_to_hub=false` | **Obbligatorio**: il default tenta di caricare su HuggingFace Hub e, senza `repo_id`, esce subito con errore; per caricare usa `--policy.repo_id=你的用户名/模型名` (prima esegui `hf auth login`) |
| `--policy.device=cpu` | Questa macchina non ha GPU dedicata, usa `cpu`; su macchine con scheda NVIDIA ometti il parametro (usa automaticamente cuda) |
| Prodotti | `output_dir/checkpoints/<步数>/` e `checkpoints/last/pretrained_model/`: il deployment punta a quest'ultimo; dentro c'è anche `train_config.json` per riprendere l'addestramento |
| Ripresa | Dopo un'interruzione aggiungi al comando originale: `--resume=true --config_path=<output_dir>/checkpoints/last/pretrained_model/train_config.json` |

**Velocità prevista su questa macchina**: solo CPU circa **2 secondi/step** (batch 2, doppia telecamera 480p; smoke di 12 step misurato con loss da 70 a 22, direzione corretta).
Quindi questa macchina è adatta a validare la catena con pochi step: il `outputs/train/smoke_act` incluso nel tutorial è proprio il prodotto di 12 step;
**per l'addestramento ufficiale (ACT tipicamente nell'ordine di 100.000 step) si consiglia una macchina con GPU, i comandi sono identici.**

> Nota sulle dipendenze: l'addestramento richiede l'extra `training` (accelerate ecc.). Se compare `accelerate is required but not installed`,
> aggiungi `--extra training` con il comando di installazione di [01](01-environment.md) e riprova.

## 8 · Deployment (far lavorare la policy da sola in simulazione)

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/rollout.py \
    --policy.path=examples/so101_mujoco/outputs/train/act_so101_sim_vision/checkpoints/last/pretrained_model \
    --strategy.type=base \
    --robot.image_camera=sim_cam --robot.top_camera=top_cam \
    --task="put the cube in the box" --duration=30
```

| Punto chiave | Descrizione |
| --- | --- |
| Parametri delle telecamere | `--robot.image_camera/--robot.top_camera` **devono essere identici a quelli usati durante la registrazione del dataset** (sim_cam + top_cam), altrimenti la policy non riceve le immagini con cui è stata addestrata |
| `--task` | Coerente con `--dataset.single_task` usato durante la registrazione |
| `--duration` | Dopo quanti secondi terminare automaticamente (prima della chiusura il braccio viene riportato alla posa iniziale e poi disconnesso); anche `Ctrl-C` interrompe |
| Per provare prima la catena | Basta il modello dimostrativo incluso nel tutorial: `--policy.path=examples/so101_mujoco/outputs/train/smoke_act/checkpoints/last/pretrained_model` (12 step di addestramento, azioni quasi casuali, serve solo a validare la catena) |
| Deployment su sola CPU | L'inferenza della policy ha picchi occasionali di 0.5s e viene segnalato `Control loop is running slower ... than the target FPS`: in simulazione funziona ma a scatti; su GPU il problema non esiste (smoke misurato: 20s di esecuzione continua, chiusura regolare) |
| Deployment sul robot reale | Sostituisci `--robot.*` con il robot reale: `--robot.type=so101_follower --robot.port=COMxx --robot.id=juxi_so101 --robot.use_degrees=false` (lascia spazio sulla scrivania) |
| Altre modalità | `--strategy.type=sentry / highlight / dagger / episodic`: registrazione durante l'esecuzione / salvataggio con tasto su buffer circolare / correzione umana nel loop / registrazione a episodi, vedi `lerobot-rollout --help` |

## Appendice A · Passare a un ambiente conda (opzionale)

Questo repository usa per default un **`.venv` isolato nel progetto gestito da uv** (vedi [01](01-environment.md)); i comandi di esecuzione richiedono il prefisso
`uv run --frozen --with mujoco`. Se preferisci conda, il metodo è **sostituire il passo "creare l'ambiente" con i tre comandi seguenti**,
dopodiché **tutti i comandi perdono il prefisso uv** (`python examples/...` eseguito direttamente) e `UV_CACHE_DIR` non serve più
(è un caso speciale della cache uv su altro disco, non ha nulla a che vedere con conda):

```bash
# una tantum: crea l'ambiente nella radice del repository (versione python allineata alla 3.12 di 01)
conda create -n lerobot-sim python=3.12 -y
conda activate lerobot-sim
pip install -e .            # installa lerobot di questo repository e le sue dipendenze (incluso torch; su Windows pip installa di default la versione CPU)
pip install "mujoco==3.16"  # con uv si usa --with mujoco in modo temporaneo; con conda si installa come dipendenza permanente
```

Dopo, ad esempio, la registrazione diventa:

```bash
python examples/so101_mujoco/record.py --robot.image_camera=sim_cam ...
```

Due avvertenze:

1. **Allineamento delle versioni**: `pip install -e .` lascia che pip risolva le versioni da sé e potrebbe non coincidere esattamente con `uv.lock`;
   per una combinazione identica all'ambiente misurato, installa con uv nell'ambiente conda secondo il file di lock:

   ```bash
   uv pip sync uv.lock --python "$(conda run -n lerobot-sim python -c 'import sys; print(sys.executable)')"
   pip install "mujoco==3.16"
   ```

2. La cache di calibrazione del braccio leader si trova in `~/.cache/huggingface/lerobot/calibration/`, indipendentemente dall'ambiente usato: cambiando ambiente non serve ricalibrare.

## Appendice B · Ostacoli comuni: consultazione rapida

| Sintomo | In una frase |
| --- | --- |
| La porta seriale non si apre | Elenca prima le porte, il numero potrebbe essere cambiato (passo 0) |
| La console resta silenziosa per decine di secondi durante il salvataggio | È in corso la codifica, è normale; quando vedi `saving the episode...` non premere tasti |
| L'immagine va a scatti durante la registrazione | Contesa delle risorse di codifica nella finestra di salvataggio; il loop di controllo non è influenzato (fai riferimento ai numeri di cadence), dettagli in 07 |
| Dopo un crash è ancora recuperabile? | Gli episodi salvati non si perdono mai; riprendi con `record.py --resume=true ... --dataset.num_episodes=N` |
| `lerobot-train` segnala `'repo_id' argument missing` | Il default vuole caricare su Hub: aggiungi `--policy.push_to_hub=false` (per caricare configura `--policy.repo_id` ed esegui prima `hf auth login`) |
| In deployment la policy non si muove o si muove a caso | Verifica prima che `--robot.image_camera/--robot.top_camera` e `--task` coincidano con quelli della registrazione; poi controlla se è stata addestrata per pochi step |

Tutti gli ostacoli e le soluzioni (inclusi memoria scarsa, OOM di codifica, episodi vuoti ecc.) in [07 · Problemi comuni](07-troubleshooting.md).
