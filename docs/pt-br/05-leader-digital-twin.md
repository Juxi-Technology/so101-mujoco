# 05 · Gêmeo digital do braço líder (braço físico acionando o braço simulado)

Arraste com a mão o **braço líder físico** e faça o **braço seguidor simulado na janela do MuJoCo** acompanhar em tempo real — demonstração de gêmeo digital e
a forma correta de coletar dados na simulação.

## Pré-requisitos

Braço líder calibrado (veja [03](03-hardware-calibration.md)), porta serial usando `COM163` como exemplo.

## Comando

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'
uv run --frozen --with mujoco python examples/so101_mujoco/teleoperate.py \
    --robot.type=so101_mujoco \
    --teleop.type=so101_leader_trim --teleop.port=COM163 --teleop.id=juxi_leader \
    --teleop.use_degrees=false
```

- `--robot.type=so101_mujoco`: o objeto controlado é o braço simulado; a janela abre automaticamente;
- `--teleop.*`: o dispositivo de controle é o braço líder físico (somente leitura, nunca aplica torque, risco zero para o braço líder);
- `--teleop.use_degrees=false`: **obrigatório**. Faz a unidade de saída do braço líder (escala proporcional ao curso) ser compatível com o braço simulado.

Troque `--robot.type` por `so101_follower --robot.port=COM172 --robot.id=juxi_so101 --robot.max_relative_target=5`
para obter o uso convencional do kit "braço líder físico → braço seguidor real"; a mesma calibração do braço líder é válida.

## E se o zero estiver deslocado: ajuste fino automático de centralização (`so101_leader_trim`)

**Sintoma**: quando o braço líder é colocado na "posição central visual", o braço simulado fica alguns graus deslocado.

**Princípio**: o zero normalizado do lerobot = **ponto médio da faixa registrada na varredura de calibração** `(min+max)/2`; já a
"pose central" no momento do Enter da calibração é registrada como o valor bruto 2048. Basta que o curso mecânico de uma junta seja assimétrico para que os dois "pontos médios" fiquem sempre com uma diferença fixa
(medido no servo nº 1: faixa registrada 776~3457, ponto médio 2116, diferença de 68 contagens em relação a 2048 ≈ **5,6°**).
**Essa diferença não desaparece com uma nova calibração** (a assimetria do curso é determinada pela estrutura mecânica); é preciso compensá-la no software.

**Solução**: o plugin `so101_leader_trim` calcula automaticamente a compensação de cada junta a partir do arquivo de calibração pela fórmula e a subtrai em tempo real;
após uma nova calibração ele acompanha automaticamente, sem ajuste manual de parâmetros:

```
补偿ᵢ = (2048 − minᵢ) / (maxᵢ − minᵢ) × 200 − 100
```

Valores medidos em vigor nesta máquina (impressos no log de inicialização):

| Junta | Compensação (unidades) |
| --- | --- |
| shoulder_pan | −5.11 |
| shoulder_lift | −0.92 |
| elbow_flex | +2.54 |
| wrist_flex | +0.69 |

As demais juntas têm desvio <0,05 e não precisam de compensação; a garra (0~100) e o modo em graus não participam do ajuste fino.

> Nota do desenvolvedor: o `name` desse plugin deve permanecer `"so_leader"` — o `name` é a chave do diretório de busca do arquivo de calibração;
> um nome de tipo personalizado faria o arquivo de calibração não ser encontrado, disparando por engano o fluxo de recalibração.
