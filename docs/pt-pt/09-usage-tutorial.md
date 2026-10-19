# 09 · Tutorial de utilização completo (braço → conjunto de dados → ver vídeos → treino → implementação)

> Manual de operação de ponta a ponta: siga-o uma vez e vai de «ligar o braço líder» até «a política treinada a trabalhar sozinha na simulação».
> Pré-requisitos: ambiente instalado segundo [01](01-environment.md), braço líder calibrado segundo [03](03-hardware-calibration.md)
> (nesta máquina, `juxi_leader` / COM124). Todos os obstáculos relacionados com a gravação estão concentrados em [07](07-troubleshooting.md).

## 0 · Preparação única

```bash
# 本机所有 uv 命令都要先设（跨盘缓存特例，见 07）
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
```

Ligue o braço líder e confirme a porta série (**o número pode mudar a cada ligação/desligação**):

```bash
uv run --frozen python -c "from serial.tools import list_ports; print([p.device for p in list_ports.comports()])"
```

Deixe espaço na secretária: a gravação abre **3 janelas** (vista principal + `wrist camera - live` + `top camera - live`).

## 1 · Aquecimento com teleoperação (recomendado)

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/teleoperate.py \
    --robot.type=so101_mujoco \
    --teleop.type=so101_leader_trim --teleop.port=COM124 --teleop.id=juxi_leader \
    --teleop.use_degrees=false
```

Mova o braço líder e confirme que o braço simulado acompanha; antes de sair (Ctrl-C), pare o braço líder **perto da pose neutra**, para não haver um grande segmento de convergência no instante em que a gravação começa.

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

Pontos essenciais (para os restantes parâmetros, ver a tabela de parâmetros em [06](06-record-and-replay.md)):

| Item | Descrição |
| --- | --- |
| `--dataset.root` | **O root é o próprio diretório do conjunto de dados**; use um novo diretório em cada sessão (recusa arrancar se o diretório com o mesmo nome existir) |
| Valores predefinidos injetados automaticamente | Codificação de vídeo `h264`, threads de codificação `2` — o `record.py` imprime duas linhas de aviso ao arrancar; passar explicitamente `--dataset.rgb_encoder.vcodec=...` / `--dataset.encoder_threads=...` sobrepõe-se (motivos em 07) |
| Janelas de pré-visualização | Abertas por omissão (15Hz; `--robot.preview_cameras=false` para desativar; `--robot.preview_fps` ajustável) |
| `--dataset.video=true` | Imagens das duas câmaras guardadas no conjunto de dados (`observation.images.wrist / top`); se só quiser a câmara de punho, remova `top_camera` |

## 3 · Operação durante a gravação

| Tecla | Ação |
| --- | --- |
| `→` ou `n` | Terminar o episódio atual e guardar |
| `←` ou `r` | Descartar o episódio atual e regravar no local |
| `q` | Terminar a sessão e guardar o conjunto de dados |

- Depois de terminar o episódio, **os cubos regressam automaticamente ao lugar**; só precisa de levar o braço líder de volta à pose inicial; comece os movimentos do episódio seguinte quando vir `Recording episode N`.
- Na fase de guardar (dezenas de segundos), a consola imprime `[record.py] reset done; saving the episode + encoding videos now` —
  durante este período **as teclas são ignoradas em segurança** (premir por engano não estraga nenhum episódio); espere pela linha seguinte `Recording episode` para voltar a operar.
- Em caso de falha de codificação há **nova tentativa automática como salvaguarda** (imprime `video encode failed ... retrying once` e tenta novamente após 3 segundos); os episódios já guardados nunca se perdem.

## 4 · Inspeção

```bash
uv run --frozen python examples/so101_mujoco/inspect_dataset.py \
    --repo-id local/so101_sim_vision \
    --root examples/so101_mujoco/outputs/datasets/so101_sim_vision
```

Como interpretar a saída:

- **Episódios com action span todo 0 (ou pinça a 0)** são gravações vazias/inválidas; elimine e regrave;
- **Um `max |act-obs|` elevado no início de cada episódio** é o segmento de convergência, normal; a meio e no fim deve ser inferior a ~10 unidades.

## 5 · Ver os vídeos

```bash
uv run --frozen python examples/so101_mujoco/export_videos.py \
    --root examples/so101_mujoco/outputs/datasets/so101_sim_vision
```

Resultados:

- `examples/so101_mujoco/outputs/videos/<数据集名>/epN_top.mp4`、`epN_wrist.mp4` — **um vídeo reproduzível com duplo clique por episódio e por câmara**;
- `examples/so101_mujoco/outputs/renders/<数据集名>_epN_dual.png` — uma imagem composta por episódio (linha de cima: vista de cima; linha de baixo: punho; 6 frames amostrados uniformemente), para inspeção visual rápida (`--no-strips` permite ignorar).

O conjunto de dados também contém os vídeos originais empacotados (vários episódios concatenados por ordem no mesmo ficheiro):
`outputs/datasets/<数据集名>/videos/observation.images.{top,wrist}/chunk-000/file-000.mp4`.

## 6 · Reprodução (opcional)

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/replay.py \
    --dataset.repo_id=local/so101_sim_vision \
    --dataset.root=examples/so101_mujoco/outputs/datasets/so101_sim_vision --dataset.episode=0
```

## 7 · Treino

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

| Ponto essencial | Descrição |
| --- | --- |
| `--policy.type` | Tipo de política, **começar por `act`** (o mais adequado a esta escala de dados/tarefa); `ls src/lerobot/policies/` mostra outras opções (diffusion / smolvla / pi0, etc.) |
| `--policy.push_to_hub=false` | **Obrigatório** — por omissão tenta publicar no HuggingFace Hub e, sem `repo_id` configurado, termina com erro; para publicar, use `--policy.repo_id=o_seu_utilizador/nome_do_modelo` (requer `hf auth login` primeiro) |
| `--policy.device=cpu` | Sem GPU dedicada nesta máquina, use `cpu`; numa máquina com placa NVIDIA, remova o parâmetro (usa cuda automaticamente) |
| Artefactos | `output_dir/checkpoints/<步数>/` e `checkpoints/last/pretrained_model/` — a implementação aponta para o segundo; o `train_config.json` para retomar o treino também está lá |
| Retoma | Após interrupção, acrescente ao comando original: `--resume=true --config_path=<output_dir>/checkpoints/last/pretrained_model/train_config.json` |

**Velocidade esperada nesta máquina**: só CPU, cerca de **2 segundos/passo** (batch 2, duas câmaras a 480p; no teste de fumo de 12 passos, a loss desceu de 70 para 22, direção normal).
Por isso esta máquina serve para validar a cadeia com poucos passos — o `outputs/train/smoke_act` incluído no tutorial é o produto de 12 passos;
**para o treino oficial (a ordem habitual de 100 mil passos para ACT) recomenda-se uma máquina com GPU; o comando é exatamente o mesmo.**

> Nota sobre dependências: o treino requer o extra `training` (accelerate, etc.). Se aparecer `accelerate is required but not installed`,
> acrescente `--extra training` ao comando de instalação de [01](01-environment.md) e tente novamente.

## 8 · Implementação (pôr a política a trabalhar sozinha na simulação)

```bash
uv run --frozen --with mujoco python examples/so101_mujoco/rollout.py \
    --policy.path=examples/so101_mujoco/outputs/train/act_so101_sim_vision/checkpoints/last/pretrained_model \
    --strategy.type=base \
    --robot.image_camera=sim_cam --robot.top_camera=top_cam \
    --task="put the cube in the box" --duration=30
```

| Ponto essencial | Descrição |
| --- | --- |
| Parâmetros das câmaras | `--robot.image_camera/--robot.top_camera` **têm de coincidir com os usados na gravação do conjunto de dados** (sim_cam + top_cam), caso contrário a política não recebe as imagens com que foi treinada |
| `--task` | Igual ao `--dataset.single_task` usado na gravação |
| `--duration` | Número de segundos após os quais a sessão termina automaticamente (antes de terminar, o braço robótico é devolvido à pose inicial e depois desligado); também pode parar a meio com `Ctrl-C` |
| Para testar primeiro a cadeia | Use o modelo de demonstração incluído no tutorial: `--policy.path=examples/so101_mujoco/outputs/train/smoke_act/checkpoints/last/pretrained_model` (treino de 12 passos; os movimentos parecem aleatórios, serve apenas para validar a cadeia) |
| Implementação só em CPU | A inferência da política tem picos ocasionais de 0,5s e avisa `Control loop is running slower ... than the target FPS` — funciona na simulação, mas aos soluços; numa GPU não há este problema (teste de fumo de 20s correu de ponta a ponta e terminou normalmente) |
| Implementação no robô real | Substitua `--robot.*` pelo robô real: `--robot.type=so101_follower --robot.port=COMxx --robot.id=juxi_so101 --robot.use_degrees=false` (deixe espaço na secretária) |
| Outros modos | `--strategy.type=sentry / highlight / dagger / episodic`: gravar durante a execução / buffer circular com gravação por tecla / correção humana no ciclo / gravação por episódios, ver `lerobot-rollout --help` |

## Anexo A · Mudar para um ambiente conda (opcional)

Este repositório usa por omissão uma **`.venv` dentro do projeto gerida pelo uv** (ver [01](01-environment.md)); os comandos de execução levam
o prefixo `uv run --frozen --with mujoco`. Se preferir conda, **substitua o passo de «criar o ambiente» pelos três comandos abaixo**
e, a partir daí, **remova o prefixo uv de todos os comandos** (`python examples/...` diretamente), deixando de precisar de `UV_CACHE_DIR`
(é o caso especial da cache do uv que atravessa discos, sem relação com o conda):

```bash
# 一次性：在仓库根目录建好环境（python 版本对齐 01 的 3.12）
conda create -n lerobot-sim python=3.12 -y
conda activate lerobot-sim
pip install -e .            # 安装本仓库 lerobot 及其依赖（含 torch，Windows 上 pip 默认就是 CPU 版）
pip install "mujoco==3.16"  # uv 路线用 --with mujoco 临时提供，conda 路线装成常驻依赖
```

Depois, por exemplo, a gravação passa a ser:

```bash
python examples/so101_mujoco/record.py --robot.image_camera=sim_cam ...
```

Dois pontos a ter em conta:

1. **Alinhamento de versões**: o `pip install -e .` deixa o pip resolver as versões por conta própria, o que pode não coincidir exatamente com o `uv.lock`;
   para obter uma combinação idêntica ao ambiente atualmente testado, instale no ambiente conda com o uv segundo o ficheiro de lock:

   ```bash
   uv pip sync uv.lock --python "$(conda run -n lerobot-sim python -c 'import sys; print(sys.executable)')"
   pip install "mujoco==3.16"
   ```

2. A cache de calibração do braço líder está em `~/.cache/huggingface/lerobot/calibration/`, independentemente do ambiente usado; mudar de ambiente não exige recalibrar.

## Anexo B · Consulta rápida de obstáculos comuns

| Sintoma | Numa frase |
| --- | --- |
| A porta série não abre | Liste primeiro as portas; o número pode ter mudado (passo 0) |
| A consola fica silenciosa dezenas de segundos ao guardar | Está a codificar, é normal; quando vir o aviso `saving the episode...`, não prima teclas |
| A imagem engasga ocasionalmente durante a gravação | Competição por recursos de codificação na janela de guardar; o ciclo de controlo em si não é afetado (guie-se pelos números de cadence), ver detalhes em 07 |
| Rebentou uma vez, ainda dá para salvar? | Os episódios guardados nunca se perdem; `record.py --resume=true ... --dataset.num_episodes=N` retoma a gravação |
| `lerobot-train` dá `'repo_id' argument missing` | Por omissão tenta publicar no Hub: acrescente `--policy.push_to_hub=false` (para publicar, configure `--policy.repo_id` e faça `hf auth login` primeiro) |
| Na implementação, a política não se mexe ou mexe-se ao acaso | Confirme primeiro se `--robot.image_camera/--robot.top_camera` e `--task` coincidem com os da gravação; depois veja se só treinou poucos passos |

Todos os obstáculos e soluções (incluindo memória escassa, OOM na codificação, episódios vazios, etc.) em [07 · Problemas comuns](07-troubleshooting.md).
