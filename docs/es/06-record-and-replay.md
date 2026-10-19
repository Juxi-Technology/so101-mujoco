# 06 · Grabación y reproducción de datos

## Plantilla de comandos de grabación

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'

# 录真机（主动臂 → 真机从动臂）
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

# 录仿真（主动臂 → 仿真从动臂）
#   把 --robot.* 换成: --robot.type=so101_mujoco
# 录仿真（键盘控制）
#   把 --teleop.* 换成: --teleop.type=so101_keyboard --teleop.rate=150
```

## Puntos clave de los parámetros (los que suelen dar problemas)

| Parámetro | Descripción |
| --- | --- |
| `--dataset.root` | **root es el propio directorio del conjunto de datos** (no una concatenación de directorio padre + repo_id); usa un directorio nuevo en cada grabación |
| `--dataset.repo_id` | En grabaciones locales solo es un identificador; para subirlo a Hub en el futuro hará falta un `usuario/nombre` real |
| `--dataset.no_stamp=true` | No añade sufijo de marca de tiempo; el directorio/nombre es estable; para regrabar con el mismo nombre hay que borrar antes el directorio antiguo |
| `--dataset.episode_time_s` | **Límite superior** de un episodio (por seguridad); en operación normal se termina antes con `→` |
| `--dataset.reset_time_s` | Tiempo de reposición entre episodios que no se graba; durante él el brazo líder sigue accionando el brazo seguidor en tiempo real. **Al grabar en simulación, los cubos se teletransportan automáticamente a su posición inicial al entrar en esta fase** (ver abajo) |
| `--dataset.video` | Actívalo solo cuando necesites datos de cámara (los conjuntos de datos visuales lo requieren en true; el respaldo con pyav está verificado y funciona) |
| `--dataset.rgb_encoder.vcodec` | Codificador de vídeo. **En esta máquina, para grabar con dos cámaras se usa `h264`**: `record.py` ya lo inyecta por defecto (el valor por defecto de upstream, libsvtav1, al abrir dos codificaciones concurrentes falla en la asignación de memoria y hace caer toda la sesión; consulta [07](07-troubleshooting.md)); si se pasa explícitamente, no se inyecta |
| `--dataset.encoder_threads` | Número de hilos de codificación. **`record.py` inyecta 2 por defecto**: usar todos los núcleos por defecto hace que la imagen de simulación se atasque notablemente durante el guardado (consulta [07](07-troubleshooting.md)); limitando cada codificación a 2 hilos, la simulación se mantiene fluida al guardar; si se pasa explícitamente, no se inyecta |
| `--dataset.push_to_hub` | En esta máquina, la conexión directa a HF necesita proxy; déjalo en false y súbelo manualmente al terminar la grabación |

## Teclas de control de episodios (globales, activas durante toda la grabación)

| Tecla | Función |
| --- | --- |
| `→` o `n` | Termina el episodio actual (**guardar**) |
| `←` o `r` | Descarta el episodio actual y **vuelve a grabar en el mismo sitio** (úsalo si un episodio no te convence; no hace falta reiniciar la sesión) |
| `q` | Termina la sesión completa y guarda el conjunto de datos (**recomendado**) |
| `Esc` | Igual que `q` (además desconecta la teleoperación por teclado; se ha verificado que sale limpiamente, pero se prefiere `q`) |

**Consejo de operación**: antes de empezar a grabar, deja el brazo líder cerca de la pose central (para evitar que se grabe el tramo de convergencia en el que el brazo simulado/real «salta» al iniciar);
una vez iniciada la grabación, permanece quieto un segundo antes de empezar a moverte.

## Reinicio automático de la escena al grabar en simulación

Al grabar con el robot real, en la fase «Reset the environment» tienes que colocar manualmente los cubos en su sitio. En simulación, el lanzador de grabación (`record.py`)
**teletransporta automáticamente los tres cubos a su posición de origen** al comenzar esa fase (poniendo también su velocidad a cero); por tanto, después de terminar cada episodio con `→`,
solo tienes que devolver el brazo líder a la pose inicial: los cubos vuelven solos y el siguiente episodio empieza desde una escena inicial fija.
El brazo seguidor real no tiene este comportamiento (se colocan a mano como siempre); `teleoperate.py`/`replay.py` tampoco lo incluyen.

## Inspección tras la grabación

```bash
uv run --frozen python examples/so101_mujoco/inspect_dataset.py \
    --repo-id local/so101_sim_vision \
    --root examples/so101_mujoco/outputs/datasets/so101_sim_vision
```

Muestra el número de fotogramas, la duración, la amplitud de movimiento de las seis articulaciones y el error de seguimiento de cada episodio:

- **Los episodios con action span = 0** son grabaciones vacías (nadie se movió); bórralos y vuelve a grabar;
- **Un |action−obs| grande al principio** es el tramo de convergencia (normal); en la parte media y final suele ser <10 unidades.

## Grabar datos «con imagen» en simulación (cámara de muñeca)

El robot simulado permite grabar en el conjunto de datos la cámara de muñeca de la escena (`sim_cam`) como observación de imagen:

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

Puntos clave: `--robot.image_camera=sim_cam` (nombre de la cámara) + `--dataset.video=true` (las imágenes se codifican como vídeo; el respaldo con pyav está verificado y funciona).
En las características del conjunto de datos aparecerá `observation.images.wrist` (480×640×3). La resolución y la tasa de fotogramas se ajustan con
`--robot.image_width/--robot.image_height/--robot.image_fps`.
Cuando la ventana está activada (`onscreen=true`, valor por defecto), además de la ventana de vista principal se abre **una ventana de vista previa en tiempo real por cada cámara**
(muñeca / cenital, con una etiqueta en la esquina superior izquierda); durante la grabación puedes ver directamente si las dos imágenes están bien. Si no las necesitas, añade
`--robot.preview_cameras=false`. Las ventanas de vista previa se actualizan por defecto a **15 Hz** (`--robot.preview_fps` es ajustable):
son indicadores de estado y no necesitan seguir los 50 Hz de la ventana principal, de modo que la carga de renderizado con 3 ventanas en pantalla es mucho menor.

**Escena y cámara cenital (desde el 2026-10-16)**: la escena de simulación incluye un área de trabajo: placa de apoyo, cubos de tres colores (34 mm), caja de almacenamiento (consulta `so101_assets.add_workspace`;
la disposición puede ajustarse renderizando con `preview_workspace.py`); además hay una cámara cenital fija `top_cam` (la parte superior de la imagen = dirección alejada del brazo).
Con `--robot.top_camera=top_cam` la imagen cenital se graba como `observation.images.top` (dos cámaras a la vez); si solo quieres la cámara de muñeca, quita ese parámetro.
La codificación de vídeo tras cada episodio procesa ambas imágenes, por lo que un tiempo de espera algo mayor es normal.

## Reproducción

```bash
# 仿真空回放（窗口里看轨迹重演）
uv run --frozen --with mujoco python examples/so101_mujoco/replay.py \
    --dataset.repo_id=local/so101_sim_vision \
    --dataset.root=examples/so101_mujoco/outputs/datasets/so101_sim_vision --dataset.episode=0

# 真机回放（同款机制，注意周围环境与录制时一致）
uv run --frozen --with mujoco python examples/so101_mujoco/replay.py \
    --robot.type=so101_follower --robot.port=COM172 --robot.id=juxi_so101 \
    --robot.use_degrees=false --robot.max_relative_target=10 \
    --dataset.repo_id=local/juxi_so101_teleop \
    --dataset.root=examples/so101_mujoco/outputs/datasets/juxi_teleop_run1 --dataset.episode=0
```

> La entrada oficial `lerobot-replay` no carga los plugins de este proyecto; usarla directamente da `invalid choice: 'so101_mujoco'`;
> por eso se usa siempre el lanzador `replay.py`.

## Formato y ubicación del conjunto de datos

El conjunto de datos es LeRobotDataset v3: `action` y `observation.state` son ambos vectores de 6 dimensiones
(`shoulder_pan.pos … gripper.pos`), igual que los conjuntos de datos reales oficiales, y pueden mezclarse directamente para entrenar.

```
examples/so101_mujoco/outputs/datasets/
└── juxi_teleop_run1/   真机键盘遥操（1 回合 / 2430 帧 / 81s）✅ 保留的真机数据

> 2026-10-16 清理：旧的仿真录制（`sim_run2`、`sim_vision_demo`、`sim_vision_run1/2/3`）
> 已全部删除。**正式数据集 `so101_sim_vision`（双相机 / 5 回合 / 10610 帧 / 353.8s / h264）
> 已于当晚录成 ✅**；每回合单机视频导出在 `outputs/videos/so101_sim_vision/`，
> 双相机预览拼图在 `outputs/renders/sim_vision_epN_dual.png`。
```

## Registro de pruebas de esta sesión (2026-10-15)

| Sesión | Contenido | Resultado |
| --- | --- | --- |
| Robot real run1 | Teleoperación por teclado grabando el robot real | 1 episodio de 81 s; amplitud de las seis articulaciones 75~140 unidades; estable a 30 Hz |
| Reproducción en robot real | Repetición del mismo episodio | 2430 fotogramas reproducidos íntegramente, sin anomalías |
| Simulación run2 | Teleoperación con brazo líder grabando en simulación | 5 episodios, 157 s; error de seguimiento de ep1~4 <12 unidades |
| Reproducción en simulación ep1 | Repetición en la ventana | Trayectoria coherente con la operación (confirmado) |

## Pruebas adicionales (2026-10-16)

| Sesión | Contenido | Resultado |
| --- | --- | --- |
| Brazo líder nuevo (COM124) | Recalibración (brazo/servos nuevos) | ✅ Calibración correcta; la compensación de cero de `so101_leader_trim` se adapta automáticamente a la nueva calibración |
| Visión run1 | Teleoperación con brazo líder grabando en simulación (con imagen) | 2 episodios / 3177 fotogramas / 106 s @ 29.97 Hz; error de seguimiento ≤2 unidades en todo el recorrido (solo 0.5 s de convergencia en el primer fotograma); el vídeo `observation.images.wrist` se guardó en el conjunto de datos y se verificó decodificándolo ✅ |
| Visión run2 | Continuación de grabación con dos cámaras (`--resume`) | ep0 (2776 fotogramas / 92.6 s) intacto; al guardar ep1, el codificador libsvtav1 se quedó sin memoria (OOM) y toda la sesión se cayó → se cambió el codificador a h264 (inyectado por defecto por `record.py`) y se verificó de extremo a extremo (2 episodios × codificación de dos vías); los restos se limpiaron y la regrabación oficial pasó a run3 |
| Visión run3 | Grabación oficial con dos cámaras (h264) | Sesión 1: ep0 (185.2 s / 5554 fotogramas) + ep1 (72.8 s / 2186 fotogramas) guardados correctamente e inspección superada; pulsar `→` repetidamente durante la pausa de codificación entre sesiones provocó un fallo por episodio vacío (mecanismo y protección en [07](07-troubleshooting.md)) → se continuó en otra sesión para grabar los episodios restantes (plan de 5 episodios) |
| Primera grabación oficial (so101_sim_vision) | Dos cámaras (h264 + 2 hilos + ventanas de vista previa a 15 Hz) | Al guardar ep0 (82.3 s / 2469 fotogramas), el codificador falló en la asignación de memoria y toda la sesión se cayó (commit del sistema casi lleno; consulta [07](07-troubleshooting.md)) → se añadieron **reintento automático ante fallo de codificación** y **silenciado de la consola** (ambos verificados, 26 pruebas de humo superadas); se volverá a grabar oficialmente tras reiniciar la máquina |
| Grabación oficial (so101_sim_vision) ✅ | Teleoperación con brazo líder y dos cámaras, 5 episodios | **5/5 episodios guardados**: 61.5 / 53.4 / 101.1 / 62.4 / 75.4 s, en total 10610 fotogramas @29.97 Hz, 0 ticks fuera de presupuesto, cero fallos; las seis articulaciones + la pinza con movimiento válido durante todo el recorrido; verificación por decodificación de ambos vídeos superada |
