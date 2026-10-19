# 08 · Próximos passos

## Concluído (executável diretamente neste repositório)

| Capacidade | Estado |
| --- | --- |
| Verificação de carregamento/acionamento/renderização de modelos de simulação (3 MJCF) | ✅ |
| Teleoperação por teclado (simulação / robô real) | ✅ validado no robô real |
| Gémeo digital do braço líder (braço físico → braço simulado, com ajuste fino do zero) | ✅ validado no robô real |
| Gravação de dados (robô real / simulação) + controlo de episódios + script de inspeção | ✅ validado no robô real |
| Reprodução de dados (robô real / simulação, mecanismo oficial) | ✅ validado no robô real |
| Teste de fumo automatizado (sem hardware `smoke_test.py`) | ✅ 26 itens aprovados |
| Conjunto de dados visual com duas câmaras `so101_sim_vision` (5 episódios / 10610 frames / 353.8s) | ✅ |
| Treino (ACT) e implementação de políticas em simulação (`lerobot-train` / `lerobot-rollout`) | ✅ medido no teste de fumo (ver [09](09-usage-tutorial.md)) |

## Próximos passos (ordenados por valor)

### Fase 2 · Câmaras no cenário (em curso)

**Concluído**:
- Suporte (STEP→STL) e câmara (corpo provisório construído segundo a folha de dados HBVCAM-F2170HD V22, 25×30×5.2mm) montados na simulação,
  com poses ajustadas por comparação com o robô real através de `adjust_mount.py` / `adjust_camera.py`;
- Elemento `<camera>` integrado (`sim_cam`, fovy inicial 49°), **cadeia de gravação visual em simulação já funcional**:
  `--robot.image_camera=sim_cam` produz um conjunto de dados de vídeo `observation.images.wrist` (teste de fumo [5] todo aprovado).

**Atualização de 2026-10-16**: a pontaria/fovy da câmara foi ajustada a contento (o `adjust_camera.py` ganhou uma **janela de imagem em tempo real live view**,
com retoma do ajuste no ponto onde ficou e reabertura automática da janela se for fechada por engano; e foi corrigido o bug «orientação da lente inversa à imagem» causado pela direção de enquadramento da câmara MuJoCo =
**−Z do elemento**, ver detalhes em [07](07-troubleshooting.md)). Foi gravado oficialmente um conjunto de dados visual com o braço líder recalibrado (inclui vídeo wrist, erro de seguimento ≤2 unidades) ✅;
as gravações experimentais antigas foram eliminadas em 2026-10-16 e o conjunto de dados oficial passou a ser uniformemente `so101_sim_vision` (duas câmaras).
**No mesmo dia, o robô simulado foi migrado para o modelo SO-ARM100 do mujoco_menagerie** (2026-10-16): as garras do modelo do tutorial original não conseguem agarrar,
as garras do novo modelo usam colisão CAD do robô real e conseguem, na medição, agarrar de forma estável um cubo de 34mm; as cadeias de gravação/teleoperação/duas câmaras/área de trabalho mantêm-se todas,
faltando uma revisão por teleoperação no robô real (sobretudo o sinal da direção de wrist_roll).
**Pendente**: depois de ligar a HBVCAM ao robô real, fazer o ajuste fino por comparação «captura real vs renderização em simulação»;
opcional: substituir o corpo provisório pelo STL real da câmara. A configuração de câmaras do lado do robô real (`--robot.cameras` OpenCV) será feita a seguir, da mesma forma.

### Fase 3 · Cenário e escala (em curso)

- ✅ Área de trabalho integrada no cenário (2026-10-16): base de apoio + cubos de três cores (34mm, agarrables) + caixa de arrumação + câmara fixa de vista de cima `top_cam`
  (definida em `so101_assets.add_workspace`, ferramenta de renderização/verificação de ganhos `preview_workspace.py`); **cadeia de gravação com duas câmaras (wrist+top)
  já funcional** (`--robot.top_camera=top_cam`);
- **Geração automática de dados**: políticas por script/RL correm em lote durante a noite na simulação (sem intervenção humana), e é daí que vem a «eficiência de dezenas de vezes»;
- Randomização de domínio visual (texturas/iluminação/trepidação da câmara) a preparar o sim2real.

### Fase 4 · Treino e implementação

- ✅ **Cadeia de treino/implementação já testada** (2026-10-16): `lerobot-train` (ACT, teste de fumo de 12 passos em CPU — cerca de 2s/passo, loss a descer normalmente,
  checkpoint guardado como esperado) e `lerobot-rollout --strategy.type=base` (executa realmente a política na simulação durante 20s e termina devolvendo automaticamente o braço à pose inicial) já estão funcionais; comandos completos, pontos essenciais e método de retoma do treino nas secções 7/8 de [09](09-usage-tutorial.md),
  o checkpoint de demonstração incluído no tutorial `outputs/train/smoke_act` pode ser usado diretamente para testar a cadeia de implementação;
- O treino oficial realiza-se numa **máquina com GPU** (ACT / SmolVLA; esta máquina, só CPU, serve apenas para validar a cadeia com poucos passos);
  basta copiar o conjunto de dados ou enviá-lo para um repositório privado no HF;
- A implementação no robô real também usa o `lerobot-rollout` (substitua `--robot.*` pela configuração `so101_follower`).

### Longo prazo · sim2real

Treino misto com dados de simulação + uma pequena quantidade de dados reais → avaliação a custo zero no robô real (em simulação é possível reproduzir e avaliar a taxa de sucesso da política).
Nota: dados puramente simulados diretamente no robô real (transferência zero-shot) é o caminho mais difícil; comece por um «ciclo curto» (treino com dados reais → implementação no robô real),
acrescentando simulação gradualmente.

## Posicionamento numa frase

Para equipas que já têm um braço físico: simulação = **caixa de areia de desenvolvimento + material de demonstração + amplificador de dados**;
para potenciais clientes: simulação = **ferramenta de experiência que permite percorrer todo o fluxo antes de comprar**.
