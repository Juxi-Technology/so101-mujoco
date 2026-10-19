# 09 · Tutorial de uso completo (iniciar brazo → conjunto de datos → ver vídeos → entrenar → desplegar)

> Manual de operación de principio a fin: síguelo una vez y pasarás de «conectar el brazo líder» a «la política entrenada trabajando sola en la simulación».
> Requisitos: entorno instalado según [01](01-environment.md) y brazo líder calibrado según [03](03-hardware-calibration.md)
> (en esta máquina, `juxi_leader` / COM124). Todos los problemas relacionados con la grabación están concentrados en [07](07-troubleshooting.md).

## 0 · Preparación única

```bash
# 本机所有 uv 命令都要先设（跨盘缓存特例，见 07）
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
```

Conecta el brazo líder y confirma el puerto serie (**el número puede cambiar cada vez que se conecta o desconecta**):

```bash
uv run --frozen python -c "from serial.tools import list_ports; print([p.device for p in list_ports.comports()])"
```

Deja espacio en el escritorio: la grabación abrirá **3 ventanas** (vista principal + `wrist camera - live` + `top camera - live`).

## 1 · Calentamiento con teleoperación (recomendado)

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/teleoperate.py \
    --robot.type=so101_mujoco \
    --teleop.type=so101_leader_trim --teleop.port=COM124 --teleop.id=juxi_leader \
    --teleop.use_degrees=false
```

Mueve el brazo líder y confirma que el brazo simulado lo sigue; antes de salir (Ctrl-C), deja el brazo líder **cerca de la pose central** para que no haya un gran tramo de convergencia al iniciar la grabación.

## 2 · Grabación (comando principal)

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

Puntos clave (para el resto de parámetros, consulta la tabla de [06](06-record-and-replay.md)):

| Elemento | Descripción |
| --- | --- |
| `--dataset.root` | **root es el propio directorio del conjunto de datos**; usa un directorio nuevo en cada sesión (si ya existe uno con el mismo nombre, se rechaza el inicio) |
| Valores por defecto inyectados automáticamente | Código de vídeo `h264` y 2 hilos de codificación: `record.py` imprime dos líneas de aviso al arrancar; pasar explícitamente `--dataset.rgb_encoder.vcodec=...` / `--dataset.encoder_threads=...` los sobrescribe (motivos en 07) |
| Ventanas de vista previa | Activadas por defecto (15 Hz; se desactivan con `--robot.preview_cameras=false`; `--robot.preview_fps` es ajustable) |
| `--dataset.video=true` | Las imágenes de las dos cámaras se guardan (`observation.images.wrist / top`); si solo quieres la cámara de muñeca, quita `top_camera` |

## 3 · Operación durante la grabación

| Tecla | Función |
| --- | --- |
| `→` o `n` | Termina el episodio actual y lo guarda |
| `←` o `r` | Descarta el episodio actual y vuelve a grabar en el mismo sitio |
| `q` | Termina la sesión completa y guarda el conjunto de datos |

- Al terminar un episodio, **los cubos vuelven solos a su sitio**; solo tienes que devolver el brazo líder a la pose inicial; empieza a moverte para el siguiente episodio cuando veas `Recording episode N`.
- Durante la fase de guardado (decenas de segundos), la consola imprime `[record.py] reset done; saving the episode + encoding videos now`;
  en ese periodo **las teclas se ignoran de forma segura** (una pulsación accidental no estropea ningún episodio); espera a que aparezca la siguiente línea `Recording episode` para operar.
- Los fallos de codificación tienen **reintento automático como red de seguridad** (imprime `video encode failed ... retrying once` y reintenta automáticamente a los 3 segundos); los episodios ya guardados nunca se pierden.

## 4 · Inspección

```bash
uv run --frozen python examples/so101_mujoco/inspect_dataset.py \
    --repo-id local/so101_sim_vision \
    --root examples/so101_mujoco/outputs/datasets/so101_sim_vision
```

Cómo interpretar la salida:

- **Los episodios con action span todo a 0 (o con la pinza a 0)** son grabaciones vacías/no válidas; bórralos y vuelve a grabar;
- **Un `max |act-obs|` grande al inicio de cada episodio** es el tramo de convergencia, normal; en la parte media y final debería ser inferior a ~10 unidades.

## 5 · Ver vídeos

```bash
uv run --frozen python examples/so101_mujoco/export_videos.py \
    --root examples/so101_mujoco/outputs/datasets/so101_sim_vision
```

Productos:

- `examples/so101_mujoco/outputs/videos/<数据集名>/epN_top.mp4`, `epN_wrist.mp4`: **un vídeo reproducible con doble clic por episodio y cámara**;
- `examples/so101_mujoco/outputs/renders/<数据集名>_epN_dual.png`: una imagen compuesta por episodio (fila superior cenital, fila inferior muñeca, 6 fotogramas muestreados uniformemente) para inspección visual rápida (`--no-strips` permite omitirla).

El conjunto de datos también contiene el vídeo empaquetado original (varios episodios concatenados en orden en un mismo archivo):
`outputs/datasets/<数据集名>/videos/observation.images.{top,wrist}/chunk-000/file-000.mp4`.

## 6 · Reproducción (opcional)

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/replay.py \
    --dataset.repo_id=local/so101_sim_vision \
    --dataset.root=examples/so101_mujoco/outputs/datasets/so101_sim_vision --dataset.episode=0
```

## 7 · Entrenamiento

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

| Punto clave | Descripción |
| --- | --- |
| `--policy.type` | Tipo de política; **empieza con `act`** (el que mejor encaja con este tamaño de datos/tarea); `ls src/lerobot/policies/` muestra otras opciones (diffusion / smolvla / pi0, etc.) |
| `--policy.push_to_hub=false` | **Obligatorio**: por defecto intenta subir a HuggingFace Hub y, si no hay `repo_id` configurado, da error y termina; si quieres subirla, cámbialo por `--policy.repo_id=tu_usuario/nombre_del_modelo` (requiere antes `hf auth login`) |
| `--policy.device=cpu` | En esta máquina sin GPU dedicada, usa `cpu`; en máquinas con tarjeta NVIDIA elimina este parámetro (usará cuda automáticamente) |
| Productos | `output_dir/checkpoints/<步数>/` y `checkpoints/last/pretrained_model/`; el despliegue apunta a este último; el `train_config.json` para continuar el entrenamiento también está dentro |
| Continuación | Tras una interrupción, añade al comando original: `--resume=true --config_path=<output_dir>/checkpoints/last/pretrained_model/train_config.json` |

**Rendimiento esperado en esta máquina**: CPU pura, unos **2 segundos/paso** (batch 2, dos cámaras a 480p; en la prueba de humo de 12 pasos, la loss bajó de 70 a 22, dirección normal).
Por eso esta máquina sirve para validar la cadena con pocos pasos; el `outputs/train/smoke_act` incluido en el tutorial es el producto de 12 pasos;
**para el entrenamiento formal (ACT suele requerir del orden de 100 000 pasos) se recomienda una máquina con GPU; los comandos son exactamente iguales.**

> Nota sobre dependencias: el entrenamiento requiere el extra `training` (accelerate, etc.). Si aparece `accelerate is required but not installed`,
> añade `--extra training` siguiendo el comando de instalación de [01](01-environment.md) y vuelve a intentarlo.

## 8 · Despliegue (hacer que la política trabaje sola en la simulación)

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/rollout.py \
    --policy.path=examples/so101_mujoco/outputs/train/act_so101_sim_vision/checkpoints/last/pretrained_model \
    --strategy.type=base \
    --robot.image_camera=sim_cam --robot.top_camera=top_cam \
    --task="put the cube in the box" --duration=30
```

| Punto clave | Descripción |
| --- | --- |
| Parámetros de cámara | `--robot.image_camera/--robot.top_camera` **deben coincidir con los usados al grabar el conjunto de datos** (sim_cam + top_cam); de lo contrario la política no recibe las imágenes con las que se entrenó |
| `--task` | Debe coincidir con `--dataset.single_task` usado al grabar |
| `--duration` | Segundos tras los cuales termina automáticamente (antes de terminar devuelve el brazo a la pose inicial y se desconecta); también se puede detener con `Ctrl-C` |
| Para probar primero la cadena | Usa el modelo de demostración incluido en el tutorial: `--policy.path=examples/so101_mujoco/outputs/train/smoke_act/checkpoints/last/pretrained_model` (12 pasos de entrenamiento; los movimientos son casi aleatorios, solo valida la cadena) |
| Despliegue en CPU pura | La inferencia de la política tiene picos ocasionales de 0.5 s y muestra `Control loop is running slower ... than the target FPS`: en simulación funciona pero con tirones; con GPU no ocurre (en la prueba de humo de 20 s se ejecutó todo el tiempo y terminó con normalidad) |
| Despliegue en robot real | Cambia `--robot.*` al robot real: `--robot.type=so101_follower --robot.port=COMxx --robot.id=juxi_so101 --robot.use_degrees=false` (deja espacio en el escritorio) |
| Otros modos | `--strategy.type=sentry / highlight / dagger / episodic`: grabar mientras se ejecuta / guardado por tecla con búfer circular / corrección con humano en el bucle / grabación por episodios; consulta `lerobot-rollout --help` |

## Apéndice A · Cambiar a un entorno conda (opcional)

Este repositorio usa por defecto un **`.venv` aislado dentro del proyecto gestionado por uv** (consulta [01](01-environment.md)), y los comandos se ejecutan con
el prefijo `uv run --frozen --with mujoco`. Si prefieres conda, **sustituye el paso de «crear el entorno» por los tres comandos siguientes**,
y después **quita el prefijo uv de todos los comandos** (`python examples/...` se ejecuta directamente); `UV_CACHE_DIR` tampoco hará falta
(es el caso especial de caché entre discos de uv, sin relación con conda):

```bash
# 一次性：在仓库根目录建好环境（python 版本对齐 01 的 3.12）
conda create -n lerobot-sim python=3.12 -y
conda activate lerobot-sim
pip install -e .            # 安装本仓库 lerobot 及其依赖（含 torch，Windows 上 pip 默认就是 CPU 版）
pip install "mujoco==3.16"  # uv 路线用 --with mujoco 临时提供，conda 路线装成常驻依赖
```

A partir de entonces, por ejemplo, la grabación queda así:

```bash
python examples/so101_mujoco/record.py --robot.image_camera=sim_cam ...
```

Dos advertencias:

1. **Alineación de versiones**: `pip install -e .` deja que pip resuelva las versiones por su cuenta y puede que no coincidan exactamente con `uv.lock`;
   si quieres una combinación idéntica al entorno probado actual, instala con uv en el entorno conda según el archivo de bloqueo:

   ```bash
   uv pip sync uv.lock --python "$(conda run -n lerobot-sim python -c 'import sys; print(sys.executable)')"
   pip install "mujoco==3.16"
   ```

2. La caché de calibración del brazo líder está en `~/.cache/huggingface/lerobot/calibration/` y no depende del entorno usado; al cambiar de entorno no hace falta recalibrar.

## Apéndice B · Consulta rápida de problemas frecuentes

| Síntoma | En una frase |
| --- | --- |
| El puerto serie no se abre | Enumera primero los puertos; el número puede haber cambiado (paso 0) |
| La consola queda en silencio decenas de segundos al guardar | Está codificando, es normal; cuando veas el aviso `saving the episode...`, no pulses teclas |
| La imagen se atasca de vez en cuando durante la grabación | Competencia por recursos de codificación en la ventana de guardado; el bucle de control no se ve afectado (guíate por las cifras de cadence); detalles en 07 |
| ¿Se puede salvar tras un fallo? | Los episodios ya guardados nunca se pierden; continúa con `record.py --resume=true ... --dataset.num_episodes=N` |
| `lerobot-train` muestra `'repo_id' argument missing` | Por defecto intenta subir a Hub: añade `--policy.push_to_hub=false` (si quieres subir, configura `--policy.repo_id` y ejecuta antes `hf auth login`) |
| Durante el despliegue la política no se mueve o se mueve de forma errática | Comprueba primero que `--robot.image_camera/--robot.top_camera` y `--task` coincidan con los de la grabación; luego revisa si se entrenaron muy pocos pasos |

Todos los problemas y soluciones (incluidos memoria escasa, OOM de codificación, episodios vacíos, etc.) están en [07 · Problemas frecuentes](07-troubleshooting.md).
