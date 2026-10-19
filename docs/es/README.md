# Tutorial completo SO-ARM101 × MuJoCo (índice)

> 🌐 Languages: [简体中文](../README.md) · [English](../en/README.md) · [Deutsch](../de/README.md) · **Español** · [Français](../fr/README.md) · [Italiano](../it/README.md) · [日本語](../ja/README.md) · [한국어](../ko/README.md) · [Português (BR)](../pt-br/README.md) · [Português (PT)](../pt-pt/README.md) · [繁體中文](../zh-hant/README.md)

> Este tutorial documenta y reproduce el **flujo de trabajo completo de simulación + robot real** del SO-ARM101: desde la preparación del entorno, la verificación del modelo y la calibración del robot real,
> hasta la teleoperación por teclado/brazo líder y la grabación y reproducción de datos. Todos los comandos se validaron en una sesión de robot real + simulación el 2026-10-15.
>
> Dirigido a: usuarios del kit Juxi SO-ARM101 e ingenieros internos. No se requieren conocimientos previos de MuJoCo ni de LeRobot.

## Mapa del flujo completo (dos vías, un conjunto de componentes compartido)

```
                         ┌──────────────── 共用组件 ────────────────┐
                         │  数据集格式(LeRobotDataset) · 回放 · 未来训练  │
                         └──────────────────────────────────────────┘
                                      ▲                    ▲
        ┌── 真机轨 ──────────────────┘                    └──────────── 仿真轨 ──┐
        │  操控: 主动臂(实体) / 键盘                                      操控: 键盘 / 主动臂(实体) │
        │  被控: 真机从动臂 (COM 串口)                                    被控: MuJoCo 仿真从动臂   │
        │  命令: --robot.type=so101_follower                            命令: --robot.type=so101_mujoco │
        └───────────────────────────────────────────────────────────────────────┘
```

| Cap. | Contenido | Lo que obtendrás |
| --- | --- | --- |
| [01 Preparación del entorno](01-environment.md) | Entorno uv, extras de dependencias, consideraciones para Windows | Un entorno funcional |
| [02 Verificación del modelo de simulación](02-sim-model-verification.md) | Carga/comparación/renderizado de los tres modelos MJCF | Confianza en el modelo y el comportamiento de la simulación |
| [03 Conexión y calibración del robot real](03-hardware-calibration.md) | Identificación del puerto serie, comprobación inicial de solo lectura, calibración del brazo seguidor/líder | Dos brazos reconocibles por el software |
| [04 Teleoperación por teclado](04-keyboard-teleop.md) | Control por teclado del robot real/simulado, ajuste de velocidad, limitación de seguridad | La forma más rápida de control manual |
| [05 Gemelo digital del brazo líder](05-leader-digital-twin.md) | El brazo líder físico acciona el brazo seguidor simulado, ajuste fino del cero | Demostración de gemelo digital y captura de datos |
| [06 Grabación y reproducción de datos](06-record-and-replay.md) | Grabar robot real/simulación/control de episodios/reproducción/script de inspección | Un conjunto de datos entrenable |
| [07 Problemas frecuentes y experiencia](07-troubleshooting.md) | Todos los obstáculos encontrados en este flujo y sus soluciones | Manual de resolución de problemas |
| [08 Hoja de ruta](08-roadmap.md) | Cámara, escena con objetos, generación automática de datos, entrenamiento | Planes para los próximos pasos |
| [09 Tutorial de uso completo](09-usage-tutorial.md) | Iniciar brazo → grabar → inspeccionar → ver vídeos → entrenar → desplegar en simulación, todo en uno; incluye alternativa con entorno conda | De cero a un conjunto de datos válido, y después la política en acción |

## Tres convenciones que debes recordar

1. **Sistema de unidades (alineación entre las tres partes)**: las cinco articulaciones del cuerpo usan **−100~100** (proporción del recorrido; 0 = punto medio del recorrido) y la pinza usa **0~100**
   (0 = cerrada). El robot real (`use_degrees=false`), la simulación y el brazo líder cumplen todos esta convención; los conjuntos de datos grabados tienen la misma estructura que los conjuntos de datos reales
   oficiales como `lerobot/svla_so101_pickplace` (vector de 6 dimensiones + nombres de articulaciones).
2. **Correspondencia de roles**: el objeto controlado (robot real o simulación) siempre se configura con `--robot.*`; el dispositivo de control (teclado/brazo líder) siempre con `--teleop.*`.
3. **Prefijo de comandos en esta máquina**: en este equipo de desarrollo, todos los comandos `uv` requieren configurar antes el directorio de caché (la razón está en [07](07-troubleshooting.md)):

   ```bash
   export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
   ```

## Entorno probado

| Elemento | Versión |
| --- | --- |
| Sistema | Windows 11 |
| Python / uv | 3.12.9 / 0.12.5 |
| lerobot | 0.6.2 (este repositorio, `.venv` aislado del proyecto, no afecta a conda) |
| MuJoCo | 3.16.0 |
| PyTorch | 2.11.0 (versión CPU) |
| Hardware | SO-ARM101 brazo líder (COM163) + brazo seguidor (COM172), chip de puerto serie CH343 |
