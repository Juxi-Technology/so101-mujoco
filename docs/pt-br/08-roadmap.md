# 08 · Roteiro futuro

## Concluído (executável diretamente neste repositório)

| Capacidade | Status |
| --- | --- |
| Verificação de carregamento/acionamento/renderização dos modelos de simulação (3 MJCF) | ✅ |
| Teleoperação por teclado (simulação / robô real) | ✅ validado no robô real |
| Gêmeo digital do braço líder (braço físico → braço simulado, com ajuste fino do zero) | ✅ validado no robô real |
| Gravação de dados (robô real / simulação) + controle de episódios + script de inspeção | ✅ validado no robô real |
| Reprodução de dados (robô real / simulação, mecanismo oficial) | ✅ validado no robô real |
| Teste de fumaça automatizado (`smoke_test.py` sem hardware) | ✅ 26 itens aprovados |
| Conjunto de dados visual com duas câmeras `so101_sim_vision` (5 episódios / 10610 quadros / 353,8 s) | ✅ |
| Treinamento (ACT) e implantação de política na simulação (`lerobot-train` / `lerobot-rollout`) | ✅ testado em smoke (veja [09](09-usage-tutorial.md)) |

## Próximos passos (por ordem de valor)

### Fase 2 · Câmera na cena (em andamento)

**Concluído**:
- Suporte (STEP→STL) e câmera (corpo provisório construído com base na folha de dados da HBVCAM-F2170HD V22, 25×30×5,2 mm) montados na simulação,
  com poses ajustadas por `adjust_mount.py` / `adjust_camera.py` em comparação com o robô real;
- Elemento `<camera>` integrado (`sim_cam`, fovy inicial 49°), **cadeia de gravação visual na simulação já funcional**:
  `--robot.image_camera=sim_cam` produz um conjunto de dados de vídeo `observation.images.wrist` (teste de fumaça [5] todo aprovado).

**Atualização de 2026-10-16**: mira/fovy da câmera ajustados a contento (o `adjust_camera.py` ganhou uma **janela de imagem em tempo real live view**,
com ajuste retomável e reabertura automática da janela se fechada por engano; e foi corrigido o bug "direção da lente e da imagem invertidas" causado pela direção de enquadramento da câmera do MuJoCo = **−Z do elemento**,
detalhes em [07](07-troubleshooting.md)). Um conjunto de dados visual foi gravado oficialmente com o braço líder recém-calibrado (incluindo vídeo wrist, erro de rastreamento ≤2 unidades) ✅;
as gravações experimentais antigas foram limpas em 2026-10-16 e o conjunto de dados oficial passou a ser `so101_sim_vision` (duas câmeras).
**No mesmo dia, o robô simulado foi migrado para o modelo SO-ARM100 do mujoco_menagerie** (2026-10-16): a garra do modelo do tutorial original não conseguia agarrar;
a garra do novo modelo é uma colisão baseada no CAD do robô real e segura com estabilidade o cubo de 34 mm na prática; as cadeias de gravação/teleoperação/duas câmeras/área de trabalho foram todas preservadas,
aguardando uma revisão por teleoperação no robô real (especialmente o sinal da direção de wrist_roll).
**Pendente**: após conectar a HBVCAM real, fazer o ajuste fino comparando "foto do robô real vs renderização da simulação";
opcional: substituir o corpo provisório pelo STL real da câmera. A configuração de câmera no lado do robô real (`--robot.cameras` OpenCV) será feita em seguida.

### Fase 3 · Cena e escala (em andamento)

- ✅ Área de trabalho na cena (2026-10-16): placa de base + cubos de três cores (34 mm, agarráveis) + caixa de armazenamento + câmera superior fixa `top_cam`
  (definida em `so101_assets.add_workspace`, ferramenta de renderização/verificação de ganho `preview_workspace.py`); **cadeia de gravação com duas câmeras (wrist+top)
  já funcional** (`--robot.top_camera=top_cam`);
- **Geração automática de dados**: políticas em script/RL rodando em lote a noite toda na simulação (sem humano no loop), a fonte da "eficiência de dezenas de vezes";
- Randomização de domínio visual (texturas/iluminação/trepidação da câmera) preparando o sim2real.

### Fase 4 · Treinamento e implantação

- ✅ **Cadeia de treinamento/implantação testada** (2026-10-16): `lerobot-train` (ACT, smoke de 12 passos em CPU — cerca de 2 s/passo, loss descendo normalmente,
  checkpoint salvo como esperado) e `lerobot-rollout --strategy.type=base` (executando a política de fato na simulação por 20 s,
  encerrando após enviar o braço de volta à pose inicial) já funcionam; comandos completos, pontos principais e método para retomar o treinamento em [09](09-usage-tutorial.md) seções 7/8,
  o tutorial já traz um checkpoint de demonstração `outputs/train/smoke_act` que pode ser usado para testar a cadeia de implantação;
- O treinamento oficial é feito em uma **máquina com GPU** (ACT / SmolVLA; esta máquina, apenas CPU, só serve para validar a cadeia com poucos passos);
  basta copiar o conjunto de dados ou enviá-lo a um repositório privado no HF;
- A implantação no robô real também usa `lerobot-rollout` (trocando `--robot.*` pela configuração `so101_follower`).

### Longo prazo · sim2real

Dados de simulação + pequena quantidade de dados reais em treinamento misto → avaliação no robô real a custo zero (a taxa de sucesso da política pode ser reproduzida e avaliada na simulação).
Atenção: usar dados puramente simulados diretamente no robô real (transferência zero-shot) é o caminho mais difícil; comece com o "ciclo curto" (treinar com dados reais → implantar no robô real)
e vá sobrepondo a simulação gradualmente.

## Posicionamento em uma frase

Para equipes que já têm o braço físico: simulação = **sandbox de desenvolvimento + material de demonstração + amplificador de dados**;
para potenciais clientes: simulação = **ferramenta de experiência que permite percorrer todo o fluxo antes de comprar**.
