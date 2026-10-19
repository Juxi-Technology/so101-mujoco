# 08 · Hoja de ruta

## Completado (ejecutable directamente desde este repositorio)

| Capacidad | Estado |
| --- | --- |
| Verificación de carga/accionamiento/renderizado del modelo de simulación (3 MJCF) | ✅ |
| Teleoperación por teclado (simulación / robot real) | ✅ verificado en hardware real |
| Gemelo digital del brazo líder (brazo físico → brazo simulado, con ajuste fino del cero) | ✅ verificado en hardware real |
| Grabación de datos (robot real / simulación) + control de episodios + script de inspección | ✅ verificado en hardware real |
| Reproducción de datos (robot real / simulación, mecanismo oficial) | ✅ verificado en hardware real |
| Pruebas de humo automatizadas (sin hardware, `smoke_test.py`) | ✅ 26 elementos superados |
| Conjunto de datos visual con dos cámaras `so101_sim_vision` (5 episodios / 10610 fotogramas / 353.8 s) | ✅ |
| Entrenamiento (ACT) y despliegue de políticas en simulación (`lerobot-train` / `lerobot-rollout`) | ✅ probado con smoke test (ver [09](09-usage-tutorial.md)) |

## Próximos pasos (ordenados por valor)

### Fase 2 · Cámara en la escena (en curso)

**Completado**:
- El soporte (STEP→STL) y la cámara (cuerpo provisional construido según la hoja de datos HBVCAM-F2170HD V22, 25×30×5.2 mm) se ensamblaron en la simulación;
  las poses se ajustaron por comparación con el robot real mediante `adjust_mount.py` / `adjust_camera.py`;
- Se integró el elemento `<camera>` (`sim_cam`, fovy inicial 49°) y **la cadena de grabación visual en simulación está operativa**:
  `--robot.image_camera=sim_cam` genera un conjunto de datos de vídeo `observation.images.wrist` (prueba de humo [5] superada por completo).

**Actualización del 2026-10-16**: la puntería/fovy de la cámara ya está ajustada a satisfacción (`adjust_camera.py` añade una **ventana de imagen en tiempo real live view**,
con ajuste reanudable y reapertura automática si se cierra la ventana por error; además se corrigió el bug de que la dirección de encuadre de la cámara de MuJoCo = **−Z del elemento** causaba que «la dirección de la lente y la imagen fueran opuestas»;
detalles en [07](07-troubleshooting.md)). Se grabó oficialmente el conjunto de datos visual con el brazo líder recién calibrado (con vídeo wrist, error de seguimiento ≤2 unidades) ✅;
las grabaciones experimentales antiguas se limpiaron el 2026-10-16 y el conjunto de datos oficial se unificó como `so101_sim_vision` (dos cámaras).
**Ese mismo día, el robot de simulación se migró al modelo SO-ARM100 de mujoco_menagerie** (2026-10-16): la pinza del modelo del tutorial original no podía agarrar;
la pinza del nuevo modelo usa colisión CAD del robot real y en pruebas sujeta de forma estable cubos de 34 mm; se conservan todas las cadenas de grabación/teleoperación/dos cámaras/área de trabajo,
pendiente de una revisión con teleoperación en el robot real (especialmente el signo de la dirección de wrist_roll).
**Pendiente**: al conectar la HBVCAM real, hacer un ajuste fino comparativo «captura real vs render de simulación»;
opcional: sustituir el cuerpo provisional por el STL real de la cámara. La configuración de cámaras en el lado del robot real (`--robot.cameras` con OpenCV) se hará después.

### Fase 3 · Escena y escalado (en curso)

- ✅ El área de trabajo entra en la escena (2026-10-16): placa de apoyo + cubos de tres colores (34 mm, agarrables) + caja de almacenamiento + cámara cenital fija `top_cam`
  (definidos en `so101_assets.add_workspace`; herramienta de renderizado/verificación de prestaciones `preview_workspace.py`); **la cadena de grabación con dos cámaras (wrist+top)
  está operativa** (`--robot.top_camera=top_cam`);
- **Generación automática de datos**: políticas scriptadas/RL ejecutándose en lote toda la noche en simulación (sin humano en el bucle); de aquí viene el «aumento de eficiencia de decenas de veces»;
- Aleatorización de dominio visual (texturas/iluminación/vibración de cámara) para preparar sim2real.

### Fase 4 · Entrenamiento y despliegue

- ✅ **La cadena de entrenamiento/despliegue está probada** (2026-10-16): `lerobot-train` (ACT, smoke test de 12 pasos en CPU: unos 2 s/paso, loss descendiendo con normalidad,
  checkpoint guardado según lo previsto) y `lerobot-rollout --strategy.type=base` (ejecuta realmente la política 20 s en simulación y
  termina devolviendo automáticamente el brazo a la pose inicial) están operativos; los comandos completos, puntos clave y el método de continuación del entrenamiento están en [09](09-usage-tutorial.md), secciones 7/8,
  el checkpoint de demostración incluido en el tutorial `outputs/train/smoke_act` puede usarse directamente para probar la cadena de despliegue;
- El entrenamiento formal se realiza en **una máquina con GPU** (ACT / SmolVLA; la CPU pura de esta máquina solo sirve para validar la cadena con pocos pasos);
  basta con copiar el conjunto de datos o subirlo a un repositorio privado de HF;
- El despliegue en el robot real también usa `lerobot-rollout` (cambiando `--robot.*` por la configuración de `so101_follower`).

### Largo plazo · sim2real

Entrenamiento mixto con datos de simulación + pocos datos reales → evaluación sin coste en el robot real (en simulación se puede reproducir la evaluación de la tasa de éxito de la política).
Nota: pasar datos puramente simulados directamente al robot real (transferencia zero-shot) es la ruta más difícil; empieza con un «bucle corto» (entrenar con datos reales → desplegar en el robot real)
e incorpora la simulación de forma gradual.

## Posicionamiento en una frase

Para equipos que ya tienen un brazo físico: la simulación = **entorno de pruebas de desarrollo + material de demostración + amplificador de datos**;
para potenciales clientes: la simulación = **una herramienta de experiencia para recorrer todo el flujo antes de comprar**.
