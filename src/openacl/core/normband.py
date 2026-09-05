"""Norm band container: mean and SD curve of one angle channel over 0-100 % gait cycle.

The ``openacl.norm`` package fills these from public reference data sets (Fukuchi 2018,
Schreiber/Moissenet 2019, Van Criekinge 2023; see ADR-0008). Gait-core only consumes them,
it never loads data itself.
"""

from __future__ import annotations

import warnings as _warnings
from collections.abc import Iterable
from dataclasses import dataclass, field

import numpy as np

N_POINTS = 101


@dataclass(frozen=True, eq=False)
class NormBand:
    """Reference mean and SD curve of one channel, sampled over the gait cycle."""

    mean: np.ndarray
    """Shape ``(101,)``, degrees, index 0 = 0 % and index 100 = 100 % of the cycle."""
    sd: np.ndarray
    """Shape ``(101,)``, degrees, between-subject standard deviation."""
    n: int
    """Number of subjects (not cycles) the band was built from."""
    source: str
    """Citation of the reference data set, shown in every report."""
    unit: str = "deg"
    meta: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        mean = np.asarray(self.mean, dtype=float)
        sd = np.asarray(self.sd, dtype=float)
        if mean.ndim != 1 or sd.shape != mean.shape:
            raise ValueError(f"mean {mean.shape} and sd {sd.shape} must be 1-D and equal")
        if np.any(sd < 0):
            raise ValueError("sd must be non-negative")
        if self.n < 1:
            raise ValueError("n must be at least 1")
        object.__setattr__(self, "mean", mean)
        object.__setattr__(self, "sd", sd)

    @property
    def n_points(self) -> int:
        return int(self.mean.size)

    @property
    def lower_2sd(self) -> np.ndarray:
        return self.mean - 2.0 * self.sd

    @property
    def upper_2sd(self) -> np.ndarray:
        return self.mean + 2.0 * self.sd

    def z_scores(self, curve: np.ndarray) -> np.ndarray:
        """Point-wise ``(curve - mean) / sd``; ``NaN`` where the band has ``sd == 0``."""
        curve = np.asarray(curve, dtype=float)
        if curve.shape != self.mean.shape:
            raise ValueError(f"curve shape {curve.shape} != band shape {self.mean.shape}")
        with np.errstate(divide="ignore", invalid="ignore"):
            z = (curve - self.mean) / np.where(self.sd > 0, self.sd, np.nan)
        return z

    @classmethod
    def from_curves(
        cls, curves: Iterable[np.ndarray], source: str, n: int | None = None, unit: str = "deg"
    ) -> NormBand:
        """Build a band from a set of time-normalised curves (rows of shape ``(101,)``)."""
        stacked = np.asarray(list(curves), dtype=float)
        if stacked.ndim != 2:
            raise ValueError(f"expected a 2-D stack of curves, got shape {stacked.shape}")
        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore", RuntimeWarning)
            mean = np.nanmean(stacked, axis=0)
            sd = (
                np.nanstd(stacked, axis=0, ddof=1)
                if stacked.shape[0] > 1
                else np.zeros(stacked.shape[1])
            )
        return cls(
            mean=mean,
            sd=np.nan_to_num(sd, nan=0.0),
            n=int(n if n is not None else stacked.shape[0]),
            source=source,
            unit=unit,
        )
