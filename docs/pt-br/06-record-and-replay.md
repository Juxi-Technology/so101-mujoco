# 06 · Gravação e reprodução de dados

## Modelo de comando de gravação

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

## Pontos importantes dos parâmetros (fáceis de errar)

| Parâmetro | Descrição |
| --- | --- |
| `--dataset.root` | **root é o próprio diretório do conjunto de dados** (não é diretório pai + concatenação de repo_id); use um novo diretório a cada gravação |
| `--dataset.repo_id` | Na gravação local é apenas um identificador; só será necessário um `用户名/名字` real no futuro, ao enviar ao Hub |
| `--dataset.no_stamp=true` | Não adiciona sufixo de timestamp; diretório/nome estáveis; para regravar com o mesmo nome, é preciso excluir o diretório antigo antes |
| `--dataset.episode_time_s` | **Limite superior** por episódio (segurança); na operação normal, pressione `→` para encerrar antes |
| `--dataset.reset_time_s` | Tempo de reposicionamento não gravado entre episódios; durante ele o braço líder continua acionando o braço seguidor em tempo real. **Na gravação em simulação, os cubos teleportam automaticamente de volta à posição inicial ao entrar nessa fase** (veja abaixo) |
| `--dataset.video` | Ative somente quando precisar de dados de câmera (conjuntos de dados visuais exigem true; o fallback pyav foi validado como funcional) |
| `--dataset.rgb_encoder.vcodec` | Codificador de vídeo. **Nesta máquina, a gravação com duas câmeras usa `h264`**: o `record.py` já injeta isso por padrão (o padrão upstream libsvtav1 falha na alocação de memória ao abrir duas codificações simultâneas e derruba a sessão inteira — veja [07](07-troubleshooting.md)); se você passar explicitamente, nada é injetado |
| `--dataset.encoder_threads` | Número de threads de codificação. **O `record.py` injeta 2 por padrão**: o padrão consome todos os núcleos e deixa a imagem da simulação visivelmente travada durante o salvamento (veja [07](07-troubleshooting.md)); limitando cada codificação a 2 threads, a simulação continua fluida ao salvar; se você passar explicitamente, nada é injetado |
| `--dataset.push_to_hub` | Nesta máquina, a conexão direta com o HF exige proxy; mantenha false e envie manualmente depois de gravar |

## Teclas de controle de episódios (globais, válidas durante toda a gravação)

| Tecla | Função |
| --- | --- |
| `→` ou `n` | Encerra o episódio atual (**salva**) |
| `←` ou `r` | Descarta o episódio atual e **regrava no mesmo lugar** (use quando um episódio não ficou bom; não precisa reiniciar a sessão) |
| `q` | Encerra a sessão inteira e salva o conjunto de dados (**recomendado**) |
| `Esc` | Igual a `q` (também desconecta a teleoperação por teclado; a saída limpa já foi validada, mas prefira `q`) |

**Recomendação de operação**: antes de iniciar a gravação, deixe o braço líder próximo da pose central (para evitar que o trecho de convergência em que o braço simulado/real "dispara" no primeiro instante seja gravado);
após iniciar, fique um segundo parado antes de começar os movimentos.

## Reset automático de cena na gravação em simulação

Na gravação com robô real, a fase "Reset the environment" exige que você coloque os cubos de volta manualmente. Na simulação, o iniciador de gravação (`record.py`)
**teleporta automaticamente os três cubos de volta à posição inicial de origem** no início dessa fase (zerando também a velocidade); assim, após encerrar cada episódio com `→`,
basta mover o braço líder de volta à pose inicial, e os cubos retornam sozinhos; o próximo episódio começa a partir da cena inicial fixa.
O braço seguidor real não tem esse comportamento (posicionamento manual, como de costume); `teleoperate.py`/`replay.py` também não se envolvem nisso.

## Inspeção após a gravação

```bash
uv run --frozen python examples/so101_mujoco/inspect_dataset.py \
    --repo-id local/so101_sim_vision \
    --root examples/so101_mujoco/outputs/datasets/so101_sim_vision
```

Saída: número de quadros, duração, amplitude das ações das seis juntas e erro de rastreamento de cada episódio:

- **Episódios com action span = 0** são gravações vazias (ninguém se moveu); basta excluir e regravar;
- **O |action−obs| grande no início** é o trecho de convergência (normal); no meio/fim, normalmente <10 unidades.

## Gravar dados "com imagem" na simulação (câmera de punho)

O robô simulado permite gravar a câmera de punho da cena (`sim_cam`) como observação de imagem no conjunto de dados:

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

Pontos principais: `--robot.image_camera=sim_cam` (nome da câmera) + `--dataset.video=true` (a imagem passa pela codificação de vídeo; o fallback pyav foi validado como funcional).
As características do conjunto de dados passarão a incluir `observation.images.wrist` (480×640×3). Resolução e taxa de quadros podem ser ajustadas com
`--robot.image_width/--robot.image_height/--robot.image_fps`.
Com a janela aberta (`onscreen=true`, padrão), além da janela da visão principal, **é aberta uma janela de pré-visualização em tempo real para cada câmera**
(punho / superior, com rótulo no canto superior esquerdo), permitindo ver durante a gravação se os dois fluxos estão normais; se não precisar, adicione
`--robot.preview_cameras=false`. As janelas de pré-visualização atualizam por padrão a **15 Hz** (`--robot.preview_fps` ajustável) —
são exibição de estado e não precisam acompanhar os 50 Hz da janela principal, o que reduz bastante a carga de renderização com 3 janelas na mesma tela.

**Cena e câmera superior (a partir de 2026-10-16)**: a cena de simulação já traz uma área de trabalho — placa de base, cubos de três cores (34 mm), caixa de armazenamento (veja `so101_assets.add_workspace`,
layout ajustável renderizando com `preview_workspace.py`); há também uma câmera superior fixa `top_cam` (topo da imagem = direção que se afasta do braço).
Adicione `--robot.top_camera=top_cam` para gravar a visão superior como `observation.images.top` (duas câmeras simultâneas); se quiser apenas a câmera de punho, remova esse parâmetro.
A codificação de vídeo ao final de cada episódio processa os dois fluxos ao mesmo tempo, então uma espera um pouco maior é normal.

## Reprodução

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

> A entrada oficial `lerobot-replay` não carrega os plugins deste projeto; usá-la diretamente reporta `invalid choice: 'so101_mujoco'` —
> por isso use sempre o iniciador `replay.py`.

## Formato e local do conjunto de dados

O conjunto de dados é LeRobotDataset v3: `action` e `observation.state` são ambos vetores de 6 dimensões
(`shoulder_pan.pos … gripper.pos`), iguais aos conjuntos de dados reais oficiais, podendo ser misturados diretamente no treinamento.

```
examples/so101_mujoco/outputs/datasets/
└── juxi_teleop_run1/   真机键盘遥操（1 回合 / 2430 帧 / 81s）✅ 保留的真机数据

> 2026-10-16 清理：旧的仿真录制（`sim_run2`、`sim_vision_demo`、`sim_vision_run1/2/3`）
> 已全部删除。**正式数据集 `so101_sim_vision`（双相机 / 5 回合 / 10610 帧 / 353.8s / h264）
> 已于当晚录成 ✅**；每回合单机视频导出在 `outputs/videos/so101_sim_vision/`，
> 双相机预览拼图在 `outputs/renders/sim_vision_epN_dual.png`。
```

## Registro de testes desta sessão (2026-10-15)

| Sessão | Conteúdo | Resultado |
| --- | --- | --- |
| Real run1 | Teleoperação por teclado gravando o robô real | 1 episódio de 81 s; amplitude das seis juntas 75~140 unidades; estável a 30 Hz |
| Reprodução real | Reprodução do mesmo episódio | 2430 quadros reproduzidos integralmente, sem anormalidades |
| Simulação run2 | Teleoperação com braço líder gravando a simulação | 5 episódios em 157 s; erro de rastreamento <12 unidades nos ep1~4 |
| Reprodução sim ep1 | Reencenação na janela | Trajetória consistente com a operação (confirmado) |

## Testes adicionais (2026-10-16)

| Sessão | Conteúdo | Resultado |
| --- | --- | --- |
| Novo braço líder (COM124) | Recalibração (braço/servos novos) | ✅ calibração bem-sucedida; a compensação de zero do `so101_leader_trim` se adaptou automaticamente à nova calibração |
| Visual run1 | Teleoperação com braço líder gravando a simulação (com imagem) | 2 episódios / 3177 quadros / 106 s @ 29.97 Hz; erro de rastreamento ≤2 unidades o tempo todo (apenas 0,5 s de convergência no primeiro quadro); vídeo `observation.images.wrist` gravado no conjunto de dados e validado por decodificação ✅ |
| Visual run2 | Continuação da gravação com duas câmeras (`--resume`) | ep0 (2776 quadros / 92,6 s) íntegro; ao salvar o ep1, o OOM do codificador libsvtav1 derrubou a sessão inteira → codificador trocado para h264 (injetado por padrão no `record.py`) e testado ponta a ponta com sucesso (2 episódios × codificação dupla); resíduos limpos, regravação oficial passou para o run3 |
| Visual run3 | Gravação oficial com duas câmeras (h264) | 1ª sessão: ep0 (185,2 s / 5554 quadros) + ep1 (72,8 s / 2186 quadros) gravados íntegros, inspeção aprovada; durante a pausa de codificação entre sessões, pressionar `→` repetidamente disparou um crash de episódio vazio (mecanismo e proteção em [07](07-troubleshooting.md)) → continuação da sessão para gravar os episódios restantes (plano de 5 episódios) |
| Primeira gravação oficial (so101_sim_vision) | Duas câmeras (h264 + 2 threads + pré-visualização a 15 Hz) | Falha de alocação de memória do codificador ao salvar o ep0 (82,3 s / 2469 quadros), derrubando a sessão inteira (commit do sistema quase cheio, veja [07](07-troubleshooting.md)) → adicionados **nova tentativa automática em caso de falha de codificação** e **silenciamento do console** (ambos validados, 26 itens de smoke test aprovados); regravação oficial aguardando o reinício da máquina |
| Gravação oficial (so101_sim_vision) ✅ | Teleoperação com braço líder e duas câmeras, 5 episódios | **5/5 episódios gravados**: 61,5 / 53,4 / 101,1 / 62,4 / 75,4 s, total de 10610 quadros @29.97 Hz, 0 ticks acima do orçamento, zero crashes; seis eixos + garra com ações válidas o tempo todo; verificação por decodificação dos dois fluxos de vídeo aprovada |
