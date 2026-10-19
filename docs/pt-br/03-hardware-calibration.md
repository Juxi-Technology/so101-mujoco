# 03 · Conexão com o robô real e calibração

## Identificação da porta serial

Após conectar a placa driver com o chip CH343, aparece uma porta COM; **o número muda ao desconectar/reconectar ou ao trocar de porta USB**, então confirme antes de cada conexão:

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
uv run --frozen python -c "import serial.tools.list_ports as lp; [print(p.device, '|', p.description, '|', p.hwid) for p in lp.comports()]"
```

## Passo 1: verificação inicial somente leitura (fiação/alimentação/inspeção dos servos)

**Sem escrever nada**, faça ping em cada um dos seis servos e depois leia tensão e temperatura (o estado de torque é mantido como está):

```bash
uv run --frozen python examples/so101_mujoco/hardware_check.py --port COM163
```

Saída normal: seis linhas de juntas, temperatura de 20~30 °C, torque 0 (braço livre). **A tensão depende do modo de alimentação**: o braço seguidor com fonte externa fica em cerca de 11 V; o braço líder alimentado apenas pela placa driver fica em cerca de 5 V — conseguir ler os seis servos por completo significa que a fiação está correta. Se houver servo faltando/modelo incompatível, o script reporta erro diretamente.

## Passo 2: calibração

A calibração grava no EEPROM dos servos a "faixa de curso de cada junta + referência central" e salva em um arquivo local; **o braço seguidor e o braço líder precisam ser calibrados, cada um uma vez**.
Os arquivos de calibração dos dois braços ficam separados e não se afetam:

| Dispositivo | Comando | Local do arquivo de calibração |
| --- | --- | --- |
| Braço seguidor | `uv run --frozen lerobot-calibrate --robot.type=so101_follower --robot.port=COM172 --robot.id=juxi_so101` | `~/.cache/huggingface/lerobot/calibration/robots/so_follower/juxi_so101.json` |
| Braço líder | `uv run --frozen lerobot-calibrate --teleop.type=so101_leader --teleop.port=COM163 --teleop.id=juxi_leader` | `.../calibration/teleoperators/so_leader/juxi_leader.json` |

O `id` pode ter qualquer nome, mas **a teleoperação/gravação posterior precisa usar o mesmo id**, caso contrário será solicitada nova calibração.

### Passos físicos (o terminal imprime um diagrama)

1. **Coloque na pose central e pressione Enter**: base apoiada na borda da mesa, braço superior na vertical para cima, antebraço na horizontal para frente, rotação do ombro e punho centralizados
   (a "garra" do braço líder é a manopla/gatilho). A posição nesse instante é registrada como a "referência central" desse braço.
2. Após o Enter, **mova cada junta lentamente por toda a faixa de movimento** (`wrist_roll` não precisa ser varrida, é tratada automaticamente como volta completa) e pressione Enter para salvar.

Observações:

- Durante a calibração do braço seguidor o torque é 0 (o braço fica mole); segure com a mão para movê-lo. O braço líder já não tem torque por natureza.
- O processo de calibração grava no EEPROM dos servos (faz parte da calibração, é normal).
- Resultado medido nesta calibração (para referência): curso das juntas do braço seguidor 1474~2688 contagens, `wrist_roll` 4095;
  braço líder 2208~2681 contagens. Curso claramente assimétrico é normal (veja [05 Ajuste fino do zero](05-leader-digital-twin.md) para entender por que é necessário).
