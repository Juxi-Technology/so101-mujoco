# 02 · Verificação do modelo de simulação (carregamento e acionamento de MJCF)

## Origem dos modelos

Os três modelos MJCF públicos do SO-ARM101 foram todos validados como utilizáveis neste projeto:

| Abreviação | Arquivo | Origem |
| --- | --- | --- |
| Oficial - nova calibração | `SO101/so101_new_calib.xml` | Repositório oficial TheRobotStudio/SO-ARM100; **há uma cópia idêntica (byte a byte) dentro do zip do tutorial deste repositório** |
| Oficial - calibração antiga | `SO101/so101_old_calib.xml` | Mesmo repositório (não está no zip, é preciso baixar) |
| Pacote de descrição ROS2 | `so_arm101_description/mjcf/so_arm101.xml` | Anexo `SO-ARM101_ROS2.zip` do tutorial deste repositório |

Nota: o fluxo de extração do zip era fornecido pela versão inicial de `so101_assets.py` e permanece disponível para consulta; desde 2026-10-16 o robô simulado foi migrado para
o **modelo SO-ARM100 do mujoco_menagerie** (vendored em `assets/menagerie_so_arm100/`; motivo da migração e pontos principais na nota de projeto em [07](07-troubleshooting.md)).

## Verificação de acionamento e renderização

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
uv run --frozen --with mujoco python examples/so101_mujoco/load_and_drive.py \
    --model "<模型路径>" --out-dir out
```

O script gera um resumo da estrutura (juntas/atuadores/ganhos/faixas), renderiza um vídeo de validação com "varredura junta a junta das seis juntas + senoide coordenada" e quadros estáticos.
Exemplos de resumo da estrutura estão em `reports/` (fornecidos com o repositório); os vídeos de comparação (`media/`) são volumosos e não são distribuídos com o repositório — podem ser regerados a qualquer momento com o comando acima.

## Principais diferenças entre os três modelos (medidas)

| Item | Oficial - nova calibração | Oficial - calibração antiga | Pacote de descrição ROS2 |
| --- | --- | --- | --- |
| Semântica do zero | **meio do curso** da junta | posição **totalmente estendida** na horizontal | meio do curso |
| Nomes das juntas | `shoulder_pan` | idem à esquerda | `shoulder_pan_joint` (sufixo) |
| Ganho de posição | kp=998.22, kv=2.731 | **kp=17.8, kv=0** | kp=998.22 |
| Unidade da garra | hinge em radianos | hinge em radianos | **normalizada 0~1** |
| Exclusão de autocolisão | não | não | sim (6 pares) |

**Erro de rastreamento medido**: a nova calibração e o pacote de descrição mantêm erro de 0,0005 rad em repouso; a calibração antiga, 0,03 rad (queda de cerca de 1,7°, kp 56 vezes menor).
Ao avaliar a mesma política na simulação, trocar o modelo produz dinâmicas diferentes; observe qual deles foi usado na gravação.

## Comportamentos do modelo que você precisa lembrar

1. **A direção positiva de `shoulder_lift` aponta para baixo**: no torque de acionamento, "abaixar" usa ângulo positivo; verifique o sinal antes de fazer mapeamento de teleoperação ou conversão de dados.
2. **Encostar no chão bloqueia**: o limite de abaixamento faz a ponta do dedo tocar o solo e ser bloqueada (o script embute uma proteção de 8 cm acima do chão que reduz automaticamente a amplitude).
3. Os modelos oficiais não têm câmera nem keyframe; existe a variante com câmera `so101_new_calib_camera.xml`, que poderá ser usada futuramente para gravar dados visuais.
