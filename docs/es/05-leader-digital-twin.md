# 05 · Gemelo digital del brazo líder (el brazo físico acciona el brazo simulado)

Mueve con la mano el **brazo líder físico** para que el **brazo seguidor simulado en la ventana de MuJoCo** lo reproduzca en tiempo real: la forma correcta de hacer
demostraciones de gemelo digital y captura de datos en simulación.

## Requisitos previos

El brazo líder debe estar calibrado (consulta [03](03-hardware-calibration.md)); se usa `COM163` como ejemplo de puerto serie.

## Comando

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
uv run --frozen --with mujoco python examples/so101_mujoco/teleoperate.py \
    --robot.type=so101_mujoco \
    --teleop.type=so101_leader_trim --teleop.port=COM163 --teleop.id=juxi_leader \
    --teleop.use_degrees=false
```

- `--robot.type=so101_mujoco`: el objeto controlado es el brazo simulado; la ventana se abre automáticamente;
- `--teleop.*`: el dispositivo de control es el brazo líder físico (solo lectura, nunca aplica par, riesgo cero para el brazo líder);
- `--teleop.use_degrees=false`: **obligatorio**. Hace que las unidades que emite el brazo líder (sistema de proporción del recorrido) coincidan con las del brazo simulado.

Si cambias `--robot.type` por `so101_follower --robot.port=COM172 --robot.id=juxi_so101 --robot.max_relative_target=5`,
obtienes el uso habitual del kit «brazo líder físico → brazo seguidor real»; la misma calibración del brazo líder sirve para ambos.

## ¿Qué hacer si el cero está desviado? Ajuste automático del centro (`so101_leader_trim`)

**Síntoma**: aunque el brazo líder se coloque en la «posición central visual», el brazo simulado se desvía unos grados.

**Principio**: el cero normalizado de lerobot = **el punto medio del rango registrado durante el barrido de calibración** `(min+max)/2`; en cambio, la «pose central» al pulsar
Enter en la calibración se registra como el valor bruto 2048. Mientras el recorrido mecánico de una articulación sea asimétrico, los dos «puntos medios» siempre difieren en una cantidad fija
(medición real del servo n.º 1: rango registrado 776~3457, punto medio 2116, diferencia de 68 cuentas respecto a 2048 ≈ **5.6°**).
**Esta desviación no se elimina recalibrando** (la asimetría del recorrido la determina la estructura mecánica); hay que compensarla por software.

**Solución**: el plugin `so101_leader_trim` calcula automáticamente la compensación de cada articulación a partir del archivo de calibración con la fórmula y la resta en tiempo real;
tras recalibrar se adapta automáticamente, sin ajustes manuales:

```
补偿ᵢ = (2048 − minᵢ) / (maxᵢ − minᵢ) × 200 − 100
```

Valores efectivos medidos en esta máquina (se imprimen en el log de arranque):

| Articulación | Compensación (unidades) |
| --- | --- |
| shoulder_pan | −5.11 |
| shoulder_lift | −0.92 |
| elbow_flex | +2.54 |
| wrist_flex | +0.69 |

El resto de articulaciones tiene una desviación <0.05 y no necesita compensación; la pinza (0~100) y el modo en grados no participan en el ajuste fino.

> Nota para desarrolladores: el `name` de este plugin debe seguir siendo `"so_leader"`; `name` es la clave del directorio de búsqueda de archivos de calibración,
> y un nombre de tipo personalizado haría que no se encontrara el archivo de calibración y se activara por error el proceso de recalibración.
