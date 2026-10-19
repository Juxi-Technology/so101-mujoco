# 07 · Problemi comuni ed esperienze

Ostacoli realmente incontrati in questo flusso di lavoro, con consultazione rapida per sintomo.

## Ambiente

| Sintomo | Causa e soluzione |
| --- | --- |
| `uv sync` segnala `failed to persist temporary file ... os error 17（跨盘）` | Caso particolare di Windows su questa macchina con la directory di cache uv su un altro disco. Aggiungi `export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'` prima di ogni comando uv |
| La console si riempie con decine di righe di errori di caricamento `libtorchcodec_core*.dll` | Avvisi innocui: dopo il fallimento del caricamento di torchcodec si passa automaticamente a **pyav**. Verificato (smoke [5]): pyav **codifica e decodifica correttamente i dataset video**; né i dataset di stato né quelli video ne sono influenzati |
| `python` apre il Microsoft Store | Usa il Python gestito da uv; non usare la versione dello Store |

## Teleoperazione

| Sintomo | Causa e soluzione |
| --- | --- |
| Il controllo da tastiera è "molto lento" | Il default di `--teleop.rate` è 60 unità/secondo, troppo conservativo; portandolo a **150** il feeling è normale (corsa completa in circa 1.3s) |
| Il log di avvio si riempie di WARNING `clamped to be safe` | Output normale del limitatore di velocità durante l'inseguimento; si ferma appena raggiunta la posizione |
| Con il braccio principale centrato il braccio simulato è sfalsato di alcuni gradi | Offset fisso dovuto all'asimmetria dell'intervallo di calibrazione: usa la micro-regolazione automatica `so101_leader_trim` ([05](05-leader-digital-twin.md)) |
| Il braccio si muove improvvisamente al momento della connessione | Comportamento previsto: sul robot reale attiva la coppia e si sposta verso il punto centrale/la posa del leader; lascia spazio intorno al braccio |
| Dopo l'uscita con Ctrl-C il braccio si affloscia | Normale: la coppia viene disattivata alla disconnessione, sostienilo con una mano |
| Digitare durante teleoperazione/registrazione aziona il braccio | L'ascolto della tastiera è **globale e non blocca i tasti**: i tasti mappati premuti in qualsiasi finestra (incluse le lettere digitate in una chat) entrano nella coda dei tasti. Non digitare durante teleoperazione/registrazione in modalità tastiera; con la modalità leader il problema non esiste |

## Registrazione

| Sintomo | Causa e soluzione |
| --- | --- |
| Dopo l'uscita con `q`, le lettere premute durante la sessione "vengono riversate tutte insieme sulla riga di comando" | Eco accumulato del buffer di input della console Windows; il launcher include già `drain_pending_keys()` per la pulizia (il fenomeno si presenta solo nelle vecchie sessioni) |
| In un episodio l'action span è tutto 0 | Registrazione vuota (nessuno ha mosso il braccio): muovi il braccio prima di registrare, oppure elimina l'episodio in seguito |
| A inizio episodio l'errore per 1 secondo è grande | Segmento di convergenza: al momento dell'avvio il follower è ancora nella posa iniziale mentre il leader è già altrove; porta il leader vicino al centro prima di iniziare per evitarlo |
| Dopo aver impostato `--dataset.root` sulla directory padre il dataset "sparisce" | **root è la directory del dataset stessa**; usa un nuovo root per ogni sessione di registrazione |
| Differenza tra `Esc` e `q` | `q` ferma solo la registrazione; `Esc` disconnette anche la teleoperazione da tastiera. Entrambi chiudono in modo pulito (corretto), ma abituati a usare `q` |
| Al salvataggio `ValueError: You must add one or several frames...` e il processo esce con l'errore | Sono state premute più volte `→`/`n` **tra un episodio e l'altro** (il caso più comune: il salvataggio + la doppia codifica video si fermano per decine di secondi e la console sembra bloccata, quindi si preme più volte), il flag resta in coda e viene consumato all'inizio dell'episodio successivo → **episodio vuoto con 0 frame**, l'upstream va in crash quando salva un episodio vuoto (limite noto di lerobot). **Gli episodi già salvati non sono interessati e i dati sono integri**; riapri la sessione e riprendi la registrazione. **Protezione aggiunta** (2026-10-16): `record.py` all'inizio di ogni episodio elimina i flag `→`/`←` rimasti dalla pausa (durante la registrazione i tasti funzionano normalmente) e prima del salvataggio stampa l'avviso `saving the episode + encoding videos now...`; test di regressione `smoke_test.py` [7] |
| All'avvio `KeyError: 'wrist'` (dataset con immagini) | Il primo frame della telecamera non era ancora stato renderizzato quando il ciclo di registrazione ha letto l'osservazione; **corretto** (2026-10-16): il plugin del robot `connect()` ora attende che il primo frame sia pronto prima di restituire |
| Gli script con video segnalano `BrokenProcessPool` / `Invalid argument: '<stdin>'` | La codifica video usa un **pool di processi multipli**; i processi figli devono reimportare il modulo di ingresso tramite il percorso del file: eseguendo lo script di registrazione con `python - <<EOF` (stdin) si ottiene un crash. Salva lo script in un vero file `.py` ed eseguilo (il vero punto di ingresso `record.py` non è interessato) |
| Al salvataggio dell'episodio l'encoder segnala `SvtMalloc[fatal]: allocate memory failed ... av.error.MemoryError: [Errno 12] ... 'avcodec_open2(libsvtav1)'` e l'intera sessione termina | L'encoder predefinito upstream **libsvtav1**, aprendo in parallelo le due codifiche delle telecamere (wrist+top), fallisce l'allocazione di un blocco di memoria di grandi dimensioni (più probabile con simulazione + finestre di anteprima; riscontrato il 2026-10-16). **Corretto**: `record.py` inietta per default `--dataset.rgb_encoder.vcodec=h264` (la codifica concorrente h264 su due flussi è stata verificata; passando vcodec esplicitamente si può sovrascrivere). Gli episodi già salvati sono intatti; il crash può lasciare `tmp*/` e parquet orfani nella directory del dataset (pulisci come fatto per run2) |
| Durante la registrazione l'immagine va a scatti (soprattutto dopo aver premuto `→`), ma l'operazione non ha ritardo | Ciò che scatta è la **finestra di salvataggio/codifica**: il processo di codifica usa per default tutti i core CPU (doppio flusso video) e contemporaneamente il thread della simulazione continua a renderizzare 5 viste (più evidente con GPU integrata). Il loop di controllo non è influenzato: fai riferimento ai numeri di cadence (misurati 29.97Hz per tutta la durata, 0 tick oltre il budget). **Mitigato** (2026-10-16): `record.py` usa per default `--dataset.encoder_threads=2` (2 thread per flusso); le finestre di anteprima delle telecamere sono passate a 15Hz (`--robot.preview_fps`). Più corto è l'episodio, maggiore è l'incidenza della finestra di salvataggio e più si percepisce lo scatto; per eliminare del tutto la pausa si può usare `--dataset.streaming_encoding=true` (codifica durante la registrazione, consigliato dall'upstream, da verificare) |
| Al salvataggio dell'episodio l'encoder segnala **errore di allocazione di memoria** e l'intera sessione termina (`SvtMalloc` di svtav1, `malloc ... failed` di x264, errori `avcodec_open2` rientrano tutti in questa categoria) | La memoria commit di sistema di questa macchina è costantemente vicina al limite (misurati il 2026-10-16 **105.9GB / 119.7GB**, con 29 giorni di uptime). Ogni salvataggio avvia 2 nuovi processi di codifica (ciascuno carica torch/av, con picchi di commit elevati) e avviarli in parallelo sul filo del rasoio causa il crash. **Mitigato**: `record.py` ora aggiunge **un retry automatico in caso di errore** alla codifica (un errore transitorio non fa più perdere l'episodio) e il log durante il salvataggio è stato silenziato (`av.logging.set_libav_level` + barra di avanzamento HF). **Soluzione definitiva = riavviare la macchina** (pulisce il commit accumulato / le perdite del kernel; i processi utente occupano solo 27GB, il resto è a livello di kernel/driver e non si può terminare); autodiagnosi: `Get-Counter '\Memory\Committed Bytes'` vs `'\Memory\Commit Limit'` |

## Hardware

| Sintomo | Causa e soluzione |
| --- | --- |
| Il numero della porta COM è diverso dall'ultima volta | Il numero della porta seriale cambia con inserimenti/rimozioni o cambio di porta; elenca sempre le porte per verificare ([03](03-hardware-calibration.md)) |
| Il controllo in sola lettura segnala servo mancanti | Problema di cablaggio/alimentazione; controlla prima la scheda driver e l'ordine dei fili, non affrettarti a calibrare |
| `shoulder_lift` si muove nella direzione opposta all'intuizione (simulazione) | La direzione positiva di questo modello punta verso il basso; verifica il segno prima della mappatura ([02](02-sim-model-verification.md)) |

## Nota di progettazione (perché è stato fatto così)

- **MuJoCo riscrive i dati dei vertici della mesh**: dopo il caricamento di `<mesh>`, `mjModel.mesh_vert` memorizza i vertici **nel sistema di coordinate della mesh stessa**
  (l'origine viene ricentrata sul baricentro dei vertici e gli assi riordinati), non più nelle coordinate originali del file; usarlo direttamente per calcolare bounding box o applicare quote CAD
  produce risultati errati (la visualizzazione del rendering non è influenzata). Per ottenere la geometria CAD reale, analizza il file originale (come in `preview_mount.py` /
  `step_to_stl.py`). Ci è capitato una volta: dimensioni reali del supporto 54.3 × 35.0 × 75.0 mm.
- **La direzione di inquadratura della telecamera MuJoCo è la −Z del suo sistema di coordinate**: l'elemento `<camera>` non guarda verso il proprio +Z (la direzione in cui sporge l'obiettivo). La prima
  versione del modulo telecamera costruiva l'obiettivo su +Z con l'elemento orientato identity → l'immagine veniva in realtà ripresa "al contrario" dal retro del PCB, con **la direzione dell'obiettivo e quella dell'immagine
  esattamente opposte** (l'origine del "la direzione di rotazione non corrisponde all'immagine" durante la regolazione dei parametri; individuato il 2026-10-16 con un test di rendering comparativo su pannelli rosso/blu).
  Correzione: elemento telecamera ruotato di 180° attorno a Y (`view.quat = RPY(0,180,0)`, uniformato nei tre punti preview_mount / adjust_camera / plugin del robot);
  `adjust_camera.py` aggiunge una finestra live "sim_cam live view", per regolare l'obiettivo con feedback immediato.
- **Il gripper del MJCF del tutorial ufficiale è una pinza a contatto puntuale "a becco d'uccello"**: le due punte dei denti si chiudono fino a un contatto puntuale di ~2.3 mm, senza quasi superficie di presa utilizzabile.
  Esperimenti fisici sistematici (2026-10-16, centinaia di configurazioni): un cubo posizionato in qualsiasi punto vicino all'apertura dei denti viene spinto via o scalzato durante la chiusura di ~100°, rendendo impossibile afferrarlo
  (vale per cubi da 16 a 34 mm; corsa meccanica e coppia sono normali). **Attenzione: non ripararlo aggiungendo piastre di collisione**:
  è stato provato ad aggiungere piastre ai due denti (migliora sensibilmente la presa), ma è **geometria inesistente sul robot reale**; le policy addestrate vi farebbero affidamento, causando distorsione sim2real,
  quindi è stato rimosso. La correzione giusta è **sostituire i denti del modello ufficiale con la geometria delle dita del robot reale** (ad es.
  SO-ARM101 di mujoco_menagerie o una ricostruzione CAD propria), mantenendo i parametri fisici coerenti con il robot reale.
- **I parametri di contatto predefiniti ufficiali sono troppo "morbidi" e causano compenetrazione fisica**: la costante di tempo `solref` è 20 ms per default; i contatti rapidi/sottili
  (cubo che cade su una superficie sottile delle dita, chiusura con spazzata) "si attraversano" prima che la forza abbia il tempo di generarsi: il sintomo è "il cubo attraversa il piano delle dita e cade".
  Correzione (2026-10-16): irrigidimento dei parametri di contatto; `harden_mesh_contacts` dopo la compilazione porta il `solref` di tutti i corpi di collisione mesh
  allo stesso valore delle superfici dei denti di menagerie (0.01 s), con lo stesso trattamento per il contatto del cubo. Correzione pura di fedeltà fisica, senza aggiungere alcuna geometria.
- **Il robot simulato è migrato al modello SO-ARM100 di mujoco_menagerie** (2026-10-16): il MJCF dello zip del tutorial originale è un pezzo dimostrativo di cinematica e il gripper non riesce ad afferrare;
  il modello menagerie è realizzato secondo il CAD del robot reale: la pinza dispone di superfici di collisione dedicate sui denti e di parametri di contatto rigidi;
  tutte e quattro le posizioni dei denti (da superficiali a profonde) sono state verificate: fermano, afferrano e sollevano un cubo da 34mm. Punti chiave della migrazione: modello vendored in
  `assets/menagerie_so_arm100/` (Apache-2.0, con LICENSE); mappatura dei giunti e segni delle unità in `MODEL_JOINT`
  (confronto per giunto con il moto nel sistema di riferimento mondiale misurato sul vecchio modello; segno di wrist_roll da verificare con teleoperazione sul robot reale); Base del modello ruotata di +90° attorno a Z per far sì che il
  frontale di lavoro guardi verso +x; supporto spostato sul lato di Fixed_Jaw (servo n. 6) (prima localizzato tramite ricerca analitica, poi finalizzato il 2026-10-16 dall'utente confrontando
  le foto del robot reale con `adjust_mount.py --model menagerie`: `[0.1, -0.7, 24.7]mm`, `RPY [0.34, -27.20, 89.51]°`). Il vecchio modello del tutorial e gli strumenti restano invariati, disponibili per il confronto.
- **Perché usare l'ambiente di progetto uv invece di conda**: `.venv` è nella stessa directory del progetto, le versioni sono bloccate da `uv.lock`, basta eliminare la directory per recuperare lo spazio
  ed è completamente isolato dagli ambienti conda della macchina; `uv run` non installa mai nulla nel conda attivato. L'ambiente conda `lerobot` di questa macchina
  punta a **un'altra copia del repository** (`lerobot-main`); i due non si interferiscono.
- **Perché i plugin sono tutti in `examples/so101_mujoco/`**: si integrano tramite il meccanismo di registrazione ufficiale (`register_subclass`),
  **zero modifiche al codice sorgente di lerobot**; per aggiornare l'upstream basta rieseguire sync.
