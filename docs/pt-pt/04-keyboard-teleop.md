# 04 · Teleoperação por teclado

Usar o teclado para «mover aos toques» as articulações e controlar manualmente o braço real ou simulado — a forma mais rápida de controlar sem o braço líder e também um dos meios de gravar dados de demonstração.

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

(`teleoperate.py` usa por omissão `--robot.type=so101_mujoco --teleop.type=so101_keyboard`.)

## Teclas (funcionam enquanto premidas, escuta global — independentemente da janela em foco)

| Tecla | Ação | Tecla | Ação |
| --- | --- | --- | --- |
| `w` / `s` | shoulder_lift cima / baixo | `a` / `z` | shoulder_pan esquerda / direita |
| `e` / `d` | elbow_flex estender / fletir | `t` / `g` | wrist_flex + / − |
| `y` / `h` | wrist_roll + / − | `u` / `j` | pinça abrir / fechar |

As teclas foram **deliberadamente escolhidas para evitar as teclas de controlo da gravação** (`n/r/q`, setas, `Esc`), para que a teleoperação e a gravação possam funcionar em simultâneo.

## Parâmetros essenciais

| Parâmetro | Função | Valor recomendado |
| --- | --- | --- |
| `--teleop.rate` | Velocidade alvo ao manter a tecla premida (unidades/segundo) | O padrão 60 é lento; no robô real **150** sente-se melhor |
| `--robot.max_relative_target` | Unidades máximas que a articulação pode mover por ciclo de controlo (limitação de segurança) | Robô real **5** (teleoperação a 60 Hz) / **10** (gravação a 30 Hz) |
| `--robot.use_degrees=false` | Usar proporção do curso (−100~100) em vez de graus | **Obrigatório no robô real**, caso contrário as unidades não batem certo (na simulação é consistente por omissão) |

## Comportamento

- **Não escreva durante a teleoperação**: a escuta do teclado é **global e não consome as teclas** — premir uma tecla mapeada em qualquer janela do computador
  (`w a s z e d t g y h u j`, incluindo a escrita de pinyin numa caixa de chat) aciona também o braço. O modo com braço líder não tem este problema.
- **O braço move-se no instante da ligação**: o braço seguidor real aplica primeiro binário (fica rígido) e depois move-se para a «pose do ponto médio» (o alvo antes de premir teclas);
  o braço simulado converge diretamente para a pose do ponto médio. Mantenha espaço livre à volta.
- **Sair**: `Ctrl-C` nesse terminal (ou premir `Esc`, que desliga a escuta do teclado e sai de forma limpa). Após sair, o robô real **perde o binário e fica mole**;
  segure-o com a mão — é o comportamento normal.
- **As séries de WARNING `clamped to be safe` no registo de arranque** são saída normal do limitador de velocidade enquanto «recupera o atraso»; param automaticamente ao chegar à posição.
