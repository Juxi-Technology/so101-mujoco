# 01 · Preparazione dell'ambiente

Operazione da fare una sola volta. Questo repository usa **uv per gestire un `.venv` isolato all'interno del progetto**:
`uv run` utilizza solo l'ambiente presente in questa directory e non tocca il tuo conda (scelta intenzionale, vedi
[07 Problemi comuni](07-troubleshooting.md)).

## Installazione

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'   # caso particolare di questa macchina, vedi 07

# torch versione CPU (questa macchina non ha GPU dedicata; su macchine con GPU NVIDIA rimuovi UV_TORCH_BACKEND e consulta i commenti di pyproject per la versione CUDA)
UV_TORCH_BACKEND=cpu uv sync --frozen --extra core_scripts --extra feetech --extra pynput-dep --extra training
```

Scopo dei quattro extra:

| extra | Cosa fornisce | A chi serve |
| --- | --- | --- |
| `core_scripts` | Punti di ingresso ufficiali record / teleoperate / calibrate / replay + dataset + dipendenze di visualizzazione | Tutti |
| `feetech` | `scservo_sdk` (protocollo seriale dei servo STS3215) | Operazioni sul robot reale |
| `pynput-dep` | Ascolto globale della tastiera | Teleoperazione da tastiera, tasti di controllo degli episodi durante la registrazione |
| `training` | `accelerate` / `wandb` ecc. | Addestramento con `lerobot-train`, deployment della policy (`lerobot-rollout`) |

Quando serve, MuJoCo viene aggiunto temporaneamente (non entra nel file di lock, viene caricato su richiesta):

```bash
uv run --frozen --with mujoco python <脚本>
```

**Vuoi passare a un ambiente conda?** In quel caso i comandi non richiedono più il prefisso `uv run`: i tre comandi
per creare l'ambiente e le relative avvertenze sono in [09 Tutorial d'uso completo · Appendice A](09-usage-tutorial.md).

## Verifica

```bash
uv run --frozen --with mujoco python -c "import mujoco, scservo_sdk, pynput, lerobot, torch; print('OK')"
uv run --frozen lerobot-calibrate --help | head -3   # punto di ingresso ufficiale disponibile
```

## Problemi comuni

- **`uv sync` segnala `failed to persist temporary file ... os error 17`**: caso particolare di questa macchina dovuto
  alla directory di cache uv su un altro disco; usa il prefisso `UV_CACHE_DIR` qui sopra, dettagli in [07](07-troubleshooting.md).
- **Non usare il Python del Microsoft Store**: scegli il Python 3.12 gestito automaticamente da uv.
- Il primo `uv run --with mujoco` scarica il wheel di mujoco (circa 5,6 MB), poi usa la cache.
