# 03 · Ligação ao robô real e calibração

## Identificar a porta série

Depois de ligar a placa controladora com o chip CH343, aparece uma porta COM; **o número muda ao desligar/ligar ou ao mudar de porta USB**, por isso confirme antes de cada ligação:

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
uv run --frozen python -c "import serial.tools.list_ports as lp; [print(p.device, '|', p.description, '|', p.hwid) for p in lp.comports()]"
```

## Primeiro passo: inspeção inicial só de leitura (ligações/alimentação/verificação dos servo-motores)

**Sem escrever nada**, faça ping a cada um dos seis servo-motores e depois leia tensão e temperatura (o estado de binário é mantido como está):

```bash
uv run --frozen python examples/so101_mujoco/hardware_check.py --port COM163
```

A saída normal tem o seguinte aspeto: seis linhas de articulações, temperatura 20~30 °C, binário 0 (braço livre). **A tensão depende do modo de alimentação**: cerca de 11 V quando o braço seguidor
está ligado a uma fonte externa, cerca de 5 V quando o braço líder é alimentado apenas pela placa controladora — se conseguir ler os seis servo-motores, as ligações estão corretas. Se faltar algum ou o modelo não corresponder,
é apresentado um erro.

## Segundo passo: calibração

A calibração grava no EEPROM dos servo-motores o «intervalo de curso de cada articulação + referência de posição média» e guarda-o num ficheiro local; **é necessário calibrar o braço seguidor e o braço líder, cada um uma vez**.
Os ficheiros de calibração dos dois braços são guardados separadamente e não se afetam:

| Dispositivo | Comando | Local do ficheiro de calibração |
| --- | --- | --- |
| Braço seguidor | `uv run --frozen lerobot-calibrate --robot.type=so101_follower --robot.port=COM172 --robot.id=juxi_so101` | `~/.cache/huggingface/lerobot/calibration/robots/so_follower/juxi_so101.json` |
| Braço líder | `uv run --frozen lerobot-calibrate --teleop.type=so101_leader --teleop.port=COM163 --teleop.id=juxi_leader` | `.../calibration/teleoperators/so_leader/juxi_leader.json` |

O `id` pode ter qualquer nome, mas **a teleoperação/gravação seguintes têm de usar o mesmo id**, caso contrário a calibração volta a ser pedida.

### Passos físicos (o terminal imprime um esquema)

1. **Coloque na pose neutra e prima Enter**: base assente na horizontal na beira da mesa, braço superior na vertical para cima, antebraço na horizontal apontado para a frente, rotação do ombro e punho centrados
   (a «pinça» do braço líder é o manípulo/gatilho). A posição neste instante é registada como a «referência neutra» desse braço.
2. Depois de premir Enter, **percorra lentamente o curso completo de cada articulação, uma a uma** (`wrist_roll` não precisa de ser percorrida, é tratada automaticamente como uma volta completa); prima Enter novamente para guardar.

Pontos a ter em conta:

- Durante a calibração, o binário do braço seguidor é 0 (o braço fica mole); mova-o com a mão. O braço líder já não tem binário por natureza.
- O processo de calibração escreve no EEPROM dos servo-motores (faz parte da calibração, é normal).
- Resultados da calibração medida nesta sessão (para referência): curso de 1474~2688 contagens nas articulações do braço seguidor, `wrist_roll` 4095;
  braço líder 2208~2681 contagens. Um curso claramente assimétrico é normal (ver [05 Ajuste fino do zero](05-leader-digital-twin.md) para saber porque é necessário).
