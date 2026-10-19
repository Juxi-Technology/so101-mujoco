# 07 · Perguntas frequentes e experiências

Armadilhas realmente encontradas neste fluxo, para consulta rápida por sintoma.

## Ambiente

| Sintoma | Causa e solução |
| --- | --- |
| `uv sync` reporta `failed to persist temporary file ... os error 17（跨盘）` | Caso especial do Windows em que o diretório de cache do uv desta máquina fica em outro disco. Adicione `export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'` antes de todos os comandos uv |
| O console exibe dezenas de linhas de falha ao carregar `libtorchcodec_core*.dll` | Aviso ruidoso: após a falha do torchcodec, o **pyav** é usado como fallback. Testado (smoke [5]): o pyav **codifica e decodifica conjuntos de dados de vídeo normalmente**; conjuntos de dados de estado e de vídeo não são afetados |
| `python` abre a Microsoft Store | Use o Python gerenciado pelo uv; não use a versão da Store |

## Teleoperação

| Sintoma | Causa e solução |
| --- | --- |
| Controle por teclado "muito lento" | `--teleop.rate` padrão de 60 unidades/s é conservador; aumente para **150** para uma sensação normal (curso completo em cerca de 1,3 s) |
| O log de inicialização exibe WARNINGs `clamped to be safe` | Saída normal do limitador de velocidade durante o alcance; para ao chegar ao alvo |
| Com o braço líder centralizado, o braço simulado fica alguns graus deslocado | Desvio fixo causado pela assimetria da faixa de calibração — use o ajuste automático do `so101_leader_trim` ([05](05-leader-digital-twin.md)) |
| O braço se move repentinamente no instante da conexão | É comportamento de projeto: no robô real, ele aplica torque e se move para o ponto central/pose do braço líder; mantenha espaço livre ao redor |
| Após sair com Ctrl-C, o braço fica mole e cai | Normal: o torque é desligado ao desconectar; segure com a mão |
| Digitar durante a teleoperação/gravação aciona o braço | A escuta do teclado é **global e não consome teclas**: qualquer tecla mapeada pressionada em qualquer janela (incluindo letras de pinyin) entra na fila de teclas. Não digite durante teleoperação/gravação no modo teclado; o modo braço líder não tem esse problema |

## Gravação

| Sintoma | Causa e solução |
| --- | --- |
| Após sair com `q`, as letras pressionadas durante a sessão "despejam-se todas de uma vez no terminal" | Eco acumulado do buffer de entrada do console do Windows; o iniciador já embute `drain_pending_keys()` para limpar (só sessões antigas apresentam esse sintoma) |
| Em algum episódio, o action span é todo 0 | Gravação vazia (ninguém se moveu) — mova algo antes de gravar ou exclua o episódio depois |
| Erro grande no primeiro segundo do episódio | Trecho de convergência: no instante em que a gravação começa, o braço seguidor ainda está na pose inicial e o braço líder já está em outro lugar; posicionar o braço líder perto do centro antes evita isso |
| Depois de configurar `--dataset.root` como diretório pai, o conjunto de dados "desaparece" | **root é o próprio diretório do conjunto de dados**; troque para um novo root a cada gravação |
| Diferença entre `Esc` e `q` | `q` apenas para a gravação; `Esc` também desconecta a teleoperação por teclado. Ambos encerram de forma limpa (corrigido); prefira `q` |
| Ao salvar, `ValueError: You must add one or several frames...` e o processo sai com erro | Foram pressionadas teclas `→`/`n` extras **no intervalo** entre episódios (o caso mais comum: o salvamento + codificação dupla de vídeo leva dezenas de segundos, o console parece travado e a pessoa pressiona várias vezes), o sinal fica retido e é consumido no início do episódio seguinte → **episódio vazio de 0 quadros**, e o upstream trava ao salvar episódio vazio (limitação conhecida do lerobot). **Os episódios já salvos não são afetados, os dados estão íntegros**; basta reabrir a sessão e continuar gravando. **Proteção adicionada** (2026-10-16): o `record.py` limpa os sinais `→`/`←` retidos no intervalo no início de cada episódio (teclas durante a gravação continuam funcionando normalmente), e antes de salvar imprime o aviso `saving the episode + encoding videos now...`; teste de regressão `smoke_test.py` [7] |
| No instante de iniciar a gravação, `KeyError: 'wrist'` (conjunto de dados com imagem) | O primeiro quadro da câmera ainda não havia sido renderizado quando o loop de gravação leu a observação; **corrigido** (2026-10-16): o `connect()` do plugin do robô agora espera o primeiro quadro ficar pronto antes de retornar |
| Scripts com vídeo reportam `BrokenProcessPool` / `Invalid argument: '<stdin>'` | A codificação de vídeo usa um **pool de multiprocessos** e o processo filho precisa reimportar o módulo de entrada pelo caminho do arquivo — executar o script de gravação via `python - <<EOF` (stdin) causa o crash. Salve o script como um arquivo `.py` real e execute (a entrada real `record.py` não é afetada) |
| Ao salvar o episódio, o codificador reporta `SvtMalloc[fatal]: allocate memory failed ... av.error.MemoryError: [Errno 12] ... 'avcodec_open2(libsvtav1)'` e a sessão inteira termina | O codificador padrão upstream **libsvtav1** falha numa única grande alocação de memória ao abrir duas codificações simultâneas (wrist+top), sobretudo sob carga da simulação + janelas de pré-visualização (medido em 2026-10-16). **Corrigido**: o `record.py` injeta `--dataset.rgb_encoder.vcodec=h264` por padrão (codificação dupla h264 simultânea validada; passar vcodec explicitamente sobrescreve). Episódios já salvos permanecem íntegros; o crash pode deixar `tmp*/` e parquets órfãos no diretório do conjunto de dados (limpe como no run2) |
| A imagem fica travada durante a gravação (especialmente após pressionar `→`), mas a operação em si não atrasa | O que trava é a **janela de salvamento/codificação**: os processos de codificação consomem toda a CPU por padrão (duas codificações simultâneas), enquanto a thread da simulação continua renderizando 5 telas (mais perceptível em GPU integrada). O loop de controle em si não é afetado — use os números de cadence como referência (medido: 29,97 Hz o tempo todo, 0 ticks acima do orçamento). **Mitigado** (2026-10-16): o `record.py` usa `--dataset.encoder_threads=2` por padrão (cada codificação limitada a 2 threads); a atualização das janelas de pré-visualização das câmeras caiu para 15 Hz (`--robot.preview_fps`). Quanto mais curto o episódio, maior a proporção da janela de salvamento e mais travado parece; para eliminar totalmente a pausa, use `--dataset.streaming_encoding=true` (codifica enquanto grava, recomendado pelo upstream, ainda a testar) |
| Ao salvar o episódio, o codificador reporta **falha de alocação de memória** e a sessão inteira sai (`SvtMalloc` do svtav1, `malloc ... failed` do x264, erros de `avcodec_open2` estão todos nessa categoria) | A memória comprometida (commit) do sistema desta máquina fica permanentemente próxima do limite (medido em 2026-10-16: **105,9 GB / 119,7 GB**, 29 dias de uptime contínuo). Cada salvamento inicia 2 processos de codificação (cada um carrega torch/av, pico de commit grande); iniciá-los em paralelo à beira do limite dá errado. **Mitigado**: o `record.py` agora faz **nova tentativa automática uma vez** em caso de falha de codificação (falhas transitórias não perdem mais o episódio), e o log durante o salvamento também foi silenciado (`av.logging.set_libav_level` + barra de progresso do HF). **Solução definitiva = reiniciar a máquina** (limpar o commit acumulado de longa execução / vazamentos do kernel; os processos de espaço de usuário ocupam apenas 27 GB, o restante está no kernel/drivers e não dá para matar); autoverificação: `Get-Counter '\Memory\Committed Bytes'` vs `'\Memory\Commit Limit'` |

## Hardware

| Sintoma | Causa e solução |
| --- | --- |
| O número da porta COM está diferente da última vez | O número da porta serial muda com desconexão/reconexão ou troca de porta; liste as portas antes de cada conexão ([03](03-hardware-calibration.md)) |
| A verificação somente leitura indica servo faltando | Problema de fiação/alimentação; verifique a placa driver e a ordem dos fios primeiro, não se apresse em calibrar |
| A direção de `shoulder_lift` é oposta à intuição (simulação) | A direção positiva desse modelo aponta para baixo; verifique o sinal antes do mapeamento ([02](02-sim-model-verification.md)) |

## Notas de projeto (por que fazemos assim)

- **O MuJoCo reescreve os dados de vértice das malhas**: após carregar um `<mesh>`, o `mjModel.mesh_vert` contém os vértices no **sistema de coordenadas da própria malha**
  (a origem é redefinida para o centroide dos vértices e os eixos são reordenados), não mais nas coordenadas originais do arquivo — usá-lo diretamente para calcular a caixa delimitadora/dimensionar CAD produz
  resultados errados (a exibição da renderização não é afetada). Para obter a geometria real do CAD, analise o arquivo original (como fazem `preview_mount.py` /
  `step_to_stl.py`). Já erramos uma vez: a dimensão real do suporte é 54,3 × 35,0 × 75,0 mm.
- **A direção de enquadramento da câmera do MuJoCo é o −Z do seu sistema de coordenadas**: o elemento `<camera>` não olha para o próprio +Z (direção de protrusão da lente). A primeira versão do
  módulo de câmera construía a lente em +Z e o elemento com orientação identity → a imagem na verdade saía "de trás para frente" a partir do verso da PCB, **com a direção da lente e a direção da imagem
  exatamente opostas** (a raiz de "o sentido de rotação não bate com a imagem" ao ajustar parâmetros; localizado em 2026-10-16 com testes de renderização comparativa usando placas vermelha/azul).
  Correção: o elemento de câmera foi girado 180° em torno de Y (`view.quat = RPY(0,180,0)`, unificado nos três pontos: preview_mount / adjust_camera / plugin do robô); o `adjust_camera.py` ganhou uma janela de imagem em tempo real "sim_cam live view", em que o que você vê é o que a lente capta.
- **A garra do MJCF do tutorial oficial é uma garra de contato pontual tipo "bico de pássaro"**: as duas pontas dos dentes fecham em contato pontual a ~2,3 mm, praticamente sem superfície de preensão útil.
  Experimentos físicos sistemáticos (2026-10-16, centenas de configurações) concluíram: um cubo colocado em qualquer posição próxima à abertura dos dentes é
  empurrado/expulso durante a varredura de fechamento de ~100°, sendo impossível agarrá-lo (o mesmo para cubos de 16–34 mm; o curso mecânico e o torque em si estão normais). **Atenção: não conserte adicionando
  "placas de colisão"** — já tentamos adicionar placas dentadas às duas garras (melhora significativa na preensão), mas essa é uma **geometria que não existe no robô real**; a política treinada passaria a
  depender dela, causando distorção sim2real, e isso foi removido. A correção correta é **substituir a garra do modelo oficial pela geometria da garra do robô real** (por exemplo, o
  SO-ARM101 do mujoco_menagerie ou uma reconstrução a partir do CAD próprio), mantendo os parâmetros físicos consistentes com o robô real.
- **Os parâmetros de contato padrão oficiais são "macios" demais e causam penetração física**: a constante de tempo `solref` padrão é 20 ms, e contatos rápidos/finos
  (cubo caindo sobre a superfície fina da garra, varredura de fechamento) se atravessam mutuamente "antes de gerar força" — o sintoma é "o cubo atravessa a superfície da garra e cai".
  Correção (2026-10-16): endurecimento dos parâmetros de contato — `harden_mesh_contacts` endurece após a compilação o `solref` de todos os corpos de colisão de malha
  para o mesmo valor usado nas faces dentadas do menagerie (0,01 s), com o mesmo tratamento para o contato do cubo. Correção pura de fidelidade física, sem adicionar geometria.
- **O robô simulado foi migrado para o modelo SO-ARM100 do mujoco_menagerie** (2026-10-16): o MJCF do zip do tutorial original era uma peça de demonstração cinemática e a garra não conseguia agarrar;
  o modelo do menagerie segue o CAD do robô real — a garra tem faces de colisão dentadas dedicadas e parâmetros de contato rígidos,
  e nas quatro posições dos dentes (rasa→profunda) ele consegue, na prática, parar, agarrar e levantar o cubo de 34 mm. Pontos da migração: o modelo está vendored em
  `assets/menagerie_so_arm100/` (Apache-2.0, incluindo LICENSE); o mapeamento de juntas e os sinais das unidades estão em `MODEL_JOINT`
  (verificação junta a junta por medição do movimento no referencial global contra o modelo antigo; o sinal de wrist_roll aguarda revisão por teleoperação no hardware real); a Base do modelo foi girada +90° em torno de Z para a
  frente de trabalho apontar para +x; o suporte foi remontado na lateral do Fixed_Jaw (servo nº 6) (primeiro por busca analítica de posicionamento; finalizado em 2026-10-16 pelo usuário, comparando fotos do robô real,
  com ajuste manual via `adjust_mount.py --model menagerie`: `[0.1, -0.7, 24.7]mm`, `RPY [0.34, -27.20, 89.51]°`). O modelo e as ferramentas do tutorial antigo foram mantidos intactos, disponíveis para comparação a qualquer momento.
- **Por que usar ambiente de projeto uv em vez de conda**: o `.venv` fica no mesmo diretório do projeto, tem versões travadas por `uv.lock` e é recuperado ao excluir o diretório,
  totalmente isolado dos ambientes conda da máquina; o `uv run` nunca instala nada no conda ativado. O ambiente conda `lerobot` desta máquina
  aponta para **outra cópia do repositório** (`lerobot-main`); os dois não se interferem.
- **Por que todos os plugins ficam em `examples/so101_mujoco/`**: integração pelo mecanismo oficial de registro (`register_subclass`),
  **zero modificação no código-fonte do lerobot**; para atualizar o upstream basta sincronizar novamente.
