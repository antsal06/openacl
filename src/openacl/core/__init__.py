"""OpenACL gait-core (layer 3): filtering, gait events, cycles, parameters, symmetry, MDC.

Pure Python/numpy/scipy. This package never imports ``openacl.backends``; its only input is
a :class:`openacl.schema.KinematicsResult` (ADR-0007).
"""

from __future__ import annotations

from .cycles import CycleMeta, GaitCycles, normalize_cycles
from .deviation import (
    DeviationResult,
    compute_deviation,
    gait_profile_score_deg,
    gait_variable_score_deg,
    pct_outside_2sd,
)
from .events import GaitEvents, detect_events
from .filtering import interpolate_short_gaps, lowpass, lowpass_columns
from .mdc import (
    DEFAULT_MDC,
    LiteratureMdc,
    ReliabilityResult,
    default_mdc,
    icc_2_1,
    is_above_mdc,
    mdc_table_from_sessions,
    reliability_from_repeats,
)
from .normband import NormBand
from .pipeline import GaitAnalysis, analyze, filter_result
from .spatiotemporal import (
    ParamStat,
    SideSpatiotemporal,
    Spatiotemporal,
    compute_spatiotemporal,
)
from .symmetry import (
    SymmetryResult,
    compute_symmetry,
    curve_rms_difference_deg,
    gait_asymmetry_pct,
    symmetry_index_pct,
)

__all__ = [
    "DEFAULT_MDC",
    "CycleMeta",
    "DeviationResult",
    "GaitAnalysis",
    "GaitCycles",
    "GaitEvents",
    "LiteratureMdc",
    "NormBand",
    "ParamStat",
    "ReliabilityResult",
    "SideSpatiotemporal",
    "Spatiotemporal",
    "SymmetryResult",
    "analyze",
    "compute_deviation",
    "compute_spatiotemporal",
    "compute_symmetry",
    "curve_rms_difference_deg",
    "default_mdc",
    "detect_events",
    "filter_result",
    "gait_asymmetry_pct",
    "gait_profile_score_deg",
    "gait_variable_score_deg",
    "icc_2_1",
    "interpolate_short_gaps",
    "is_above_mdc",
    "lowpass",
    "lowpass_columns",
    "mdc_table_from_sessions",
    "normalize_cycles",
    "pct_outside_2sd",
    "reliability_from_repeats",
    "symmetry_index_pct",
]
