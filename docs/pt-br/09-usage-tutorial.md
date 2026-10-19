# 09 · Tutorial de uso completo (iniciar o braço → conjunto de dados → ver vídeos → treinar → implantar)

> Manual de operação de ponta a ponta: seguindo uma vez, você sai de "conectar o braço líder" até "a política treinada trabalhando sozinha na simulação".
> Pré-requisito: ambiente instalado conforme [01](01-environment.md), braço líder calibrado conforme [03](03-hardware-calibration.md)
> (nesta máquina, `juxi_leader` / COM124). Todas as armadilhas relacionadas à gravação estão concentradas em [07](07-troubleshooting.md).

## 0 · Preparação única

```bash
# 本机所有 uv 命令都要先设（跨盘缓存特例，见 07）
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
```

Conecte o braço líder e confirme a porta serial (**o número pode mudar a cada conexão**):

```bash
uv run --frozen python -c "from serial.tools import list_ports; print([p.device for p in list_ports.comports()])"
```

Deixe espaço na mesa: a gravação abrirá **3 janelas** (visão principal + `wrist camera - live` + `top camera - live`).

## 1 · Aquecimento de teleoperação (recomendado)

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/teleoperate.py \
    --robot.type=so101_mujoco \
    --teleop.type=so101_leader_trim --teleop.port=COM124 --teleop.id=juxi_leader \
    --teleop.use_degrees=false
```

Mova o braço líder e confirme que o braço simulado acompanha; antes de sair (Ctrl-C), deixe o braço líder **perto da pose central**, para não haver um grande trecho de convergência no início da gravação.

## 2 · Gravação (comando principal)

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/record.py \
    --robot.image_camera=sim_cam --robot.top_camera=top_cam \
    --teleop.type=so101_leader_trim --teleop.port=COM124 --teleop.id=juxi_leader \
    --teleop.use_degrees=false \
    --dataset.repo_id=local/so101_sim_vision \
    --dataset.root=examples/so101_mujoco/outputs/datasets/so101_sim_vision \
    --dataset.num_episodes=5 --dataset.episode_time_s=600 --dataset.reset_time_s=10 \
    --dataset.single_task="put the cube in the box" \
    --dataset.video=true --dataset.push_to_hub=false --play_sounds=false --dataset.no_stamp=true
```

Pontos principais (demais parâmetros na tabela de [06](06-record-and-replay.md)):

| Item | Descrição |
| --- | --- |
| `--dataset.root` | **root é o próprio diretório do conjunto de dados**; troque para um novo diretório a cada gravação (se existir um diretório com o mesmo nome, a inicialização é recusada) |
| Valores padrão injetados automaticamente | Codificação de vídeo `h264`, threads de codificação `2` — o `record.py` imprime duas linhas de dica ao iniciar; passar explicitamente `--dataset.rgb_encoder.vcodec=...` / `--dataset.encoder_threads=...` sobrescreve (motivo em 07) |
| Janelas de pré-visualização | Abertas por padrão (15 Hz; `--robot.preview_cameras=false` desativa; `--robot.preview_fps` ajusta) |
| `--dataset.video=true` | Imagens das duas câmeras gravadas (`observation.images.wrist / top`); se quiser apenas a câmera de punho, remova `top_camera` |

## 3 · Operação durante a gravação

| Tecla | Função |
| --- | --- |
| `→` ou `n` | Encerra o episódio atual e salva |
| `←` ou `r` | Descarta o episódio atual e regrava no mesmo lugar |
| `q` | Encerra a sessão e salva o conjunto de dados |

- Após o fim do episódio, **os cubos voltam sozinhos à posição**; basta puxar o braço líder de volta à pose inicial; comece os movimentos do próximo episódio quando aparecer `Recording episode N`.
- Na fase de salvamento (dezenas de segundos), o console imprime `[record.py] reset done; saving the episode + encoding videos now` —
  durante esse período **as teclas são ignoradas com segurança** (pressionar por engano não estraga nenhum episódio); espere aparecer a próxima linha `Recording episode` para operar.
- Falhas de codificação têm **nova tentativa automática como rede de segurança** (imprime `video encode failed ... retrying once` e tenta de novo após 3 segundos); episódios já salvos nunca são perdidos.

## 4 · Inspeção

```bash
uv run --frozen python examples/so101_mujoco/inspect_dataset.py \
    --repo-id local/so101_sim_vision \
    --root examples/so101_mujoco/outputs/datasets/so101_sim_vision
```

Como ler a saída:

- **Episódios com action span todo 0 (ou garra 0)** são gravações vazias/inválidas; exclua e regrave;
- **O `max |act-obs|` grande no início de cada episódio** é o trecho de convergência, normal; no meio/fim deve ficar abaixo de ~10 unidades.

## 5 · Ver vídeos

```bash
uv run --frozen python examples/so101_mujoco/export_videos.py \
    --root examples/so101_mujoco/outputs/datasets/so101_sim_vision
```

Artefatos:

- `examples/so101_mujoco/outputs/videos/<数据集名>/epN_top.mp4`, `epN_wrist.mp4` — **um vídeo por episódio por câmera, com duplo clique para reproduzir**;
- `examples/so101_mujoco/outputs/renders/<数据集名>_epN_dual.png` — uma montagem por episódio (linha de cima: visão superior; linha de baixo: punho; 6 quadros amostrados uniformemente), para inspeção visual rápida (`--no-strips` pode ser usado para pular).

O conjunto de dados também contém os vídeos empacotados originais (vários episódios concatenados em ordem em um mesmo arquivo):
`outputs/datasets/<数据集名>/videos/observation.images.{top,wrist}/chunk-000/file-000.mp4`.

## 6 · Reprodução (opcional)

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/replay.py \
    --dataset.repo_id=local/so101_sim_vision \
    --dataset.root=examples/so101_mujoco/outputs/datasets/so101_sim_vision --dataset.episode=0
```

## 7 · Treinamento

```bash
uv run --frozen lerobot-train \
    --policy.type=act \
    --policy.push_to_hub=false \
    --dataset.repo_id=local/so101_sim_vision \
    --dataset.root=examples/so101_mujoco/outputs/datasets/so101_sim_vision \
    --output_dir=examples/so101_mujoco/outputs/train/act_so101_sim_vision \
    --steps=100000 --batch_size=8 --save_freq=20000 --log_freq=200 \
    --num_workers=4 --wandb.enable=false --policy.device=cpu
```

| Item | Descrição |
| --- | --- |
| `--policy.type` | Tipo de política; **comece com `act`** (o mais adequado a esta escala de dados/tarefa); `ls src/lerobot/policies/` mostra outras opções (diffusion / smolvla / pi0 etc.) |
| `--policy.push_to_hub=false` | **Obrigatório** — o padrão tenta enviar ao HuggingFace Hub e, sem `repo_id` configurado, sai com erro; para enviar, mude para `--policy.repo_id=你的用户名/模型名` (requer `hf auth login` antes) |
| `--policy.device=cpu` | Sem GPU dedicada nesta máquina, use `cpu`; em máquinas com placa NVIDIA, remova o parâmetro (usa cuda automaticamente) |
| Artefatos | `output_dir/checkpoints/<步数>/` e `checkpoints/last/pretrained_model/` — a implantação aponta para o segundo; o `train_config.json` para retomar o treinamento também fica lá |
| Retomar treinamento | Após interrupção, adicione ao comando original: `--resume=true --config_path=<output_dir>/checkpoints/last/pretrained_model/train_config.json` |

**Expectativa de velocidade nesta máquina**: apenas CPU, cerca de **2 segundos/passo** (batch 2, duas câmeras em 480p; medido: smoke de 12 passos com loss caindo de 70 para 22, direção normal).
Portanto, esta máquina serve para validar a cadeia com poucos passos — o `outputs/train/smoke_act` que acompanha o tutorial é justamente o produto de 12 passos;
**o treinamento oficial (ACT normalmente na ordem de 100 mil passos) deve ser feito em uma máquina com GPU; os comandos são exatamente os mesmos.**

> Dica de dependência: o treinamento precisa do extra `training` (accelerate etc.). Se aparecer `accelerate is required but not installed`,
> adicione `--extra training` conforme o comando de instalação do [01](01-environment.md) e tente de novo.

## 8 · Implantação (fazer a política trabalhar sozinha na simulação)

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/rollout.py \
    --policy.path=examples/so101_mujoco/outputs/train/act_so101_sim_vision/checkpoints/last/pretrained_model \
    --strategy.type=base \
    --robot.image_camera=sim_cam --robot.top_camera=top_cam \
    --task="put the cube in the box" --duration=30
```

| Item | Descrição |
| --- | --- |
| Parâmetros de câmera | `--robot.image_camera/--robot.top_camera` **devem ser iguais aos usados na gravação do conjunto de dados** (sim_cam + top_cam), caso contrário a política não recebe as imagens com que foi treinada |
| `--task` | Igual ao `--dataset.single_task` usado na gravação |
| `--duration` | Encerra automaticamente após quantos segundos (antes de encerrar, envia o braço de volta à pose inicial e desconecta); `Ctrl-C` também interrompe |
| Para testar a cadeia primeiro | Use o modelo de demonstração que acompanha o tutorial: `--policy.path=examples/so101_mujoco/outputs/train/smoke_act/checkpoints/last/pretrained_model` (treinamento de 12 passos, ações quase aleatórias, apenas valida a cadeia) |
| Implantação em CPU pura | A inferência da política tem picos ocasionais de 0,5 s e avisa `Control loop is running slower ... than the target FPS` — roda na simulação, mas com engasgos; em GPU não há esse problema (medido: smoke de 20 s roda do início ao fim e encerra normalmente) |
| Implantação no robô real | Troque `--robot.*` pelo robô real: `--robot.type=so101_follower --robot.port=COMxx --robot.id=juxi_so101 --robot.use_degrees=false` (atenção para deixar espaço na mesa) |
| Outros modos | `--strategy.type=sentry / highlight / dagger / episodic`: gravar enquanto executa / salvar com tecla em buffer circular / correção humana no loop / gravação por episódios; veja `lerobot-rollout --help` |

## Apêndice A · Trocar para ambiente conda (opcional)

Este repositório usa por padrão o **`.venv` do projeto gerenciado pelo uv** (veja [01](01-environment.md)), e os comandos de execução precisam do prefixo
`uv run --frozen --with mujoco`. Se você prefere conda, **substitua a etapa "criar ambiente" pelos três comandos abaixo** e depois
**remova o prefixo uv de todos os comandos** (`python examples/...` roda diretamente); o `UV_CACHE_DIR` também deixa de ser necessário
(é a particularidade do cache uv entre discos diferentes, sem relação com conda):

```bash
# 一次性：在仓库根目录建好环境（python 版本对齐 01 的 3.12）
conda create -n lerobot-sim python=3.12 -y
conda activate lerobot-sim
pip install -e .            # 安装本仓库 lerobot 及其依赖（含 torch，Windows 上 pip 默认就是 CPU 版）
pip install "mujoco==3.16"  # uv 路线用 --with mujoco 临时提供，conda 路线装成常驻依赖
```

Depois disso, por exemplo, a gravação passa a ser:

```bash
python examples/so101_mujoco/record.py --robot.image_camera=sim_cam ...
```

Dois pontos de atenção:

1. **Alinhamento de versões**: o `pip install -e .` resolve as versões por conta própria e pode não ser idêntico ao `uv.lock`;
   para uma combinação exatamente igual ao ambiente medido atual, instale no ambiente conda com uv seguindo o arquivo de lock:

   ```bash
   uv pip sync uv.lock --python "$(conda run -n lerobot-sim python -c 'import sys; print(sys.executable)')"
   pip install "mujoco==3.16"
   ```

2. O cache de calibração do braço líder fica em `~/.cache/huggingface/lerobot/calibration/`, independente do ambiente usado; ao migrar de ambiente, não é preciso recalibrar.

## Apêndice B · Consulta rápida de armadilhas comuns

| Sintoma | Em uma frase |
| --- | --- |
| A porta serial não abre | Liste as portas primeiro; o número pode ter mudado (passo 0) |
| O console fica quieto por dezenas de segundos ao salvar | Está codificando, é normal; ao ver o aviso `saving the episode...`, não pressione teclas |
| A imagem trava ocasionalmente durante a gravação | Disputa de recursos de codificação na janela de salvamento; o loop de controle em si não é afetado (use os números de cadence), detalhes em 07 |
| Deu crash uma vez, ainda dá para salvar? | Episódios já salvos nunca são perdidos; continue com `record.py --resume=true ... --dataset.num_episodes=N` |
| `lerobot-train` reporta `'repo_id' argument missing` | O padrão tenta enviar ao Hub: adicione `--policy.push_to_hub=false` (para enviar, configure `--policy.repo_id` e faça `hf auth login` antes) |
| Na implantação, a política não se move ou se move aleatoriamente | Verifique primeiro se `--robot.image_camera/--robot.top_camera` e `--task` são iguais aos da gravação; depois veja se o treinamento teve poucos passos |

Todas as armadilhas e soluções (incluindo memória apertada, OOM de codificação, episódios vazios etc.) em [07 · Perguntas frequentes](07-troubleshooting.md).
