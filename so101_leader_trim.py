"""SO-101 leader teleoperator with automatic centre trim (plugin ``so101_leader_trim``).

The official ``so101_leader`` normalizes each joint over its calibrated sweep
range, so the zero of every joint sits at the middle of the *recorded* range.
When a joint's mechanical travel is asymmetric around the pose the arm was
homed at, the visually centred pose reports a small non-zero value (e.g.
shoulder_pan on our unit reports -5.1 units, ~5.6 deg on a follower), which
drags the follower -- real or simulated -- a few degrees off centre. That
offset is invariant to recalibration as long as the mechanical range itself is
asymmetric, so it has to be removed in software.

This subclass subtracts, per joint, the value the leader reports at the homed
pose (raw 2048, the pose captured by ``set_half_turn_homings`` during
calibration). The trim is derived from the leader's own calibration file, so
it follows recalibrations automatically -- no manual tuning.

Trim applies to joints in range mode (``use_degrees=false``); in the default
degrees mode the offsets are not meaningful and are left untouched.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from lerobot.motors import MotorNormMode
from lerobot.teleoperators.config import TeleoperatorConfig
from lerobot.teleoperators.so_leader import SOLeader
from lerobot.teleoperators.so_leader.config_so_leader import SOLeaderTeleopConfig
from lerobot.utils.decorators import check_if_not_connected

logger = logging.getLogger(__name__)

_HOMED_RAW = 2048  # reading of a motor at the pose captured during homing


@TeleoperatorConfig.register_subclass("so101_leader_trim")
@dataclass
class SO101LeaderTrimmedConfig(SOLeaderTeleopConfig):
    """Same fields as ``so101_leader``; actions are re-centred on the homed pose."""


class SO101LeaderTrimmed(SOLeader):
    config_class = SO101LeaderTrimmedConfig
    # `name` is the calibration storage key (files live under
    # calibration/teleoperators/<name>/), so it must stay "so_leader" -- the
    # trimmed teleop is the same physical device as the official leader.
    name = "so_leader"

    def __init__(self, config: SO101LeaderTrimmedConfig):
        super().__init__(config)
        self._trim: dict[str, float] | None = None

    def _centre_offsets(self) -> dict[str, float]:
        offsets: dict[str, float] = {}
        for motor, cal in self.calibration.items():
            if self.bus.motors[motor].norm_mode is not MotorNormMode.RANGE_M100_100:
                continue  # gripper (0-100) and degrees mode keep their own semantics
            span = cal.range_max - cal.range_min
            if span > 0:
                offsets[f"{motor}.pos"] = (_HOMED_RAW - cal.range_min) / span * 200 - 100
        return offsets

    @check_if_not_connected
    def get_action(self) -> dict[str, float]:
        action = super().get_action()
        if self._trim is None:
            self._trim = self._centre_offsets()
            active = {k: round(v, 2) for k, v in self._trim.items() if abs(v) > 0.05}
            if active:
                logger.info("so101_leader_trim centre offsets (units): %s", active)
        return {key: value - self._trim.get(key, 0.0) for key, value in action.items()}
