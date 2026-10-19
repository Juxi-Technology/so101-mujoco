# 01 · Preparação do ambiente

Operação única. Este repositório usa o **uv para gerir uma `.venv` isolada dentro do projeto** — o `uv run` utiliza apenas o ambiente deste diretório,
não toca no seu conda (esta escolha é intencional, ver [07 Problemas comuns](07-troubleshooting.md)).

## Instalação

```bash
export UV_CACHE_DIR='C:\Users\admin\AppData\Local\Temp\uv-cache'   # 本机特例，见 07

# CPU 版 torch（本机无独显；有 NVIDIA GPU 的机器去掉 UV_TORCH_BACKEND 并参考 pyproject 注释换 CUDA 版）
UV_TORCH_BACKEND=cpu uv sync --frozen --extra core_scripts --extra feetech --extra pynput-dep --extra training
```

Para que servem os quatro extras:

| extra | O que fornece | Quem precisa |
| --- | --- | --- |
| `core_scripts` | Pontos de entrada oficiais record / teleoperate / calibrate / replay + conjunto de dados + dependências de visualização | Todos |
| `feetech` | `scservo_sdk` (protocolo série dos servo-motores STS3215) | Operações com o robô real |
| `pynput-dep` | Escuta global do teclado | Teleoperação por teclado, teclas de controlo de episódios na gravação |
| `training` | `accelerate` / `wandb`, etc. | Treino com `lerobot-train`, implementação de políticas (`lerobot-rollout`) |

Quando necessário, acrescente o MuJoCo temporariamente (não entra no ficheiro de lock, é carregado a pedido):

```bash
uv run --frozen --with mujoco python <脚本>
```

**Prefere usar um ambiente conda?** Então os comandos deixam de precisar do prefixo `uv run` — os três comandos para criar o ambiente e os pontos a ter em conta estão em
[09 Tutorial de utilização completo · Anexo A](09-usage-tutorial.md).

## Verificação

```bash
uv run --frozen --with mujoco python -c "import mujoco, scservo_sdk, pynput, lerobot, torch; print('OK')"
uv run --frozen lerobot-calibrate --help | head -3   # 官方入口可用
```

## Problemas comuns

- **O `uv sync` apresenta `failed to persist temporary file ... os error 17`**: caso especial do diretório de cache do uv desta máquina, que atravessa discos;
  basta usar o prefixo `UV_CACHE_DIR` acima, ver detalhes em [07](07-troubleshooting.md).
- **Não use o Python da Microsoft Store**: escolha o Python 3.12 gerido automaticamente pelo uv.
- A primeira execução de `uv run --with mujoco` transfere um wheel do mujoco com cerca de 5,6 MB; depois passa a usar a cache.
