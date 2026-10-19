# 07 · Problemas frecuentes y experiencia

Problemas realmente encontrados en este flujo, para consultar rápidamente por síntoma.

## Entorno

| Síntoma | Causa y solución |
| --- | --- |
| `uv sync` muestra `failed to persist temporary file ... os error 17（跨盘）` | Caso especial de Windows en esta máquina: el directorio de caché de uv está en otro disco. Añade `export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'` delante de todos los comandos uv |
| La consola imprime decenas de líneas de fallo al cargar `libtorchcodec_core*.dll` | Aviso de ruido: si torchcodec no carga, se recurre automáticamente a **pyav**. Verificado (smoke [5]): pyav **codifica y decodifica los conjuntos de datos de vídeo con normalidad**; ni los conjuntos de datos de estado ni los de vídeo se ven afectados |
| `python` abre Microsoft Store | Usa el Python gestionado por uv; no uses la versión de Store |

## Teleoperación

| Síntoma | Causa y solución |
| --- | --- |
| El control por teclado «va muy lento» | `--teleop.rate` por defecto es 60 unidades/s, demasiado conservador; con **150** la sensación es normal (recorrido completo en unos 1.3 s) |
| El log de arranque se llena de WARNING `clamped to be safe` | Salida normal del limitador de velocidad mientras alcanza la posición; se detiene al llegar |
| Al centrar el brazo líder, el brazo simulado se desvía unos grados | Desviación fija causada por la asimetría del rango de calibración; usa el ajuste automático de `so101_leader_trim` ([05](05-leader-digital-twin.md)) |
| El brazo se mueve bruscamente al conectar | Es el comportamiento diseñado: en el robot real aplica par y se mueve hacia el punto medio/la pose del brazo líder; deja espacio alrededor |
| Tras salir con Ctrl-C el brazo se vuelve blando y cae | Normal: al desconectar se desactiva el par; sujétalo con la mano |
| Escribir durante la teleoperación/grabación acciona el brazo | La escucha del teclado es **global y no consume las teclas**: pulsar teclas mapeadas en cualquier ventana (incluidas letras de pinyin) entra en la cola de teclas. No escribas durante la teleoperación/grabación en modo teclado; con el modo de brazo líder no ocurre |

## Grabación

| Síntoma | Causa y solución |
| --- | --- |
| Tras salir con `q`, las letras pulsadas durante la sesión «se vuelcan de golpe en la línea de comandos» | Eco acumulado del búfer de entrada de la consola de Windows; el lanzador ya incorpora la limpieza `drain_pending_keys()` (solo ocurría en sesiones antiguas) |
| Un episodio tiene action span todo a 0 | Grabación vacía (nadie se movió): muévete antes de grabar o borra ese episodio después |
| El error es grande durante el primer segundo del episodio | Tramo de convergencia: al iniciar la grabación el brazo seguidor sigue en la pose inicial y el brazo líder ya está en otro sitio; evitarlo colocando antes el brazo líder cerca del punto medio |
| Tras configurar `--dataset.root` con el directorio padre, el conjunto de datos «desaparece» | **root es el propio directorio del conjunto de datos**; usa un root nuevo en cada grabación |
| Diferencia entre `Esc` y `q` | `q` solo detiene la grabación; `Esc` además desconecta la teleoperación por teclado. Ambos cierran limpiamente (corregido); acostúmbrate a usar `q` |
| Al guardar, `ValueError: You must add one or several frames...` y el proceso termina con error | Se pulsó `→`/`n` de más **entre episodios** (lo más habitual: el guardado + la codificación de doble vídeo se detiene durante decenas de segundos, la consola parece colgada y uno pulsa varias veces), la marca permanece hasta el inicio del siguiente episodio y se consume → **episodio vacío de 0 fotogramas**; upstream falla al guardar un episodio vacío (límite conocido de lerobot). **Los episodios ya guardados no se ven afectados y los datos están intactos**; reabre la sesión y continúa grabando. **Ya hay protección** (2026-10-16): `record.py` limpia al inicio de cada episodio las marcas `→`/`←` que quedaron retenidas durante el intervalo (las teclas siguen funcionando durante la grabación) y, antes de guardar, imprime el aviso `saving the episode + encoding videos now...`; prueba de regresión `smoke_test.py` [7] |
| `KeyError: 'wrist'` en el instante de iniciar la grabación (conjuntos de datos con imagen) | El bucle de grabación leía la observación antes de que la cámara hubiera renderizado el primer fotograma; **corregido** (2026-10-16): ahora el `connect()` del plugin del robot espera a que el primer fotograma esté listo antes de regresar |
| Un script con vídeo da `BrokenProcessPool` / `Invalid argument: '<stdin>'` | La codificación de vídeo usa un **grupo de multiprocesos** y los procesos hijos reimportan el módulo de entrada a partir de la ruta del archivo; si ejecutas el script de grabación con `python - <<EOF` (stdin), falla. Guarda el script como un archivo `.py` real y ejecútalo (la entrada real `record.py` no se ve afectada) |
| Al guardar un episodio, `SvtMalloc[fatal]: allocate memory failed ... av.error.MemoryError: [Errno 12] ... 'avcodec_open2(libsvtav1)'` y toda la sesión termina | El codificador por defecto de upstream, **libsvtav1**, falla al asignar un bloque grande de memoria al abrir a la vez dos codificaciones de dos cámaras (wrist+top) (más probable con la simulación + ventanas de vista previa; se sufrió en pruebas el 2026-10-16). **Corregido**: `record.py` inyecta por defecto `--dataset.rgb_encoder.vcodec=h264` (codificación concurrente de dos vías h264 verificada; pasar vcodec explícitamente lo sobrescribe). Los episodios ya guardados están intactos; un fallo puede dejar `tmp*/` y parquet huérfanos en el directorio del conjunto de datos (limpiar como en run2) |
| La imagen se atasca durante la grabación (sobre todo tras pulsar `→`), pero la operación en realidad no tiene retardo | Lo que se atasca es la **ventana de guardado/codificación**: los procesos de codificación usan por defecto todos los núcleos de CPU (dos vídeos concurrentes), mientras el hilo de simulación sigue renderizando 5 imágenes (más evidente con gráficos integrados). El bucle de control no se ve afectado: guíate por las cifras de cadence (medido: 29.97 Hz en todo el recorrido, 0 ticks fuera de presupuesto). **Mitigado** (2026-10-16): `record.py` usa por defecto `--dataset.encoder_threads=2` (cada codificación limitada a 2 hilos); la actualización de las ventanas de vista previa baja a 15 Hz (`--robot.preview_fps`). Cuanto más corto es el episodio, mayor es la proporción de la ventana de guardado y más se nota el atasco; para eliminar del todo la pausa puede usarse `--dataset.streaming_encoding=true` (codificación mientras se graba, recomendado por upstream, pendiente de probar) |
| Al guardar un episodio, el codificador informa **fallo de asignación de memoria** y toda la sesión termina (incluye `SvtMalloc` de svtav1, `malloc ... failed` de x264 y errores de `avcodec_open2`) | La memoria comprometida (commit) del sistema de esta máquina lleva mucho tiempo cerca del límite (medido el 2026-10-16: **105.9GB / 119.7GB**, con 29 días de encendido continuo). Cada guardado arranca 2 procesos de codificación nuevos (cada uno carga torch/av, con picos grandes de commit); lanzarlos a la vez al borde del precipicio acaba en fallo. **Mitigado**: `record.py` ahora añade **un reintento automático ante fallo** de codificación (los fallos transitorios ya no pierden episodios) y también se ha silenciado el ruido de logs durante el guardado (`av.logging.set_libav_level` + barra de progreso de HF). **Solución definitiva = reiniciar la máquina** (limpia el commit acumulado por ejecuciones largas / fugas del kernel; los procesos de usuario solo ocupan 27GB, el resto está en el kernel/drivers y no se puede matar); autocomprobación: `Get-Counter '\Memory\Committed Bytes'` vs `'\Memory\Commit Limit'` |

## Hardware

| Síntoma | Causa y solución |
| --- | --- |
| El número de COM no es el mismo que la última vez | El número de puerto serie cambia al desconectar/reconectar o cambiar de puerto; enumera los puertos antes de cada uso ([03](03-hardware-calibration.md)) |
| La comprobación de solo lectura indica servos ausentes | Problema de cableado/alimentación; revisa primero la placa controladora y el orden de los cables; no te apresures a calibrar |
| La dirección de `shoulder_lift` es contraria a la intuición (simulación) | La dirección positiva de ese modelo apunta hacia abajo; verifica el signo antes de mapear ([02](02-sim-model-verification.md)) |

## Notas de diseño (por qué se hizo así)

- **MuJoCo reescribe los datos de vértices de la malla**: tras cargar `<mesh>`, `mjModel.mesh_vert` guarda los vértices en el **sistema de coordenadas de la propia malla**
  (el origen se recoloca en el centroide de los vértices y los ejes se reordenan), ya no son las coordenadas originales del archivo; usarlos directamente para calcular la caja envolvente o tomar medidas CAD
  da resultados erróneos (la visualización del renderizado no se ve afectada). Para obtener la geometría CAD real, analiza el archivo original (como se hace en `preview_mount.py` /
  `step_to_stl.py`). Nos ocurrió una vez: el tamaño real del soporte es 54.3 × 35.0 × 75.0 mm.
- **La dirección de encuadre de la cámara de MuJoCo es el −Z de su sistema de coordenadas**: el elemento `<camera>` no mira hacia su propio +Z (la dirección en la que sobresale la lente). La primera versión
  del módulo de cámara construía la lente en +Z con el elemento orientado a identity → la imagen salía realmente «al revés» desde la parte trasera de la PCB, y **la dirección de la lente y la de la imagen
  eran exactamente opuestas** (la raíz de que «la dirección de giro no coincidiera con la imagen» al ajustar parámetros; localizado el 2026-10-16 con una prueba de renderizado comparativo con placas roja/azul).
  Corrección: el elemento de cámara gira 180° alrededor de Y (`view.quat = RPY(0,180,0)`, unificado en preview_mount / adjust_camera / plugin del robot); `adjust_camera.py` añade una ventana de imagen en tiempo real "sim_cam live view", para ajustar la lente con resultado inmediato.
- **La pinza del MJCF del tutorial oficial es una pinza de contacto puntual «en forma de pico de ave»**: las puntas de las dos piezas se cierran hasta un contacto puntual de ~2.3 mm y casi no hay superficie de agarre útil.
  La conclusión de los experimentos físicos sistemáticos (2026-10-16, cientos de configuraciones) es que, coloques el cubo donde lo coloques cerca de la boca de la pinza, será empujado/expulsado durante el barrido de cierre de ~100°
  y no se podrá sujetar (así ocurre con cubos de 16–34 mm; el recorrido mecánico y el par son normales de por sí). **Atención: no lo arregles «añadiendo piezas de colisión»**; se probó a añadir placas dentadas
  a las dos piezas (mejora mucho el agarre), pero era una **geometría que no existe en el robot real**, y las políticas entrenadas dependerían de ella, provocando distorsión sim2real; ya se retiró. La forma correcta de arreglarlo es
  **sustituir la pinza del modelo oficial por la geometría de la pinza del robot real** (por ejemplo, el SO-ARM101 de mujoco_menagerie o una reconstrucción CAD propia), manteniendo los parámetros físicos coherentes con el robot real.
- **Los parámetros de contacto por defecto oficiales son demasiado «blandos» y provocan penetración física**: la constante de tiempo `solref` por defecto es 20 ms; los contactos rápidos/finos
  (un cubo cayendo sobre una cara fina de la pinza, el barrido de cierre) se atraviesan mutuamente «antes de que dé tiempo a generar fuerza»; el síntoma es que «el cubo atraviesa la cara de la pinza y cae».
  Corrección (2026-10-16): endurecimiento de los parámetros de contacto; `harden_mesh_contacts` endurece tras la compilación el `solref` de todos los cuerpos de colisión de malla al mismo valor que las caras dentadas de menagerie (0.01 s),
  y el contacto de los cubos se trata igual. Es una corrección pura de fidelidad física; no añade geometría.
- **El robot de simulación se ha migrado al modelo SO-ARM100 de mujoco_menagerie** (2026-10-16): el MJCF del zip del tutorial original era una pieza de demostración cinemática y su pinza no podía agarrar;
  el modelo de menagerie sigue el CAD del robot real: la pinza tiene caras dentadas de colisión dedicadas y parámetros de contacto duros, y en las cuatro posiciones de los dientes (de superficial a profunda) se verifica que puede detener contra la pieza + sujetar + levantar un cubo de 34 mm.
  Puntos clave de la migración: el modelo está incluido en el repositorio en `assets/menagerie_so_arm100/` (Apache-2.0, con LICENSE); el mapeo de articulaciones y los signos de las unidades están en `MODEL_JOINT`
  (determinados articulación por articulación comparando el movimiento en el mundo con el modelo antiguo; el signo de wrist_roll queda pendiente de revisión con teleoperación en el robot real); la Base del modelo gira +90° alrededor de Z para que su
  frente de trabajo mire hacia +x; el soporte se monta ahora en el lateral de Fixed_Jaw (servo n.º 6) (primero se localizó por búsqueda analítica; el 2026-10-16 el usuario lo ajustó a mano comparando con fotos del robot real
  mediante `adjust_mount.py --model menagerie` hasta el valor final: `[0.1, -0.7, 24.7]mm`, `RPY [0.34, -27.20, 89.51]°`). El modelo y las herramientas del tutorial antiguo se conservan sin cambios para poder comparar en cualquier momento.
- **Por qué se usa un entorno de proyecto uv en lugar de conda**: el `.venv` está en el mismo directorio que el proyecto, las versiones quedan fijadas por `uv.lock` y basta borrar el directorio para recuperarlo todo;
  está completamente aislado de los entornos conda de la máquina; `uv run` nunca instala nada en el conda activado. El entorno conda `lerobot` de esta máquina
  apunta a **otra copia del repositorio** (`lerobot-main`), y ambos no se interfieren.
- **Por qué los plugins están todos en `examples/so101_mujoco/`**: se integran mediante el mecanismo oficial de registro (`register_subclass`),
  **sin modificar el código fuente de lerobot**; para actualizar upstream basta con volver a hacer sync.
