# 05 · Gémeo digital do braço líder (braço físico a comandar o braço simulado)

Arraste com a mão o **braço líder físico** e faça o **braço seguidor simulado na janela do MuJoCo** acompanhar em espelho, em tempo real — a forma correta de fazer demonstrações de gémeo digital
e recolha de dados em simulação.

## Pré-requisitos

Braço líder já calibrado (ver [03](03-hardware-calibration.md)); a porta série usada como exemplo é `COM163`.

## Comando

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
uv run --frozen --with mujoco python examples/so101_mujoco/teleoperate.py \
    --robot.type=so101_mujoco \
    --teleop.type=so101_leader_trim --teleop.port=COM163 --teleop.id=juxi_leader \
    --teleop.use_degrees=false
```

- `--robot.type=so101_mujoco`: o objeto controlado é o braço simulado; a janela abre automaticamente;
- `--teleop.*`: o dispositivo de controlo é o braço líder físico (apenas leitura, nunca aplica binário, risco zero para o braço líder);
- `--teleop.use_degrees=false`: **obrigatório**. Faz com que as unidades de saída do braço líder (proporção do curso) coincidam com as do braço simulado.

Se substituir `--robot.type` por `so101_follower --robot.port=COM172 --robot.id=juxi_so101 --robot.max_relative_target=5`,
obtém o modo habitual do kit «braço líder físico → braço seguidor real»; a mesma calibração do braço líder é válida.

## E se o zero estiver desviado? Ajuste automático do centro (`so101_leader_trim`)

**Sintoma**: o braço líder é colocado na «posição média visual», mas o braço simulado desvia-se alguns graus.

**Princípio**: o zero de normalização do lerobot = **ponto médio do intervalo registado durante o varrimento de calibração** `(min+max)/2`; porém, a «pose neutra» no momento do
Enter de calibração é registada como o valor bruto 2048. Se o curso mecânico de uma articulação for assimétrico, os dois «pontos médios» ficam sempre separados por uma quantidade fixa
(medição no servo n.º 1: intervalo registado 776~3457, ponto médio 2116, 68 contagens de diferença em relação a 2048 ≈ **5,6°**).
**Este desvio não desaparece com uma nova calibração** (a assimetria do curso é determinada pela estrutura mecânica) e tem de ser compensado no software.

**Solução**: o plugin `so101_leader_trim` calcula automaticamente a compensação de cada articulação a partir do ficheiro de calibração segundo a fórmula e subtrai-a em tempo real;
após uma nova calibração, acompanha automaticamente, sem ajuste manual de parâmetros:

```
补偿ᵢ = (2048 − minᵢ) / (maxᵢ − minᵢ) × 200 − 100
```

Valores em vigor medidos nesta máquina (impressos no registo de arranque):

| Articulação | Compensação (unidades) |
| --- | --- |
| shoulder_pan | −5.11 |
| shoulder_lift | −0.92 |
| elbow_flex | +2.54 |
| wrist_flex | +0.69 |

As restantes articulações têm um desvio <0.05 e não precisam de compensação; a pinça (0~100) e o modo em graus não participam no ajuste fino.

> Nota do programador: o `name` deste plugin tem de permanecer `"so_leader"` — o `name` é a chave do diretório de procura do ficheiro de calibração;
> um nome de tipo personalizado faz com que o ficheiro de calibração não seja encontrado e dispare incorretamente o processo de recalibração.
