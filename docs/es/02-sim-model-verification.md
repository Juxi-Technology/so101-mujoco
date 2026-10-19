# 02 · Verificación del modelo de simulación (carga y accionamiento de MJCF)

## Origen de los modelos

Los tres modelos MJCF públicos del SO-ARM101 se han verificado y son utilizables en este proyecto:

| Abreviatura | Archivo | Origen |
| --- | --- | --- |
| Oficial - calibración nueva | `SO101/so101_new_calib.xml` | Repositorio oficial TheRobotStudio/SO-ARM100; **el zip del tutorial de este repositorio incluye una copia idéntica** (byte a byte) |
| Oficial - calibración antigua | `SO101/so101_old_calib.xml` | Mismo repositorio (no está en el zip; hay que descargarlo) |
| Paquete de descripción ROS2 | `so_arm101_description/mjcf/so_arm101.xml` | Adjunto del tutorial de este repositorio `SO-ARM101_ROS2.zip` |

Nota: el proceso de extracción del zip lo proporciona y conserva la versión temprana de `so101_assets.py` para consulta; desde el 2026-10-16 el robot de simulación se ha migrado al
**modelo SO-ARM100 de mujoco_menagerie** (incluido en el repositorio en `assets/menagerie_so_arm100/`;
los motivos y puntos clave de la migración están en las notas de diseño de [07](07-troubleshooting.md)).

## Verificación de accionamiento y renderizado

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
uv run --frozen --with mujoco python examples/so101_mujoco/load_and_drive.py \
    --model "<模型路径>" --out-dir out
```

El script genera un resumen estructural (articulaciones/actuadores/ganancias/rangos), renderiza un vídeo de verificación y fotogramas fijos con un «barrido secuencial de las seis articulaciones + seno coordinado».
Hay ejemplos del resumen estructural en `reports/` (incluidos en el repositorio); el vídeo de referencia (`media/`) ocupa mucho y no se distribuye con el repositorio: puede regenerarse en cualquier momento con el comando de arriba.

## Diferencias clave entre los tres modelos (medidas)

| Elemento | Oficial - calibración nueva | Oficial - calibración antigua | Paquete de descripción ROS2 |
| --- | --- | --- | --- |
| Semántica del cero | **Punto medio del recorrido** de la articulación | Posición **totalmente extendida** horizontal | Punto medio del recorrido |
| Nombre de articulaciones | `shoulder_pan` | Igual que a la izquierda | `shoulder_pan_joint` (sufijo) |
| Ganancia de posición | kp=998.22, kv=2.731 | **kp=17.8, kv=0** | kp=998.22 |
| Unidades de la pinza | hinge en radianes | hinge en radianes | **normalizado 0~1** |
| Exclusión de autocolisión | No | No | Sí (6 pares) |

**Error de seguimiento medido**: la calibración nueva y el paquete de descripción mantienen un error en reposo de 0.0005 rad; la calibración antigua, 0.03 rad (una caída de unos 1.7°, con kp 56 veces más débil).
Al evaluar una misma política en simulación, cambiar de modelo produce dinámicas distintas; ten en cuenta qué versión se está usando.

## Comportamientos del modelo que debes recordar

1. **La dirección positiva de `shoulder_lift` apunta hacia abajo**: en el par de accionamiento, «bajar el brazo» usa ángulos positivos; verifica el signo antes de hacer mapeos de teleoperación o conversiones de datos.
2. **Tocar el suelo bloquea**: el límite de descenso hace que la punta toque el suelo y se detenga (el script incorpora una protección de 8 cm respecto al suelo que recorta automáticamente la amplitud).
3. Los modelos oficiales no tienen cámara ni keyframes; existe la variante con cámara `so101_new_calib_camera.xml`, que podrá usarse más adelante para grabar datos visuales.
