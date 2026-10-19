# 01 · Preparación del entorno

Operación única. Este repositorio usa **uv para gestionar un `.venv` aislado dentro del proyecto**: `uv run` solo utilizará el entorno de este directorio,
nunca tocará tu conda (este diseño es intencional; consulta [07 Problemas frecuentes](07-troubleshooting.md)).

## Instalación

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'   # 本机特例，见 07

# CPU 版 torch（本机无独显；有 NVIDIA GPU 的机器去掉 UV_TORCH_BACKEND 并参考 pyproject 注释换 CUDA 版）
UV_TORCH_BACKEND=cpu uv sync --frozen --extra core_scripts --extra feetech --extra pynput-dep --extra training
```

Propósito de los cuatro extras:

| extra | Qué proporciona | Quién lo necesita |
| --- | --- | --- |
| `core_scripts` | Entradas oficiales record / teleoperate / calibrate / replay + conjuntos de datos + dependencias de visualización | Todos |
| `feetech` | `scservo_sdk` (protocolo serie de los servos STS3215) | Operaciones con el robot real |
| `pynput-dep` | Escucha global del teclado | Teleoperación por teclado, teclas de control de episodios durante la grabación |
| `training` | `accelerate` / `wandb`, etc. | Entrenamiento con `lerobot-train`, despliegue de políticas (`lerobot-rollout`) |

Cuando haga falta, añade MuJoCo de forma temporal (no entra en el archivo de bloqueo; se carga bajo demanda):

```bash
uv run --frozen --with mujoco python <脚本>
```

**¿Prefieres cambiar a un entorno conda?** Entonces los comandos ya no necesitan el prefijo `uv run`; los tres comandos para crear el entorno y los puntos a tener en cuenta están en
[09 Tutorial de uso completo · Apéndice A](09-usage-tutorial.md).

## Verificación

```bash
uv run --frozen --with mujoco python -c "import mujoco, scservo_sdk, pynput, lerobot, torch; print('OK')"
uv run --frozen lerobot-calibrate --help | head -3   # 官方入口可用
```

## Problemas frecuentes

- **`uv sync` muestra `failed to persist temporary file ... os error 17`**: caso especial de esta máquina por tener el directorio de caché de uv
  en otro disco; basta con usar el prefijo `UV_CACHE_DIR` de arriba; consulta [07](07-troubleshooting.md) para más detalles.
- **No uses la versión de Python de Microsoft Store**: elige el Python 3.12 gestionado automáticamente por uv.
- La primera ejecución de `uv run --with mujoco` descarga un wheel de mujoco de unos 5.6 MB; después se usa la caché.
