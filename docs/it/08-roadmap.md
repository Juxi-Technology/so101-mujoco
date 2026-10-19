# 08 · Roadmap futura

## Completato (eseguibile direttamente da questo repository)

| Capacità | Stato |
| --- | --- |
| Verifica di caricamento/azionamento/rendering del modello di simulazione (3 MJCF) | ✅ |
| Teleoperazione da tastiera (simulazione / robot reale) | ✅ verificato sul robot reale |
| Digital twin del braccio leader (braccio fisico → braccio simulato, con micro-regolazione dello zero) | ✅ verificato sul robot reale |
| Registrazione dati (robot reale / simulazione) + controllo episodi + script di ispezione | ✅ verificato sul robot reale |
| Riproduzione dati (robot reale / simulazione, meccanismo ufficiale) | ✅ verificato sul robot reale |
| Test di smoke automatizzati (senza hardware `smoke_test.py`) | ✅ 26 voci superate |
| Dataset visivo con due telecamere `so101_sim_vision` (5 episodi / 10610 frame / 353.8s) | ✅ |
| Addestramento (ACT) e deployment della policy in simulazione (`lerobot-train` / `lerobot-rollout`) | ✅ misurato con smoke test (vedi [09](09-usage-tutorial.md)) |

## Prossimi passi (in ordine di valore)

### Fase 2 · Telecamera nella scena (in corso)

**Completato**:
- Supporto (STEP→STL) e telecamera (segnaposto costruito secondo il datasheet HBVCAM-F2170HD V22, 25×30×5.2mm) assemblati nella simulazione,
  pose regolate con `adjust_mount.py` / `adjust_camera.py` confrontando il robot reale;
- elemento `<camera>` integrato (`sim_cam`, fovy iniziale 49°), **catena di registrazione visiva in simulazione completata**:
  `--robot.image_camera=sim_cam` produce un dataset video `observation.images.wrist` (test di smoke [5] tutti superati).

**Aggiornamento 2026-10-16**: puntamento/fovy della telecamera regolati in modo soddisfacente (`adjust_camera.py` aggiunge la **finestra live view**,
regolazione con ripresa da punto di interruzione, riapertura automatica se la finestra viene chiusa per errore; inoltre corretto il bug per cui la direzione di inquadratura della telecamera MuJoCo (pari alla **−Z dell'elemento**) causava "obiettivo e immagine in direzioni opposte",
dettagli in [07](07-troubleshooting.md)). Con il nuovo leader calibrato è stato registrato ufficialmente il dataset visivo (con video wrist, errore di inseguimento ≤2 unità) ✅;
le vecchie registrazioni sperimentali sono state eliminate il 2026-10-16 e il dataset ufficiale è unificato in `so101_sim_vision` (due telecamere).
**Lo stesso giorno il robot simulato è migrato al modello SO-ARM100 di mujoco_menagerie** (2026-10-16): il gripper del modello del tutorial originale non riesce ad afferrare,
quello del nuovo modello è collisione CAD del robot reale e afferra stabilmente un cubo da 34mm; le catene di registrazione/teleoperazione/doppia telecamera/area di lavoro sono tutte conservate,
in attesa di una verifica con teleoperazione sul robot reale (in particolare il segno della direzione di wrist_roll).
**Da completare**: dopo aver collegato la HBVCAM al robot reale, regolazione comparativa "ripresa reale vs rendering simulato";
opzionale: sostituire il segnaposto con lo STL del corpo della telecamera. La configurazione delle telecamere lato robot reale (`--robot.cameras` OpenCV) sarà fatta in seguito.

### Fase 3 · Scene e scala (in corso)

- ✅ Area di lavoro nella scena (2026-10-16): tappetino + cubi di tre colori (34mm, afferrabili) + scatola di raccolta + telecamera fissa dall'alto `top_cam`
  (definita in `so101_assets.add_workspace`, strumento di rendering/verifica dei risultati `preview_workspace.py`); **catena di registrazione con due telecamere (wrist+top)
  completata** (`--robot.top_camera=top_cam`);
- **Generazione automatica dei dati**: policy scriptate/RL eseguite in batch tutta la notte in simulazione (senza operatore umano): è questa la fonte dell'aumento di efficienza di decine di volte;
- Randomizzazione del dominio visivo (texture/illuminazione/jitter della telecamera) in preparazione del sim2real.

### Fase 4 · Addestramento e deployment

- ✅ **Catena di addestramento/deployment verificata** (2026-10-16): `lerobot-train` (ACT, smoke CPU da 12 step: circa 2s/step, loss in calo regolare,
  checkpoint salvati come previsto) e `lerobot-rollout --strategy.type=base` (esecuzione effettiva della policy in simulazione per 20s,
  con ritorno automatico del braccio alla posa iniziale e chiusura) sono entrambi operativi; comandi completi, punti chiave e metodo di ripresa in [09](09-usage-tutorial.md) sezioni 7/8,
  il tutorial include un checkpoint dimostrativo `outputs/train/smoke_act` utilizzabile subito per provare la catena di deployment;
- L'addestramento ufficiale avviene su una **macchina con GPU** (ACT / SmolVLA; il solo CPU di questa macchina è adatto solo a validare la catena con pochi step);
  è sufficiente copiare il dataset o caricarlo su un repository privato HF;
- Anche il deployment sul robot reale passa da `lerobot-rollout` (sostituisci `--robot.*` con la configurazione `so101_follower`).

### Lungo termine · sim2real

Addestramento misto con dati simulati + pochi dati reali → valutazione a costo zero sul robot reale (in simulazione si può riprodurre il tasso di successo della policy).
Nota: usare direttamente dati puramente simulati sul robot reale (trasferimento zero-shot) è la strada più difficile; inizia con un "ciclo corto" (addestramento su dati reali → deployment su robot reale)
e aggiungi gradualmente la simulazione.

## Posizionamento in una frase

Per i team che hanno già un braccio fisico: la simulazione = **sandbox di sviluppo + materiale dimostrativo + amplificatore di dati**;
per potenziali clienti: la simulazione = **strumento di esperienza per percorrere l'intero flusso prima dell'acquisto**.
