# 04 · Teleoperación por teclado

Usa el teclado para «mover a pasos» las articulaciones y controlar manualmente el brazo real o simulado: la forma más rápida de controlar cuando no se dispone del brazo líder, y también uno de los medios para grabar datos de demostración.

## Comando

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'

# 真机从动臂
uv run --frozen --with mujoco python examples/so101_mujoco/teleoperate.py \
    --robot.type=so101_follower --robot.port=COM172 --robot.id=juxi_so101 \
    --robot.use_degrees=false --robot.max_relative_target=5 \
    --teleop.type=so101_keyboard --teleop.rate=150

# 仿真从动臂（MuJoCo 窗口自动打开）
uv run --frozen --with mujoco python examples/so101_mujoco/teleoperate.py \
    --teleop.rate=150
```

(`teleoperate.py` ya usa por defecto `--robot.type=so101_mujoco --teleop.type=so101_keyboard`.)

## Teclas (se activan al mantenerlas pulsadas, escucha global: no importa qué ventana tenga el foco)

| Tecla | Acción | Tecla | Acción |
| --- | --- | --- | --- |
| `w` / `s` | shoulder_lift arriba / abajo | `a` / `z` | shoulder_pan izquierda / derecha |
| `e` / `d` | elbow_flex extender / flexionar | `t` / `g` | wrist_flex + / − |
| `y` / `h` | wrist_roll + / − | `u` / `j` | pinza abrir / cerrar |

Las teclas se eligieron **evitando deliberadamente las teclas de control de grabación** (`n/r/q`, las flechas, `Esc`), de modo que la teleoperación y la grabación pueden ejecutarse a la vez.

## Parámetros clave

| Parámetro | Función | Valor recomendado |
| --- | --- | --- |
| `--teleop.rate` | Velocidad objetivo al mantener pulsada una tecla (unidades/segundo) | El valor por defecto, 60, es algo lento; en el robot real **150** resulta más adecuado |
| `--robot.max_relative_target` | Cuántas unidades como máximo puede moverse una articulación por ciclo de control (limitación de seguridad) | Robot real **5** (teleoperación a 60 Hz) / **10** (grabación a 30 Hz) |
| `--robot.use_degrees=false` | Usar el sistema de proporción del recorrido (−100~100) en lugar de grados | **Obligatorio en el robot real**; de lo contrario las unidades no coinciden (en simulación coincide por defecto) |

## Comportamiento

- **No escribas durante la teleoperación**: la escucha del teclado es **global y no consume las teclas**; pulsar teclas mapeadas
  en cualquier ventana del ordenador (`w a s z e d t g y h u j`, incluido el pinyin en un cuadro de chat) también accionará el brazo. Con el modo de brazo líder este problema no existe.
- **El brazo se mueve al conectar**: el brazo seguidor real primero aplica par (se vuelve rígido) y luego se mueve hacia la «pose central» (el objetivo antes de pulsar teclas);
  el brazo simulado converge directamente a la pose central. Deja espacio alrededor del brazo.
- **Salir**: pulsa `Ctrl-C` en esa terminal (o `Esc`; la escucha del teclado se desconecta y el programa termina limpiamente). Tras salir, el robot real **pierde el par y se vuelve blando**;
  sujétalo con la mano: es el comportamiento normal.
- **Las series de WARNING `clamped to be safe` en el log de arranque** son la salida normal del limitador de velocidad mientras «alcanza» la posición; se detienen automáticamente al llegar.
