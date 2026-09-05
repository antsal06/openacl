"""OpenACL norm layer: loaders for public reference data sets and derived norm bands.

The heavy raw data stays in ``data/norm/`` (gitignored, see ADR-0008). Only the small derived
bands under ``openacl/norm/data/`` ship with the package; :func:`load_normbands` reads them.
"""

from openacl.norm.bands import (
    SPEED_CLASSES,
    BandKey,
    NormBand,
    assign_speed_class,
    froude,
    leg_length_m,
    load_normbands,
)

__all__ = [
    "SPEED_CLASSES",
    "BandKey",
    "NormBand",
    "assign_speed_class",
    "froude",
    "leg_length_m",
    "load_normbands",
]
