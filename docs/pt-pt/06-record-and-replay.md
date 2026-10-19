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

## Pontos essenciais dos parâmetros (armadilhas comuns)

| Parâmetro | Descrição |
| --- | --- |
| `--dataset.root` | **O root é o próprio diretório do conjunto de dados** (não é um diretório pai concatenado com o repo_id); use um novo diretório em cada gravação |
| `--dataset.repo_id` | Numa gravação local é apenas um identificador; só é necessário um `utilizador/nome` real quando se publicar no Hub |
| `--dataset.no_stamp=true` | Sem sufixo de data/hora, diretório/nome estáveis; para regravar com o mesmo nome, elimine primeiro o diretório antigo |
| `--dataset.episode_time_s` | **Limite máximo** de um episódio (segurança); numa operação normal, termine antes com `→` |
| `--dataset.reset_time_s` | Tempo de reposição entre episódios, não gravado; durante este período o braço líder continua a comandar o seguidor em tempo real. **Ao gravar em simulação, os cubos são teletransportados automaticamente para a posição inicial ao entrar nesta fase** (ver abaixo) |
| `--dataset.video` | Ativar apenas quando forem necessários dados de câmara (obrigatório em conjuntos de dados visuais; o fallback pyav foi validado) |
| `--dataset.rgb_encoder.vcodec` | Codificador de vídeo. **Nesta máquina, use `h264` para gravação com duas câmaras**: o `record.py` já o injeta por omissão (o padrão upstream libsvtav1 falha a alocação de memória quando as duas codificações abrem em simultâneo e a sessão inteira rebenta — ver [07](07-troubleshooting.md)); se for passado explicitamente, deixa de ser injetado |
| `--dataset.encoder_threads` | Número de threads de codificação. **O `record.py` injeta 2 por omissão**: usar todos os núcleos torna a imagem da simulação visivelmente lenta durante a fase de guardar (ver [07](07-troubleshooting.md)); limitar a 2 threads por codificação mantém a simulação fluida ao guardar; se for passado explicitamente, deixa de ser injetado |
| `--dataset.push_to_hub` | A ligação direta ao HF nesta máquina requer proxy; mantenha false e envie manualmente após a gravação |

## Teclas de controlo de episódios (globais, ativas durante toda a gravação)

| Tecla | Ação |
| --- | --- |
| `→` ou `n` | Terminar o episódio atual (**guardar**) |
| `←` ou `r` | Descartar o episódio atual e **regravar no local** (use quando um episódio não ficou bom, sem reiniciar a sessão) |
| `q` | Terminar a sessão e guardar o conjunto de dados (**recomendado**) |
| `Esc` | Igual a `q` (desliga também a teleoperação por teclado; a saída limpa foi validada, mas prefira `q`) |

**Recomendação de operação**: antes de iniciar a gravação, deixe o braço líder perto da pose neutra (para evitar que o segmento de convergência em que o braço simulado/real «salta»
no primeiro instante fique gravado); após iniciar, fique imóvel durante um segundo antes de começar a mover.

## Reposição automática do cenário na gravação em simulação

Na gravação com o robô real, a fase «Reset the environment» exige que coloque manualmente os cubos na posição original. Na simulação, o lançador de gravação (`record.py`)
**teletransporta automaticamente os três cubos para a posição de origem** (zerando também as velocidades) no início dessa fase; por isso, depois de terminar cada episódio com `→`,
basta mover o braço líder de volta à pose inicial — os cubos regressam automaticamente e o episódio seguinte começa num cenário inicial fixo.
O braço seguidor real não tem este comportamento (colocação manual, como habitualmente); `teleoperate.py`/`replay.py` também não estão envolvidos.

## Inspeção após a gravação

```bash
uv run --frozen python examples/so101_mujoco/inspect_dataset.py \
    --repo-id local/so101_sim_vision \
    --root examples/so101_mujoco/outputs/datasets/so101_sim_vision
```

Apresenta, por episódio, o número de frames, a duração, a amplitude de movimento das seis articulações e o erro de seguimento:

- **Episódios com action span = 0** são gravações vazias (ninguém se moveu); elimine e regrave;
- **Um |action−obs| elevado no início** é o segmento de convergência (normal); a meio e no fim é geralmente <10 unidades.

## Gravar dados «com imagem» em simulação (câmara wrist)

O robô simulado permite gravar a câmara de punho do cenário (`sim_cam`) no conjunto de dados como observação de imagem:

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

Pontos essenciais: `--robot.image_camera=sim_cam` (nome da câmara) + `--dataset.video=true` (as imagens passam pela codificação de vídeo; o fallback pyav foi validado).
As características do conjunto de dados passam a incluir `observation.images.wrist` (480×640×3). A resolução e a taxa de frames podem ser ajustadas com
`--robot.image_width/--robot.image_height/--robot.image_fps`.
Ao abrir a janela (`onscreen=true`, predefinição), além da janela da vista principal, é aberta **uma janela de pré-visualização em tempo real para cada câmara**
(punho / vista de cima, com etiqueta no canto superior esquerdo), permitindo ver imediatamente se as duas imagens estão corretas durante a gravação; se não precisar, acrescente
`--robot.preview_cameras=false`. As janelas de pré-visualização atualizam a **15Hz** por omissão (`--robot.preview_fps` ajustável) —
são apenas indicadores de estado e não precisam de acompanhar os 50Hz da janela principal, o que reduz muito a carga de renderização com 3 janelas no ecrã.

**Cenário e câmara de vista de cima (desde 2026-10-16)**: o cenário simulado inclui uma área de trabalho — base de apoio, cubos de três cores (34mm), caixa de arrumação (ver `so101_assets.add_workspace`,
a disposição pode ser ajustada renderizando com `preview_workspace.py`); há ainda uma câmara fixa de vista de cima `top_cam` (parte superior da imagem = direção oposta ao braço robótico).
Acrescentar `--robot.top_camera=top_cam` grava a vista de cima como `observation.images.top` (duas câmaras em simultâneo); se só quiser a câmara de punho, remova esse parâmetro.
A codificação de vídeo no fim de cada episódio processa as duas imagens ao mesmo tempo, pelo que um tempo de espera ligeiramente maior é normal.

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

> O ponto de entrada oficial `lerobot-replay` não carrega os plugins deste projeto; usá-lo diretamente dá `invalid choice: 'so101_mujoco'` —
> por isso use sempre o lançador `replay.py`.

## Formato e localização do conjunto de dados

O conjunto de dados é LeRobotDataset v3: `action` e `observation.state` são ambos vetores de 6 dimensões
(`shoulder_pan.pos … gripper.pos`), consistentes com os conjuntos de dados reais oficiais, podendo ser misturados diretamente no treino.

```
examples/so101_mujoco/outputs/datasets/
└── juxi_teleop_run1/   真机键盘遥操（1 回合 / 2430 帧 / 81s）✅ 保留的真机数据

> 2026-10-16 清理：旧的仿真录制（`sim_run2`、`sim_vision_demo`、`sim_vision_run1/2/3`）
> 已全部删除。**正式数据集 `so101_sim_vision`（双相机 / 5 回合 / 10610 帧 / 353.8s / h264）
> 已于当晚录成 ✅**；每回合单机视频导出在 `outputs/videos/so101_sim_vision/`，
> 双相机预览拼图在 `outputs/renders/sim_vision_epN_dual.png`。
```

## Registo das medições desta sessão (2026-10-15)

| Sessão | Conteúdo | Resultado |
| --- | --- | --- |
| Real run1 | Gravação no robô real com teleoperação por teclado | 1 episódio de 81s, amplitude das seis articulações 75~140 unidades, 30Hz estável |
| Reprodução real | Repetição do mesmo episódio | 2430 frames reproduzidos na íntegra, sem anomalias |
| Simulação run2 | Gravação em simulação com teleoperação pelo braço líder | 5 episódios em 157s, erro de seguimento dos ep1~4 <12 unidades |
| Reprodução simulação ep1 | Repetição na janela | Trajetória consistente com a operação (confirmado) |

## Medições adicionais (2026-10-16)

| Sessão | Conteúdo | Resultado |
| --- | --- | --- |
| Novo braço líder (COM124) | Recalibração (novo braço/novos servo-motores) | ✅ Calibração bem-sucedida; a compensação de zero do `so101_leader_trim` adaptou-se automaticamente à nova calibração |
| Visual run1 | Gravação em simulação com teleoperação pelo braço líder (com imagem) | 2 episódios / 3177 frames / 106s @ 29.97Hz; erro de seguimento ≤2 unidades durante todo o percurso (apenas 0,5s de convergência no primeiro frame); vídeo `observation.images.wrist` guardado no conjunto de dados e descodificado para verificação ✅ |
| Visual run2 | Gravação contínua com duas câmaras (`--resume`) | ep0 (2776 frames / 92,6s) sem perdas; ao guardar o ep1, o codificador libsvtav1 ficou sem memória (OOM) e a sessão inteira rebentou → codificador alterado para h264 (injetado por omissão no `record.py`) e testado ponto a ponto com sucesso (2 episódios × codificação dupla); resíduos eliminados, regravação oficial passou para o run3 |
| Visual run3 | Gravação oficial com duas câmaras (h264) | 1.ª sessão: ep0 (185,2s / 5554 frames) + ep1 (72,8s / 2186 frames) guardados corretamente e inspeção aprovada; premir `→` repetidamente durante a pausa de codificação entre sessões desencadeou um crash de episódio vazio (mecanismo e proteção em [07](07-troubleshooting.md)) → sessão retomada para gravar os episódios restantes (plano de 5 episódios) |
| Estreia da gravação oficial (so101_sim_vision) | Duas câmaras (h264 + 2 threads + pré-visualização a 15Hz) | Ao guardar o ep0 (82,3s / 2469 frames), falha de alocação de memória do codificador e a sessão inteira rebentou (commit do sistema quase esgotado, ver [07](07-troubleshooting.md)) → adicionadas **nova tentativa automática em caso de falha de codificação** e **silenciamento da consola** (ambos validados, 26 itens do smoke test aprovados); aguarda reinício da máquina para regravar oficialmente |
| Gravação oficial (so101_sim_vision) ✅ | Teleoperação pelo braço líder com duas câmaras, 5 episódios | **5/5 episódios guardados**: 61,5 / 53,4 / 101,1 / 62,4 / 75,4 s, num total de 10610 frames @29.97Hz, 0 ticks acima do orçamento, zero crashes; movimento válido dos seis eixos + pinça durante todo o percurso; descodificação e verificação dos dois vídeos aprovada |
