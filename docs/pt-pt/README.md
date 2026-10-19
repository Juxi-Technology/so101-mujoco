# SO-ARM101 × MuJoCo — Tutorial do fluxo completo (índice)

> 🌐 Languages: [简体中文](../README.md) · [English](../en/README.md) · [Deutsch](../de/README.md) · [Español](../es/README.md) · [Français](../fr/README.md) · [Italiano](../it/README.md) · [日本語](../ja/README.md) · [한국어](../ko/README.md) · [Português (BR)](../pt-br/README.md) · **Português (PT)** · [繁體中文](../zh-hant/README.md)

> Este tutorial documenta e reproduz o **fluxo de trabalho completo de simulação + robô real** do SO-ARM101: desde a preparação do ambiente, verificação do modelo e calibração do robô real,
> até à teleoperação por teclado/braço líder, gravação e reprodução de dados. Todos os comandos foram testados numa sessão real + simulação em 2026-10-15.
>
> Público-alvo: utilizadores do kit Juxi SO-ARM101 e engenheiros internos. Não é necessário conhecimento prévio de MuJoCo ou LeRobot.

## Mapa do fluxo completo (duas vias, um conjunto comum de componentes)

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

| Capítulo | Conteúdo | O que vai obter |
| --- | --- | --- |
| [01 Preparação do ambiente](01-environment.md) | Ambiente uv, extras de dependências, notas para Windows | Um ambiente funcional |
| [02 Verificação do modelo de simulação](02-sim-model-verification.md) | Carregamento/comparação/renderização de três modelos MJCF | Confiança no modelo e no comportamento da simulação |
| [03 Ligação ao robô real e calibração](03-hardware-calibration.md) | Identificação da porta série, inspeção inicial só de leitura, calibração do seguidor/líder | Dois braços reconhecidos pelo software |
| [04 Teleoperação por teclado](04-keyboard-teleop.md) | Controlar robô real/simulação por teclado, ajuste de velocidade, limitação de segurança | A forma mais rápida de controlo manual |
| [05 Gémeo digital do braço líder](05-leader-digital-twin.md) | Braço líder físico a comandar o seguidor simulado, ajuste fino do zero | Demonstração de gémeo digital e recolha de dados |
| [06 Gravação e reprodução de dados](06-record-and-replay.md) | Gravar robô real/simulação/controlo de episódios/reprodução/script de inspeção | Um conjunto de dados treinável |
| [07 Problemas comuns e lições aprendidas](07-troubleshooting.md) | Todos os obstáculos encontrados neste fluxo e as respetivas soluções | Um manual de resolução de problemas |
| [08 Próximos passos](08-roadmap.md) | Câmaras, cenários com objetos, geração automática de dados, treino | O plano seguinte |
| [09 Tutorial de utilização completo](09-usage-tutorial.md) | Braço → gravação → inspeção → ver vídeos → treino → implementação em simulação, tudo de uma vez; inclui alternativa com ambiente conda | Do zero a um conjunto de dados válido e depois à política em ação |

## Três convenções a memorizar

1. **Sistema de unidades (alinhamento entre as três partes)**: as cinco articulações do corpo usam **−100~100** (proporção do curso, 0 = ponto médio do curso), a pinça usa **0~100**
   (0 = fechada). O robô real (`use_degrees=false`), a simulação e o braço líder seguem todos esta convenção; o conjunto de dados gravado tem a mesma estrutura dos conjuntos de dados reais oficiais
   como `lerobot/svla_so101_pickplace` (vetor de 6 dimensões + nomes das articulações).
2. **Correspondência de papéis**: o objeto controlado (robô real ou simulação) usa sempre `--robot.*`; o dispositivo de controlo (teclado/braço líder) usa sempre `--teleop.*`.
3. **Prefixo dos comandos nesta máquina**: nesta máquina de desenvolvimento, todos os comandos `uv` precisam de definir primeiro o diretório de cache (motivo em [07](07-troubleshooting.md)):

   ```bash
   export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
   ```

## Ambiente testado

| Item | Versão |
| --- | --- |
| Sistema | Windows 11 |
| Python / uv | 3.12.9 / 0.12.5 |
| lerobot | 0.6.2 (este repositório, `.venv` isolado do projeto, não afeta o conda) |
| MuJoCo | 3.16.0 |
| PyTorch | 2.11.0 (versão CPU) |
| Hardware | SO-ARM101 braço líder (COM163) + seguidor (COM172), chip de porta série CH343 |
