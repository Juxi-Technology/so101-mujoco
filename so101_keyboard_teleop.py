"""LeRobot teleoperator plugin: keyboard joint-jog for the SO-ARM101.

Hold a key to move one joint at a constant rate. Keys are deliberately chosen
to avoid the recording controls of ``lerobot-record`` (Right/Left/Esc and their
letter aliases ``n`` / ``r`` / ``q``), which listen globally at the same time:

    w / s   shoulder_lift  + / -        a / z   shoulder_pan  + / -
    e / d   elbow_flex     + / -        t / g   wrist_flex    + / -
    y / h   wrist_roll     + / -        u / j   gripper       open / close

``get_action`` returns an *absolute* joint target in SO-101 hardware units
(body joints in [-100, 100], gripper in [0, 100]) -- the same convention the
:class:`~so101_mujoco_robot.SO101MujocoRobot` uses. The target starts at the
middle of every joint range (gripper at 50), matching the pose the sim robot
starts in, and is rate-limited by ``rate`` (units per second while a key is
held), so the arm never jumps even if the loop stalls briefly.
"""

from __future__ import annotations

import logging
import sys
import time
from dataclasses import dataclass
from queue import Queue
from typing import TYPE_CHECKING, Any, cast

from lerobot.lerobot_types import RobotAction
from lerobot.teleoperators.config import TeleoperatorConfig
from lerobot.teleoperators.teleoperator import Teleoperator
from lerobot.utils.decorators import check_if_already_connected, check_if_not_connected
from lerobot.utils.import_utils import _pynput_available, require_package
from lerobot.utils.keyboard_input import pynput_can_capture

from so101_mujoco_robot import GRIPPER, JOINT_NAMES

PYNPUT_AVAILABLE = _pynput_available
if TYPE_CHECKING:
    from pynput import keyboard
else:
    keyboard = None
    if PYNPUT_AVAILABLE:
        try:
            from pynput import keyboard
        except Exception as e:  # installed but not importable here
            PYNPUT_AVAILABLE = False
            logging.info("Could not import pynput keyboard backend: %s", e)

# key -> (joint, direction); direction is +1/-1 in normalized units.
KEY_MAP: dict[str, tuple[str, float]] = {
    "w": ("shoulder_lift", +1.0),
    "s": ("shoulder_lift", -1.0),
    "a": ("shoulder_pan", +1.0),
    "z": ("shoulder_pan", -1.0),
    "e": ("elbow_flex", +1.0),
    "d": ("elbow_flex", -1.0),
    "t": ("wrist_flex", +1.0),
    "g": ("wrist_flex", -1.0),
    "y": ("wrist_roll", +1.0),
    "h": ("wrist_roll", -1.0),
    "u": ("gripper", +1.0),
    "j": ("gripper", -1.0),
}
_WITHIN_JOINT = (-100.0, 100.0)
_WITHIN_GRIPPER = (0.0, 100.0)
_MAX_DT = 0.1  # s; cap the per-call integration step so stalls never jump the arm


@TeleoperatorConfig.register_subclass("so101_keyboard")
@dataclass
class SO101KeyboardTeleopConfig(TeleoperatorConfig):
    """Config for the keyboard joint-jog teleoperator.

    Args:
        rate: Units per second for the five body joints while a key is held
            (the full [-100, 100] range takes ~3.3 s at the default 60).
        gripper_rate: Same, for the gripper ([0, 100] scale).
    """

    rate: float = 60.0
    gripper_rate: float = 60.0


class SO101KeyboardTeleop(Teleoperator):
    config_class = SO101KeyboardTeleopConfig
    name = "so101_keyboard"

    def __init__(self, config: SO101KeyboardTeleopConfig):
        super().__init__(config)
        self.config = config
        self.robot_type = config.type

        self.event_queue: Queue[tuple[str | keyboard.Key | None, bool]] = Queue()
        self.current_pressed: dict[str | keyboard.Key | None, bool] = {}
        self.listener = None
        self.logs: dict[str, float] = {}

        self._target = {name: (50.0 if name == GRIPPER else 0.0) for name in JOINT_NAMES}
        self._last_t: float | None = None
        self._connected = False

    # ------------------------------------------------------------ interface
    @property
    def action_features(self) -> dict:
        return {f"{name}.pos": float for name in JOINT_NAMES}

    @property
    def feedback_features(self) -> dict:
        return {}

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def is_calibrated(self) -> bool:
        return True

    def calibrate(self) -> None:
        pass

    def configure(self) -> None:
        pass

    @check_if_already_connected
    def connect(self, calibrate: bool = True) -> None:
        require_package("pynput", extra="pynput-dep")
        self._connected = True
        self._last_t = None
        if PYNPUT_AVAILABLE and pynput_can_capture():
            self.listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
            self.listener.start()
            logging.info("SO-101 keyboard teleop ready. %s", " | ".join(
                f"{k}={j}{'+' if d > 0 else '-'}" for k, (j, d) in KEY_MAP.items()))
        else:
            logging.warning(
                "pynput cannot capture keys in this environment (headless/Wayland); "
                "the keyboard teleoperator will produce no movement. Use a Windows desktop "
                "or an X11 session."
            )
            self.listener = None

    def _on_press(self, key) -> None:
        if hasattr(key, "char"):
            key = key.char
        self.event_queue.put((key, True))

    def _on_release(self, key) -> None:
        if hasattr(key, "char"):
            key = key.char
        self.event_queue.put((key, False))
        if keyboard is not None and key == keyboard.Key.esc:
            logging.info("ESC pressed, disconnecting the keyboard teleoperator.")
            self.disconnect()

    def _drain_pressed_keys(self) -> None:
        while not self.event_queue.empty():
            key_char, is_pressed = self.event_queue.get_nowait()
            self.current_pressed[key_char] = is_pressed

    @check_if_not_connected
    def get_action(self) -> RobotAction:
        before_read_t = time.perf_counter()
        self._drain_pressed_keys()

        now = time.perf_counter()
        dt = _MAX_DT if self._last_t is None else min(now - self._last_t, _MAX_DT)
        self._last_t = now

        for key, pressed in self.current_pressed.items():
            if not pressed or key not in KEY_MAP:
                continue
            name, direction = KEY_MAP[key]
            rate = self.config.gripper_rate if name == GRIPPER else self.config.rate
            lo, hi = _WITHIN_GRIPPER if name == GRIPPER else _WITHIN_JOINT
            self._target[name] = min(max(self._target[name] + direction * rate * dt, lo), hi)

        self.logs["read_pos_dt_s"] = time.perf_counter() - before_read_t
        return cast(RobotAction, {f"{name}.pos": self._target[name] for name in JOINT_NAMES})

    def send_feedback(self, feedback: dict[str, Any]) -> None:
        pass

    def disconnect(self) -> None:
        # Idempotent: the Esc handler disconnects mid-session and the caller's
        # cleanup disconnects again; a second call must not raise.
        if self.listener is not None:
            self.listener.stop()
            self.listener = None
        self._connected = False


def drain_pending_keys(duration_s: float = 0.3) -> None:
    """Drain keys buffered in the Windows console input queue.

    The pynput listener observes key presses without consuming them, so keys
    pressed while the terminal window is focused during a session also pile up
    in the console input queue. When the process exits, the shell (PSReadLine)
    resumes reading that queue and echoes all of them onto the next prompt at
    once. Consuming the queue here -- while the process still owns it -- keeps
    the shell prompt clean. Windows-only; a no-op elsewhere.
    """
    if sys.platform != "win32":
        return
    try:
        import msvcrt

        deadline = time.monotonic() + duration_s
        while time.monotonic() < deadline:
            while msvcrt.kbhit():
                msvcrt.getwch()
            time.sleep(0.02)
    except Exception:  # noqa: BLE001 -- cosmetic cleanup must not fail shutdown
        pass
