# Tutorial completo SO-ARM101 × MuJoCo (índice)

> 🌐 Languages: [简体中文](../README.md) · [English](../en/README.md) · [Deutsch](../de/README.md) · [Español](../es/README.md) · [Français](../fr/README.md) · [Italiano](../it/README.md) · [日本語](../ja/README.md) · [한국어](../ko/README.md) · **Português (BR)** · [Português (PT)](../pt-pt/README.md) · [繁體中文](../zh-hant/README.md)

> Este tutorial documenta e reproduz o **fluxo de trabalho completo de simulação + robô real** do SO-ARM101: da preparação do ambiente e verificação do modelo à calibração no robô real,
> passando pela teleoperação por teclado/braço líder e pela gravação e reprodução de dados. Todos os comandos foram validados em sessões reais de robô + simulação em 2026-10-15.
>
> Público-alvo: usuários do kit Juxi SO-ARM101 e engenheiros internos. Não é necessário conhecimento prévio de MuJoCo ou LeRobot.

## Mapa do fluxo completo (duas trilhas, um conjunto de componentes compartilhado)

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

| Cap. | Conteúdo | O que você obtém |
| --- | --- | --- |
| [01 Preparação do ambiente](01-environment.md) | Ambiente uv, extras de dependências, observações para Windows | Um ambiente executável |
| [02 Verificação do modelo de simulação](02-sim-model-verification.md) | Carregamento/comparação/renderização dos três modelos MJCF | Confiança no modelo e no comportamento da simulação |
| [03 Conexão com o robô real e calibração](03-hardware-calibration.md) | Identificação da porta serial, verificação inicial somente leitura, calibração do braço seguidor/líder | Dois braços reconhecidos pelo software |
| [04 Teleoperação por teclado](04-keyboard-teleop.md) | Controle do robô real/simulação pelo teclado, ajuste de taxa, limite seguro de velocidade | A forma mais rápida de controle manual |
| [05 Gêmeo digital do braço líder](05-leader-digital-twin.md) | Braço líder físico acionando o braço seguidor simulado, ajuste fino do zero | Demonstração de gêmeo digital e coleta de dados |
| [06 Gravação e reprodução de dados](06-record-and-replay.md) | Gravar robô real/simulação/controle de episódios/reprodução/script de inspeção | Um conjunto de dados treinável |
| [07 Perguntas frequentes e experiências](07-troubleshooting.md) | Todas as armadilhas encontradas neste fluxo e suas soluções | Manual de solução de problemas |
| [08 Roteiro futuro](08-roadmap.md) | Câmeras, cenas com objetos, geração automática de dados, treinamento | Planos para os próximos passos |
| [09 Tutorial de uso completo](09-usage-tutorial.md) | Iniciar o braço → gravar → inspecionar → assistir aos vídeos → treinar → implantar na simulação, tudo em um só fluxo; inclui alternativa com ambiente conda | Do zero a um conjunto de dados qualificado, e depois à política em ação |

## Três convenções que você precisa lembrar

1. **Sistema de unidades (alinhamento entre as três partes)**: as cinco juntas do corpo usam **−100~100** (proporção do curso, 0 = meio do curso) e a garra usa **0~100**
   (0 = fechada). O robô real (`use_degrees=false`), a simulação e o braço líder seguem todos essa convenção; os conjuntos de dados gravados têm a mesma estrutura dos
   conjuntos de dados reais oficiais, como `lerobot/svla_so101_pickplace` (vetor de 6 dimensões + nomes das juntas).
2. **Correspondência de papéis**: o objeto controlado (robô real ou simulação) sempre usa `--robot.*`; o dispositivo de controle (teclado/braço líder) sempre usa `--teleop.*`.
3. **Prefixo de comando nesta máquina**: nesta máquina de desenvolvimento, todos os comandos `uv` exigem que o diretório de cache seja definido antes (motivo em [07](07-troubleshooting.md)):

   ```bash
   export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
   ```

## Ambiente testado

| Item | Versão |
| --- | --- |
| Sistema | Windows 11 |
| Python / uv | 3.12.9 / 0.12.5 |
| lerobot | 0.6.2 (este repositório, isolado no `.venv` do projeto, sem afetar o conda) |
| MuJoCo | 3.16.0 |
| PyTorch | 2.11.0 (versão CPU) |
| Hardware | SO-ARM101 braço líder (COM163) + seguidor (COM172), chip serial CH343 |
