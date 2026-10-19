# 03 · Conexión y calibración del robot real

## Identificar el puerto serie

Al conectar la placa controladora con chip CH343 aparece un puerto COM; **el número cambia al conectar/desconectar o al cambiar de puerto USB**, así que confírmalo antes de cada conexión:

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
uv run --frozen python -c "import serial.tools.list_ports as lp; [print(p.device, '|', p.description, '|', p.hwid) for p in lp.comports()]"
```

## Paso 1: comprobación inicial de solo lectura (cableado/alimentación/estado de los servos)

**Sin escribir nada**, primero haz ping a los seis servos uno por uno y luego lee voltaje y temperatura (el estado de par se mantiene tal cual):

```bash
uv run --frozen python examples/so101_mujoco/hardware_check.py --port COM163
```

La salida normal tiene el aspecto de: seis líneas de articulaciones, temperatura 20~30 °C, par 0 (brazo libre). **El voltaje depende del modo de alimentación**: el brazo seguidor con fuente
externa ronda los 11 V; el brazo líder alimentado solo por la placa controladora, unos 5 V. Si se leen los seis servos completos, el cableado es correcto. Si falta alguno o el modelo no coincide,
se produce un error directamente.

## Paso 2: calibración

La calibración escribe en la EEPROM de los servos «el rango de recorrido de cada articulación + la referencia central» y lo guarda en un archivo local; **hay que calibrar una vez el brazo seguidor y otra el brazo líder**.
Los archivos de calibración de ambos brazos se guardan por separado y no se afectan entre sí:

| Dispositivo | Comando | Ubicación del archivo de calibración |
| --- | --- | --- |
| Brazo seguidor | `uv run --frozen lerobot-calibrate --robot.type=so101_follower --robot.port=COM172 --robot.id=juxi_so101` | `~/.cache/huggingface/lerobot/calibration/robots/so_follower/juxi_so101.json` |
| Brazo líder | `uv run --frozen lerobot-calibrate --teleop.type=so101_leader --teleop.port=COM163 --teleop.id=juxi_leader` | `.../calibration/teleoperators/so_leader/juxi_leader.json` |

El `id` puede tener cualquier nombre, pero **la teleoperación y la grabación posteriores deben usar el mismo id**; de lo contrario, se volverá a solicitar la calibración.

### Pasos físicos (la terminal imprime un esquema)

1. **Coloca el brazo en la pose central y pulsa Enter**: la base plana en el borde de la mesa, el brazo superior vertical hacia arriba, el antebrazo horizontal hacia delante, la rotación del hombro y la muñeca centradas
   (la «pinza» del brazo líder es un mango/gatillo). La posición de ese instante se registra como la «referencia central» de ese brazo.
2. Tras pulsar Enter, **recorre lentamente el rango completo de movimiento de cada articulación, una por una** (`wrist_roll` no necesita barrido; se trata automáticamente como vuelta completa) y pulsa Enter de nuevo para guardar.

Advertencias:

- Durante la calibración del brazo seguidor el par es 0 (el brazo está suelto); sujétalo con la mano para moverlo. El brazo líder no tiene par de por sí.
- El proceso de calibración escribe en la EEPROM de los servos (forma parte de la calibración; es normal).
- Resultados de calibración medidos en esta sesión (como referencia): recorrido de las articulaciones del brazo seguidor 1474~2688 cuentas, `wrist_roll` 4095;
  brazo líder 2208~2681 cuentas. Que el recorrido sea claramente asimétrico es normal (consulta [05 Ajuste fino del cero](05-leader-digital-twin.md) para saber por qué se hace).
