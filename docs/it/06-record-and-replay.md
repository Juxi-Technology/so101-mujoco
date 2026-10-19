# 06 · Registrazione e riproduzione dei dati

## Modello di comando per la registrazione

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'

# registra il robot reale (leader → follower reale)
uv run --frozen --with mujoco python examples/so101_mujoco/record.py \
    --robot.type=so101_follower --robot.port=COM172 --robot.id=juxi_so101 \
    --robot.use_degrees=false --robot.max_relative_target=10 \
    --teleop.type=so101_leader_trim --teleop.port=COM163 --teleop.id=juxi_leader \
    --teleop.use_degrees=false \
    --dataset.repo_id=local/juxi_so101_teleop \
    --dataset.root=examples/so101_mujoco/outputs/datasets/real_run1 \
    --dataset.num_episodes=5 --dataset.episode_time_s=600 --dataset.reset_time_s=10 \
    --dataset.single_task="pick up the cube" \
    --dataset.video=false --dataset.push_to_hub=false --play_sounds=false --dataset.no_stamp=true

# registra in simulazione (leader → follower simulato)
#   sostituisci --robot.* con: --robot.type=so101_mujoco
# registra in simulazione (controllo da tastiera)
#   sostituisci --teleop.* con: --teleop.type=so101_keyboard --teleop.rate=150
```

## Punti chiave dei parametri (quelli facili da sbagliare)

| Parametro | Descrizione |
| --- | --- |
| `--dataset.root` | **root è la directory del dataset stessa** (non la directory padre + concatenazione con repo_id); usa una nuova directory a ogni registrazione |
| `--dataset.repo_id` | Nella registrazione locale è solo un identificatore; il vero `用户名/名字` serve solo quando in futuro pubblicherai su Hub |
| `--dataset.no_stamp=true` | Nessun suffisso timestamp, directory/nome stabili; per registrare di nuovo con lo stesso nome elimina prima la vecchia directory |
| `--dataset.episode_time_s` | **Limite massimo** per episodio (di sicurezza); in condizioni normali premi `→` per terminare prima |
| `--dataset.reset_time_s` | Tempo di riposizionamento non registrato tra un episodio e l'altro; durante questa fase il leader continua a comandare il follower in tempo reale. **Durante la registrazione in simulazione il cubo viene teletrasportato automaticamente nella posizione iniziale quando inizia questa fase** (vedi sotto) |
| `--dataset.video` | Attivalo solo se servono i dati delle telecamere (i dataset visivi richiedono true; il fallback pyav è stato verificato e funziona) |
| `--dataset.rgb_encoder.vcodec` | Codec video. **Su questa macchina, per la registrazione con due telecamere si usa `h264`**: `record.py` lo inietta già per default (il default upstream libsvtav1, aprendo in parallelo due codifiche, causa un errore di allocazione della memoria e il crash dell'intera sessione: vedi [07](07-troubleshooting.md)); se lo passi esplicitamente non viene più iniettato |
| `--dataset.encoder_threads` | Numero di thread di codifica. **`record.py` inietta 2 per default**: il default che sfrutta tutti i core rende visibilmente a scatti la simulazione durante il salvataggio (vedi [07](07-troubleshooting.md)); limitando a 2 thread per flusso la simulazione resta fluida durante il salvataggio; se lo passi esplicitamente non viene più iniettato |
| `--dataset.push_to_hub` | La connessione diretta a HF da questa macchina richiede un proxy: lascia false e carica manualmente dopo la registrazione |

## Tasti di controllo degli episodi (globali, sempre attivi durante la registrazione)

| Tasto | Funzione |
| --- | --- |
| `→` o `n` | Termina l'episodio corrente (**salva**) |
| `←` o `r` | Scarta l'episodio corrente e **registra di nuovo sul posto** (usalo se un singolo episodio non ti soddisfa, senza riavviare la sessione) |
| `q` | Termina l'intera sessione e salva il dataset (**consigliato**) |
| `Esc` | Come `q` (disconnette anche la teleoperazione da tastiera; l'uscita pulita è stata verificata, ma preferisci comunque `q`) |

**Consigli operativi**: prima di iniziare a registrare, porta il braccio leader vicino alla posa centrale (per evitare che il segmento di convergenza in cui il braccio simulato/reale "scatta" all'inizio
venga registrato); dopo l'avvio resta fermo per un secondo prima di iniziare i movimenti.

## Reimpostazione automatica della scena nella registrazione simulata

Nella registrazione sul robot reale, durante la fase "Reset the environment" devi rimettere manualmente il cubo al suo posto. In simulazione il launcher di registrazione (`record.py`)
**teletrasporta automaticamente i tre cubi nella posizione di origine** all'inizio di questa fase (azzerandone anche la velocità), quindi dopo aver terminato ogni episodio con `→`
devi solo riportare il braccio leader nella posa iniziale: i cubi tornano al loro posto da soli e l'episodio successivo parte da una scena iniziale fissa.
Il follower reale non ha questo comportamento (i cubi vanno posizionati a mano come sempre); anche `teleoperate.py`/`replay.py` non sono interessati.

## Ispezione del dataset dopo la registrazione

```bash
uv run --frozen python examples/so101_mujoco/inspect_dataset.py \
    --repo-id local/so101_sim_vision \
    --root examples/so101_mujoco/outputs/datasets/so101_sim_vision
```

Stampa per ogni episodio il numero di frame, la durata, l'ampiezza d'azione dei sei giunti e l'errore di inseguimento:

- **Gli episodi con action span = 0** sono registrazioni vuote (nessuno ha mosso il braccio): eliminali e registra di nuovo;
- **Un |action−obs| grande all'inizio** è il segmento di convergenza (normale); nella parte centrale e finale è di solito <10 unità.

## Registrare dati "con immagine" in simulazione (telecamera wrist)

Il robot simulato supporta la registrazione della telecamera del polso (`sim_cam`) presente nella scena come osservazione di immagine nel dataset:

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/record.py \
    --robot.image_camera=sim_cam --robot.top_camera=top_cam \
    --teleop.type=so101_leader_trim --teleop.port=COM124 --teleop.id=juxi_leader \
    --teleop.use_degrees=false \
    --dataset.repo_id=local/so101_sim_vision \
    --dataset.root=examples/so101_mujoco/outputs/datasets/so101_sim_vision \
    --dataset.num_episodes=5 --dataset.episode_time_s=600 --dataset.reset_time_s=10 \
    --dataset.single_task="pick up the cube" \
    --dataset.video=true --dataset.push_to_hub=false --play_sounds=false --dataset.no_stamp=true
```

Punti chiave: `--robot.image_camera=sim_cam` (nome della telecamera) + `--dataset.video=true` (le immagini passano alla codifica video; il fallback pyav è stato verificato e funziona).
Tra le feature del dataset comparirà `observation.images.wrist` (480×640×3). Risoluzione e frame rate si regolano con
`--robot.image_width/--robot.image_height/--robot.image_fps`.
Con la finestra aperta (`onscreen=true`, default), oltre alla finestra della vista principale viene aperta **una finestra di anteprima in tempo reale per ogni telecamera**
(polso / dall'alto, con etichetta nell'angolo in alto a sinistra), così durante la registrazione puoi vedere subito se entrambi i flussi sono corretti; se non servono, aggiungi
`--robot.preview_cameras=false`. Le anteprime si aggiornano per default a **15Hz** (`--robot.preview_fps` regolabile):
sono una visualizzazione di stato e non devono seguire i 50Hz della finestra principale, così con 3 finestre sullo schermo il carico di rendering è molto minore.

**Scena e telecamera dall'alto (dal 2026-10-16)**: la scena simulata include un'area di lavoro: tappetino, cubi di tre colori (34mm), scatola di raccolta (vedi `so101_assets.add_workspace`;
il layout può essere regolato renderizzandolo con `preview_workspace.py`); è inoltre presente una telecamera fissa dall'alto `top_cam` (la parte superiore dell'immagine = direzione opposta al braccio robotico).
Aggiungendo `--robot.top_camera=top_cam` la vista dall'alto viene registrata in `observation.images.top` (registrazione simultanea con due telecamere); se vuoi solo la telecamera del polso, ometti questo parametro.
La codifica video a fine episodio elabora entrambi i flussi: un'attesa un po' più lunga è normale.

## Riproduzione

```bash
# replay in simulazione (rivedi la traiettoria nella finestra)
uv run --frozen --with mujoco python examples/so101_mujoco/replay.py \
    --dataset.repo_id=local/so101_sim_vision \
    --dataset.root=examples/so101_mujoco/outputs/datasets/so101_sim_vision --dataset.episode=0

# replay sul robot reale (stesso meccanismo; l'ambiente circostante deve essere identico a quello della registrazione)
uv run --frozen --with mujoco python examples/so101_mujoco/replay.py \
    --robot.type=so101_follower --robot.port=COM172 --robot.id=juxi_so101 \
    --robot.use_degrees=false --robot.max_relative_target=10 \
    --dataset.repo_id=local/juxi_so101_teleop \
    --dataset.root=examples/so101_mujoco/outputs/datasets/juxi_teleop_run1 --dataset.episode=0
```

> Il punto di ingresso ufficiale `lerobot-replay` non carica i plugin di questo progetto e, usato direttamente, segnala `invalid choice: 'so101_mujoco'`;
> per questo si usa sempre il launcher `replay.py`.

## Formato e posizione del dataset

Il dataset è in formato LeRobotDataset v3: `action` e `observation.state` sono entrambi vettori a 6 dimensioni
(`shoulder_pan.pos … gripper.pos`), coerenti con i dataset ufficiali del robot reale e utilizzabili direttamente per un addestramento misto.

```
examples/so101_mujoco/outputs/datasets/
└── juxi_teleop_run1/   teleoperazione da tastiera su robot reale (1 episodio / 2430 frame / 81s) ✅ dati reali conservati

> Pulizia del 2026-10-16: le vecchie registrazioni in simulazione (`sim_run2`, `sim_vision_demo`, `sim_vision_run1/2/3`)
> sono state tutte eliminate. **Il dataset ufficiale `so101_sim_vision` (due telecamere / 5 episodi / 10610 frame / 353.8s / h264)
> è stato registrato quella stessa sera ✅**; l'esportazione dei video per singolo episodio è in `outputs/videos/so101_sim_vision/`,
> il collage di anteprima delle due telecamere in `outputs/renders/sim_vision_epN_dual.png`.
```

## Record misurati in questa sessione (2026-10-15)

| Sessione | Contenuto | Risultato |
| --- | --- | --- |
| Robot reale run1 | Teleoperazione da tastiera con registrazione su robot reale | 1 episodio 81s, ampiezza dei sei giunti 75~140 unità, stabile a 30Hz |
| Replay robot reale | Riproduzione dello stesso episodio | 2430 frame riprodotti integralmente, nessuna anomalia |
| Simulazione run2 | Teleoperazione con leader e registrazione in simulazione | 5 episodi 157s, errore di inseguimento ep1~4 <12 unità |
| Replay simulazione ep1 | Riproduzione nella finestra | Traiettoria coerente con l'operazione (confermato) |

## Misurazioni aggiuntive (2026-10-16)

| Sessione | Contenuto | Risultato |
| --- | --- | --- |
| Nuovo leader (COM124) | Nuova calibrazione (nuovo braccio/nuovi servo) | ✅ Calibrazione riuscita; la compensazione dello zero di `so101_leader_trim` si adatta automaticamente alla nuova calibrazione |
| Visione run1 | Teleoperazione con leader e registrazione in simulazione (con immagini) | 2 episodi / 3177 frame / 106s @ 29.97Hz; errore di inseguimento ≤2 unità per tutta la durata (solo 0.5s di convergenza al primo frame); video `observation.images.wrist` salvato nel dataset e verificato tramite decodifica ✅ |
| Visione run2 | Registrazione continua con due telecamere (`--resume`) | ep0 (2776 frame / 92.6s) integro; al salvataggio di ep1 l'encoder libsvtav1 va in OOM e l'intera sessione si blocca → codec cambiato in h264 (iniettato per default da `record.py`) e test end-to-end superato (2 episodi × doppia codifica); residui puliti, registrazione ufficiale spostata a run3 |
| Visione run3 | Registrazione ufficiale con due telecamere (h264) | 1ª sessione: ep0 (185.2s / 5554 frame) + ep1 (72.8s / 2186 frame) salvati correttamente, ispezione superata; durante la pausa di codifica tra le sessioni, pressioni ripetute di `→` hanno causato il crash di un episodio vuoto (meccanismo e protezione in [07](07-troubleshooting.md)) → sessione successiva per gli episodi rimanenti (piano da 5 episodi) |
| Prima prova della registrazione ufficiale (so101_sim_vision) | Doppia telecamera (h264 + 2 thread + anteprime a 15Hz) | Al salvataggio di ep0 (82.3s / 2469 frame) l'encoder va in errore di allocazione di memoria e l'intera sessione si blocca (commit di sistema quasi pieno, vedi [07](07-troubleshooting.md)) → aggiunti **retry automatico in caso di errore di codifica** e **silenziamento della console** (entrambi verificati, 26 voci di smoke test superate); in attesa del riavvio della macchina per la registrazione ufficiale |
| Registrazione ufficiale (so101_sim_vision) ✅ | Teleoperazione con leader e doppia telecamera, 5 episodi | **5/5 episodi salvati**: 61.5 / 53.4 / 101.1 / 62.4 / 75.4 s, 10610 frame totali @29.97Hz, 0 tick oltre il budget, nessun crash; azione valida su tutti e sei gli assi + gripper per tutta la durata; verifica tramite decodifica di entrambi i flussi video superata |
