# 04 · Teleoperação por teclado

Use o teclado para acionar as juntas em pequenos incrementos e controlar manualmente o braço real ou simulado — é a forma mais rápida de controlar quando não há braço líder e também um dos meios de gravar dados de demonstração.

## Comando

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'

# 真机从动臂
uv run --frozen --with mujoco python examples/so101_mujoco/teleoperate.py \
    --robot.type=so101_follower --robot.port=COM172 --robot.id=juxi_so101 \
    --robot.use_degrees=false --robot.max_relative_target=5 \
    --teleop.type=so101_keyboard --teleop.rate=150

# 仿真从动臂（MuJoCo 窗口自动打开）
uv run --frozen --with mujoco python examples/so101_mujoco/teleoperate.py \
    --teleop.rate=150
```

(`teleoperate.py` já usa por padrão `--robot.type=so101_mujoco --teleop.type=so101_keyboard`.)

## Teclas (valem enquanto pressionadas, escuta global — não importa qual janela está em foco)

| Tecla | Ação | Tecla | Ação |
| --- | --- | --- | --- |
| `w` / `s` | shoulder_lift para cima / para baixo | `a` / `z` | shoulder_pan para a esquerda / direita |
| `e` / `d` | elbow_flex estender / dobrar | `t` / `g` | wrist_flex + / − |
| `y` / `h` | wrist_roll + / − | `u` / `j` | garra abrir / fechar |

As teclas foram escolhidas **deliberadamente para evitar as teclas de controle de gravação** (`n/r/q`, setas, `Esc`), de modo que teleoperação e gravação possam rodar ao mesmo tempo.

## Parâmetros principais

| Parâmetro | Função | Valor sugerido |
| --- | --- | --- |
| `--teleop.rate` | Velocidade alvo ao manter a tecla pressionada (unidades/segundo) | O padrão 60 é um pouco lento; no robô real, **150** dá uma sensação adequada |
| `--robot.max_relative_target` | Quanto a junta pode se mover no máximo por ciclo de controle (limite de velocidade de segurança) | Robô real **5** (teleoperação a 60 Hz) / **10** (gravação a 30 Hz) |
| `--robot.use_degrees=false` | Usa escala proporcional ao curso (−100~100) em vez de graus | **Obrigatório no robô real**, senão as unidades não batem (a simulação já é consistente por padrão) |

## Comportamento

- **Não digite durante a teleoperação**: a escuta do teclado é **global e não consome as teclas** — pressionar uma tecla mapeada em qualquer janela do computador
  (`w a s z e d t g y h u j`, inclusive pinyin em uma caixa de chat) também aciona o braço. O modo braço líder não tem esse problema.
- **O braço se move no instante da conexão**: o braço seguidor real primeiro aplica torque (fica rígido) e depois se move em direção à "pose central" (o alvo antes de pressionar teclas);
  o braço simulado converge diretamente para a pose central. Mantenha espaço livre ao redor.
- **Sair**: use `Ctrl-C` nesse terminal (ou pressione `Esc`; a escuta do teclado é desconectada e o programa sai de forma limpa). Após sair, o robô real **perde torque e fica mole**;
  segure-o com a mão — isso é comportamento normal.
- **Os WARNINGs `clamped to be safe` em sequência no log de inicialização** são saída normal do limitador de velocidade durante o "alcance"; param automaticamente ao chegar ao alvo.
