# 07 · Problemas comuns e lições aprendidas

Obstáculos realmente encontrados neste fluxo, para consulta rápida por sintoma.

## Ambiente

| Sintoma | Causa e solução |
| --- | --- |
| O `uv sync` apresenta `failed to persist temporary file ... os error 17（跨盘）` | Caso especial do Windows em que o diretório de cache do uv desta máquina atravessa discos. Antes de todos os comandos uv, acrescente `export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'` |
| A consola mostra dezenas de linhas de falha ao carregar `libtorchcodec_core*.dll` | Aviso ruidoso: após a falha do torchcodec, há fallback automático para **pyav**. Medição (smoke [5]): o pyav **codifica e descodifica normalmente conjuntos de dados de vídeo**; nem os conjuntos de dados de estado nem os de vídeo são afetados |
| `python` abre a Microsoft Store | Use o Python gerido pelo uv; não use a versão da Store |

## Teleoperação

| Sintoma | Causa e solução |
| --- | --- |
| O controlo por teclado «muito lento» | O `--teleop.rate` predefinido de 60 unidades/s é conservador; aumente para **150** para uma sensação normal (curso completo em cerca de 1,3s) |
| O registo de arranque enche-se de WARNING `clamped to be safe` | Saída normal durante a recuperação do limitador de velocidade; para quando chega à posição |
| O braço simulado desvia-se alguns graus quando o braço líder está centrado | Desvio fixo causado pela assimetria do intervalo de calibração — use o ajuste automático `so101_leader_trim` ([05](05-leader-digital-twin.md)) |
| O braço move-se subitamente no instante da ligação | É o comportamento previsto: no robô real aplica binário e move-se para o ponto médio/pose do braço líder; mantenha espaço livre à volta |
| Após sair com Ctrl-C, o braço fica mole e cai | Normal: o binário é desligado ao desconectar; segure-o com a mão |
| Escrever durante a teleoperação/gravação aciona o braço | A escuta do teclado é **global e não consome teclas**: premir teclas mapeadas em qualquer janela (incluindo letras de pinyin) entra na fila de teclas. Não escreva durante teleoperação/gravação no modo teclado; o modo com braço líder não tem este problema |

## Gravação

| Sintoma | Causa e solução |
| --- | --- |
| Após sair com `q`, as letras premidas durante a sessão «saem todas de uma vez na linha de comandos» | Eco acumulado do buffer de entrada da consola Windows; o lançador já inclui a limpeza `drain_pending_keys()` (o fenómeno só ocorre em sessões antigas) |
| Numa sessão, o action span é todo 0 | Gravação vazia (ninguém se moveu) — mexa-se antes de gravar ou elimine o episódio depois |
| Erro elevado no primeiro segundo do episódio | Segmento de convergência: no instante em que a gravação começa, o seguidor ainda está na pose inicial e o braço líder já parou noutro sítio; colocar o braço líder perto da posição média antes evita-o |
| Depois de configurar `--dataset.root` como diretório pai, o conjunto de dados «desaparece» | **O root é o próprio diretório do conjunto de dados**; use um novo root em cada gravação |
| Diferença entre `Esc` e `q` | `q` apenas para a gravação; `Esc` também desliga a teleoperação por teclado. Ambos terminam de forma limpa (corrigido); habitue-se a usar `q` |
| Ao guardar, `ValueError: You must add one or several frames...` e o processo termina com o erro | Premiu `→`/`n` a mais **entre** episódios (o caso mais comum: a pausa de guardar + codificar os dois vídeos demora dezenas de segundos, a consola parece bloqueada e alguém carrega várias vezes), o sinal fica retido e é consumido no início do episódio seguinte → **episódio vazio de 0 frames**; o upstream rebenta ao guardar um episódio vazio (limitação conhecida do lerobot). **Os episódios já guardados não são afetados, os dados estão intactos**; reabra a sessão e continue a gravar. **Proteção adicionada** (2026-10-16): o `record.py` limpa no início de cada episódio os sinais `→`/`←` retidos no intervalo (as teclas continuam a funcionar durante a gravação) e imprime `saving the episode + encoding videos now...` antes de guardar; teste de regressão `smoke_test.py` [7] |
| No instante de início da gravação, `KeyError: 'wrist'` (conjunto de dados com imagens) | O ciclo de gravação leu a observação antes de o primeiro frame da câmara estar renderizado; **corrigido** (2026-10-16): o `connect()` do plugin do robô espera agora que o primeiro frame esteja pronto antes de retornar |
| Scripts com vídeo dão `BrokenProcessPool` / `Invalid argument: '<stdin>'` | A codificação de vídeo usa um **pool multiprocesso** e os subprocessos reimportam o módulo de entrada através do caminho do ficheiro — executar o script de gravação com `python - <<EOF` (stdin) rebenta. Guarde o script num ficheiro `.py` real e execute-o (o ponto de entrada real `record.py` não é afetado) |
| Ao guardar um episódio, `SvtMalloc[fatal]: allocate memory failed ... av.error.MemoryError: [Errno 12] ... 'avcodec_open2(libsvtav1)'` e a sessão inteira termina | O codificador predefinido upstream **libsvtav1** falha uma grande alocação de memória única quando as duas codificações (wrist+top) abrem em simultâneo (mais provável sob carga da simulação + janelas de pré-visualização; observado em 2026-10-16). **Corrigido**: o `record.py` injeta por omissão `--dataset.rgb_encoder.vcodec=h264` (codificação dupla h264 em simultâneo validada; passar vcodec explicitamente sobrepõe-se). Os episódios já guardados ficam intactos; o crash pode deixar `tmp*/` e parquet órfãos no diretório do conjunto de dados (limpar como no run2) |
| A imagem fica aos soluços durante a gravação (especialmente depois de premir `→`), mas a operação não tem atraso | O que engasga é a **janela de guardar/codificar**: os processos de codificação usam todos os núcleos por omissão (duas codificações em simultâneo), enquanto a thread da simulação continua a renderizar 5 imagens (mais notório em gráfica integrada). O ciclo de controlo em si não é afetado — guie-se pelos números de cadence (29,97Hz durante todo o percurso, 0 ticks acima do orçamento na medição). **Mitigado** (2026-10-16): `record.py` usa por omissão `--dataset.encoder_threads=2` (2 threads por codificação); a atualização das janelas de pré-visualização das câmaras desceu para 15Hz (`--robot.preview_fps`). Quanto mais curto o episódio, maior o peso da janela de guardar e mais se nota o engasgo; para eliminar completamente a pausa, pode usar `--dataset.streaming_encoding=true` (codificar durante a gravação, recomendado upstream, por testar) |
| Ao guardar um episódio, o codificador reporta **falha de alocação de memória** e a sessão termina (o `SvtMalloc` do svtav1, o `malloc ... failed` do x264 e erros `avcodec_open2` pertencem todos a esta categoria) | O commit de memória do sistema desta máquina está persistentemente perto do limite (2026-10-16: **105,9GB / 119,7GB**, com 29 dias de uptime). Cada gravação lança 2 processos de codificação novos (cada um carrega torch/av, com picos de commit elevados) e iniciá-los em simultâneo à beira do penhasco dá asneira. **Mitigado**: o `record.py` agora faz **uma nova tentativa automática** da codificação em caso de falha (falhas transitórias já não perdem episódios) e o ruído de registo durante a gravação foi silenciado (`av.logging.set_libav_level` + barra de progresso do HF). **Solução definitiva = reiniciar a máquina** (limpar o commit acumulado de longa duração / fugas do kernel; os processos de utilizador só ocupam 27GB, o resto está no kernel/drivers e não se consegue matar); autodiagnóstico: `Get-Counter '\Memory\Committed Bytes'` vs `'\Memory\Commit Limit'` |

## Hardware

| Sintoma | Causa e solução |
| --- | --- |
| O número da porta COM é diferente da última vez | O número da porta série muda ao desligar/ligar ou mudar de porta; liste sempre as portas antes ([03](03-hardware-calibration.md)) |
| A inspeção só de leitura indica servo-motores em falta | Problema de ligação/alimentação; verifique primeiro a placa controladora e a ordem dos fios, não se apresse a calibrar |
| A direção de `shoulder_lift` é contraintuitiva (simulação) | A direção positiva deste modelo aponta para baixo; verifique o sinal antes do mapeamento ([02](02-sim-model-verification.md)) |

## Notas de conceção (porque foi feito assim)

- **O MuJoCo reescreve os dados dos vértices da malha**: depois de carregar um `<mesh>`, o `mjModel.mesh_vert` guarda os vértices no **sistema de coordenadas da própria malha**
  (a origem é recentrada no centro de gravidade dos vértices e os eixos são reordenados), deixando de corresponder às coordenadas originais do ficheiro — usá-lo diretamente para calcular a caixa envolvente ou aplicar dimensões CAD
  produz resultados errados (a renderização não é afetada). Para obter a geometria CAD real, analise o ficheiro original (como fazem `preview_mount.py` /
  `step_to_stl.py`). Já aconteceu uma vez: as dimensões reais do suporte são 54.3 × 35.0 × 75.0 mm.
- **A direção de enquadramento das câmaras MuJoCo é o −Z do seu sistema de coordenadas**: o elemento `<camera>` não olha na direção do seu +Z (a direção em que a lente se projeta). A primeira versão
  do módulo de câmara construiu a lente em +Z com a orientação do elemento em identity → a imagem era na prática vista «ao contrário» a partir da parte de trás da PCB, com **a orientação da lente e a direção da imagem
  exatamente opostas** (a raiz do «o sentido de rotação não corresponde à imagem» ao ajustar parâmetros; localizado em 2026-10-16 com testes de renderização comparativa com placas vermelha/azul).
  Correção: rodar o elemento da câmara 180° em torno de Y (`view.quat = RPY(0,180,0)`, uniformizado nos três locais: preview_mount / adjust_camera / plugin do robô);
  o `adjust_camera.py` ganhou uma janela de imagem em tempo real "sim_cam live view", para ajustar a lente com resultado imediato.
- **A pinça do MJCF do tutorial oficial é uma pinça de contacto pontual «tipo bico de ave»**: as duas pontas dos dentes fecham até um contacto pontual de ~2.3 mm, quase sem superfície de agarre útil.
  Conclusão de experiências físicas sistemáticas (2026-10-16, centenas de ensaios): um cubo colocado em qualquer posição perto da abertura dos dentes é empurrado/expelido durante o varrimento de fecho de
  ~100°, não sendo possível agarrá-lo (o mesmo para cubos de 16–34 mm; o curso mecânico e o binário estão normais). **Atenção: não corrigir «acrescentando placas de colisão»** — tentou-se acrescentar
  placas dentadas às duas garras (melhorava significativamente o agarre), mas trata-se de **geometria que não existe no robô real**; uma política treinada passaria a depender dela, causando distorção sim2real, pelo que foi removida.
  A correção correta é **substituir as garras do modelo oficial pela geometria das garras do robô real** (por exemplo, o SO-ARM101 do
  mujoco_menagerie ou uma reconstrução CAD própria), mantendo os parâmetros físicos coerentes com o robô real.
- **Os parâmetros de contacto predefinidos oficiais são demasiado «moles» e causam interpenetração física**: a constante de tempo `solref` predefinida é 20 ms; contactos rápidos/finos
  (um cubo a cair sobre a face fina da garra, o varrimento de fecho) atravessam-se mutuamente «antes de haver tempo para gerar força» — o sintoma é «o cubo atravessa a face da garra e cai».
  Correção (2026-10-16): endurecimento dos parâmetros de contacto — `harden_mesh_contacts` endurece, após a compilação, o `solref` de todos os corpos de colisão de malha
  para o mesmo valor usado nas faces dentadas do menagerie (0.01 s), aplicando o mesmo tratamento ao contacto dos cubos. Correção pura de fidelidade física, sem acrescentar geometria.
- **O robô simulado foi migrado para o modelo SO-ARM100 do mujoco_menagerie** (2026-10-16): o MJCF do zip do tutorial original é
  uma peça de demonstração cinemática, com garras incapazes de agarrar; o modelo do menagerie segue o CAD do robô real — as garras têm faces dentadas de colisão dedicadas e parâmetros de contacto rígidos,
  e as quatro posições dos dentes (raso→fundo) conseguem, na medição, travar + agarrar + levantar um cubo de 34mm. Pontos da migração: o modelo está vendored em
  `assets/menagerie_so_arm100/` (Apache-2.0, inclui LICENSE); o mapeamento de articulações e os sinais das unidades estão em `MODEL_JOINT`
  (determinado articulação a articulação por comparação do movimento no mundo com o modelo antigo; o sinal de wrist_roll aguarda confirmação por teleoperação no robô real); a Base do modelo é rodada +90° em Z para que a
  frente de trabalho aponte para +x; o suporte passa a ser montado na face lateral da Fixed_Jaw (servo n.º 6) (primeiro localizado por pesquisa analítica; em 2026-10-16 o utilizador
  afinou manualmente com `adjust_mount.py --model menagerie` comparando com fotografias do robô real: `[0.1, -0.7, 24.7]mm`, `RPY [0.34, -27.20, 89.51]°`). O modelo e as ferramentas do tutorial antigo foram mantidos intactos, para comparação a qualquer momento.
- **Porque usar o ambiente de projeto uv em vez de conda**: a `.venv` está no mesmo diretório do projeto, tem versões fixadas pelo `uv.lock` e é recuperada ao eliminar o diretório,
  ficando completamente isolada dos ambientes conda da máquina; o `uv run` nunca instala nada no conda ativo. O ambiente conda `lerobot` desta máquina
  aponta para **outra cópia do repositório** (`lerobot-main`); ambos não interferem entre si.
- **Porque os plugins estão todos em `examples/so101_mujoco/`**: são integrados através do mecanismo oficial de registo (`register_subclass`),
  **sem qualquer modificação ao código-fonte do lerobot**; atualizar o upstream exige apenas um novo sync.
