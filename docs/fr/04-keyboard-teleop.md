# 04 · Téléopération au clavier

Piloter les articulations au clavier par petits mouvements (« jog ») pour contrôler manuellement le bras réel ou simulé — le moyen de contrôle le plus rapide sans bras maître, et l'une des méthodes d'enregistrement de données de démonstration.

## Commande

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

(`teleoperate.py` utilise par défaut `--robot.type=so101_mujoco --teleop.type=so101_keyboard`.)

## Touches (maintenir pour agir, écoute globale — quelle que soit la fenêtre au premier plan)

| Touche | Action | Touche | Action |
| --- | --- | --- | --- |
| `w` / `s` | shoulder_lift haut / bas | `a` / `z` | shoulder_pan gauche / droite |
| `e` / `d` | elbow_flex extension / flexion | `t` / `g` | wrist_flex + / − |
| `y` / `h` | wrist_roll + / − | `u` / `j` | pince ouvrir / fermer |

Les touches ont été choisies **délibérément pour éviter les touches de contrôle d'enregistrement** (`n/r/q`, flèches, `Esc`), afin que téléopération et enregistrement puissent tourner simultanément.

## Paramètres clés

| Paramètre | Rôle | Valeur recommandée |
| --- | --- | --- |
| `--teleop.rate` | vitesse cible lorsque la touche est maintenue (unités/seconde) | la valeur par défaut 60 est plutôt lente ; en pratique sur le robot réel, **150** convient mieux |
| `--robot.max_relative_target` | nombre maximal d'unités dont une articulation peut bouger par cycle de contrôle (limitation de vitesse de sécurité) | robot réel **5** (téléopération à 60 Hz) / **10** (enregistrement à 30 Hz) |
| `--robot.use_degrees=false` | utiliser le système proportionnel à la course (−100~100) plutôt que les degrés | **obligatoire pour le robot réel**, sinon les unités ne correspondent pas (la simulation est alignée par défaut) |

## Comportement

- **Ne tapez pas au clavier pendant la téléopération** : l'écoute du clavier est **globale et n'absorbe pas les touches** — toute frappe d'une touche mappée dans n'importe quelle fenêtre de l'ordinateur (`w a s z e d t g y h u j`, y compris la saisie pinyin dans une fenêtre de chat) pilote simultanément le bras. Le mode bras maître n'a pas ce problème.
- **Le bras bouge au moment de la connexion** : le bras esclave réel applique d'abord le couple (devient rigide), puis se déplace vers la « pose médiane » (la cible avant tout appui sur une touche) ; le bras simulé converge directement vers la pose médiane. Gardez de l'espace autour de vous.
- **Quitter** : `Ctrl-C` dans ce terminal (ou appuyer sur `Esc`, l'écoute clavier se déconnecte et se termine proprement). Après la sortie, le robot réel **perd son couple et devient mou**, soutenez-le à la main — c'est un comportement normal.
- **Les séries de WARNING `clamped to be safe` dans les logs de démarrage** sont la sortie normale du limiteur de vitesse en phase de « rattrapage » ; elles s'arrêtent automatiquement une fois la cible atteinte.
