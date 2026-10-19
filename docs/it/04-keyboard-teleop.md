# 04 · Teleoperazione da tastiera

Usa la tastiera per muovere "a impulsi" i giunti e controllare manualmente il braccio reale o simulato: è il modo più rapido quando non hai il braccio leader ed è anche uno dei metodi per registrare dati dimostrativi.

## Comandi

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'

# follower reale
uv run --frozen --with mujoco python examples/so101_mujoco/teleoperate.py \
    --robot.type=so101_follower --robot.port=COM172 --robot.id=juxi_so101 \
    --robot.use_degrees=false --robot.max_relative_target=5 \
    --teleop.type=so101_keyboard --teleop.rate=150

# follower simulato (la finestra MuJoCo si apre automaticamente)
uv run --frozen --with mujoco python examples/so101_mujoco/teleoperate.py \
    --teleop.rate=150
```

(`teleoperate.py` usa già per default `--robot.type=so101_mujoco --teleop.type=so101_keyboard`.)

## Tasti (attivi mentre premuti, ascolto globale: indipendentemente dalla finestra in primo piano)

| Tasto | Azione | Tasto | Azione |
| --- | --- | --- | --- |
| `w` / `s` | shoulder_lift su / giù | `a` / `z` | shoulder_pan sinistra / destra |
| `e` / `d` | elbow_flex estendi / flettere | `t` / `g` | wrist_flex + / − |
| `y` / `h` | wrist_roll + / − | `u` / `j` | gripper apri / chiudi |

I tasti sono stati scelti **volutamente evitando i tasti di controllo della registrazione** (`n/r/q`, frecce, `Esc`), così teleoperazione e registrazione possono funzionare contemporaneamente.

## Parametri principali

| Parametro | Funzione | Valore consigliato |
| --- | --- | --- |
| `--teleop.rate` | Velocità del target mentre si tiene premuto un tasto (unità/secondo) | Il default 60 è piuttosto lento; sul robot reale **150** è più adatto |
| `--robot.max_relative_target` | Quanto al massimo può muoversi un giunto per ciclo di controllo (limite di velocità di sicurezza) | Robot reale **5** (teleoperazione a 60Hz) / **10** (registrazione a 30Hz) |
| `--robot.use_degrees=false` | Usa il sistema proporzionale alla corsa (−100~100) invece dei gradi | **Obbligatorio sul robot reale**, altrimenti le unità non corrispondono (la simulazione è già allineata per default) |

## Comportamento

- **Non digitare durante la teleoperazione**: l'ascolto della tastiera è **globale e non blocca i tasti**: premere i tasti mappati in qualsiasi finestra del computer
  (`w a s z e d t g y h u j`, inclusi i caratteri digitati in una chat) aziona contemporaneamente il braccio. Con la modalità braccio leader questo problema non esiste.
- **Al momento della connessione il braccio si muove**: il follower reale prima attiva la coppia (diventa rigido), poi si sposta verso la "posizione centrale" (il target prima che si prema un tasto);
  il braccio simulato converge direttamente verso la posa centrale. Lascia spazio intorno al braccio.
- **Uscita**: `Ctrl-C` su quel terminale (oppure `Esc`: l'ascolto della tastiera si disconnette e il programma termina in modo pulito). Dopo l'uscita il robot reale **perde la coppia e diventa flaccido**:
  sostienilo con una mano, è un comportamento normale.
- **Le serie di WARNING `clamped to be safe` nel log di avvio** sono l'output normale del limitatore di velocità durante l'inseguimento; si fermano automaticamente una volta raggiunta la posizione.
