"""Run the kinematics backend and gait-core once per pass, with a cache and no fatal errors.

Per pass (ADR-0009):

1. If ``derived/<pass>/kinematics.npz`` exists and ``force`` is off, load it -- no backend run.
2. Otherwise check the video is decodable; an HEVC ``.mov`` OpenCV cannot open is transcoded
   to H.264 first (see :func:`openacl.backends.video.transcode_to_h264`).
3. Run Sports2D, in metres when ``subject.height_m`` is known, and cache the result.
   ``visible_side`` is resolved from ``passes.yaml`` (ADR-0010, a segmented pass has a known
   walking direction) via ``meta.yaml`` ``cameras.A.near_side_when_walking_plus_x`` instead of
   Sports2D's own per-frame heuristic; a pass without a ``passes.yaml`` entry still falls back
   to ``"auto"``. ``cameras.A.distance_m`` is passed through as Sports2D's perspective-effect
   camera-to-person distance (its own default is 10 m).
4. Run :func:`openacl.core.pipeline.analyze` with the operated side and the norm bands.

A pass that fails is recorded with its error message and the session continues; one unusable
video out of ten must not cost the other nine.
"""

from __future__ import annotations

import logging
import time
import traceback
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from openacl.core.normband import NormBand
from openacl.core.pipeline import GaitAnalysis, analyze
from openacl.schema import KinematicsResult, Side
from openacl.session.model import (
    KINEMATICS_STEM,
    PassFile,
    Session,
    read_pass_directions,
    resolve_near_side_from_direction,
)

_NEAR_SIDE_TO_VISIBLE_SIDE: dict[Side, str] = {"L": "left", "R": "right"}
"""``Session.meta``/``passes.yaml``-resolved near side -> Sports2D's ``visible_side`` (ADR-0010)."""

logger = logging.getLogger(__name__)

TRANSCODED_NAME = "transcoded_h264.mp4"
"""Name of the H.264 fallback written next to the cached kinematics of a pass."""

PROVISIONAL_SPEED_CLASS = "comfortable"
"""Norm-band class used for the *per-pass* deviation scores.

The real speed class of the session comes from the Froude number of the pooled walking speed
(:func:`openacl.session.aggregate.resolve_speed_class`), which cannot be known before every
pass has been processed. The per-pass scores are diagnostics only; the report uses the pooled
ones."""


@dataclass(eq=False)
class PassResult:
    """Outcome of one pass: kinematics, gait-core analysis, or the error that stopped it."""

    name: str
    video: Path | None = None
    kinematics: KinematicsResult | None = None
    analysis: GaitAnalysis | None = None
    cached: bool = False
    """``True`` when the kinematics came from ``derived/<pass>/kinematics.npz``."""
    transcoded: bool = False
    error: str | None = None
    runtime_s: float = 0.0
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.error is None and self.analysis is not None

    @property
    def camera_near_side(self) -> Side | None:
        return self.kinematics.camera_near_side if self.kinematics is not None else None


def _ensure_decodable(video: Path, pass_dir: Path) -> tuple[Path, bool, list[str]]:
    """Return a video path Sports2D can read, transcoding to H.264 only if necessary."""
    from openacl.backends.video import can_decode, probe

    warnings: list[str] = []
    try:
        info = probe(video)
        warnings.extend(info.warnings)
        decodable = can_decode(video)
    except FileNotFoundError as exc:
        warnings.append(f"OpenCV could not open the container ({exc}); trying an H.264 transcode")
        decodable = False

    if decodable:
        return video, False, warnings

    from openacl.backends.video import transcode_to_h264

    target = pass_dir / TRANSCODED_NAME
    if target.exists():
        warnings.append(f"reusing the existing H.264 transcode {target.name}")
        return target, True, warnings
    pass_dir.mkdir(parents=True, exist_ok=True)
    warnings.append(
        f"OpenCV cannot decode {video.name} (codec not supported by the linked FFmpeg build); "
        f"transcoding to H.264 as {target.name} first"
    )
    transcode_to_h264(video, target)
    return target, True, warnings


def run_backend(
    session: Session,
    pass_file: PassFile,
    *,
    mode: str = "balanced",
    force: bool = False,
) -> tuple[KinematicsResult, bool, bool, list[str]]:
    """Return ``(kinematics, from_cache, transcoded, warnings)`` for one pass.

    The pixel-to-metre conversion is switched on exactly when ``subject.height_m`` is known;
    without it the spatial parameters (step length, speed) stay unavailable by design rather
    than being computed from a guessed height.
    """
    from openacl.backends.sports2d import run_sports2d

    pass_dir = session.pass_dir(pass_file)
    cache = session.kinematics_path(pass_file)
    if not force and cache.with_suffix(".npz").exists() and cache.with_suffix(".json").exists():
        cached = KinematicsResult.load(cache)
        warnings: list[str] = []
        if cached.backend == "sports2d" and "angles_unwrapped_180" not in cached.meta:
            # Cache written before the 180-deg unwrap existed: apply it on load.
            from openacl.backends.sports2d import unwrap_angles

            shifted = unwrap_angles(cached.angles_deg)
            if shifted:
                warnings.append(
                    f"angles shifted by 180 deg on load (wrong visible-side flip): {shifted}"
                )
        return cached, True, False, warnings

    if pass_file.video is None:
        raise FileNotFoundError(
            f"pass {pass_file.name!r} has neither a video nor a cached "
            f"{KINEMATICS_STEM}.npz in {pass_dir}"
        )

    video, transcoded, warnings = _ensure_decodable(pass_file.video, pass_dir)
    height_m = session.meta.subject.height_m

    visible_side = "auto"
    direction = read_pass_directions(session.root).get(pass_file.name)
    if direction is not None:
        near_side = resolve_near_side_from_direction(
            direction, session.meta.near_side_when_walking_plus_x
        )
        visible_side = _NEAR_SIDE_TO_VISIBLE_SIDE[near_side]

    extra_config: dict | None = None
    distance_m = session.meta.camera_distance_m("A")
    if distance_m is not None:
        extra_config = {"px_to_meters_conversion": {"perspective_value": distance_m}}

    result = run_sports2d(
        video,
        pass_dir,
        mode=mode,  # type: ignore[arg-type]
        to_meters=height_m is not None,
        person_height_m=height_m,
        visible_side=visible_side,  # type: ignore[arg-type]
        extra_config=extra_config,
    )
    if transcoded:
        result.meta["source_video"] = str(pass_file.video)
        result.meta["transcoded_to_h264"] = str(video)
        result.save(cache)
    return result, False, transcoded, warnings


def process_pass(
    session: Session,
    pass_file: PassFile,
    *,
    mode: str = "balanced",
    force: bool = False,
    normbands: Mapping[str, NormBand] | None = None,
    speed_class: str | None = None,
) -> PassResult:
    """Backend plus gait-core for one pass; every exception becomes ``PassResult.error``."""
    started = time.perf_counter()
    outcome = PassResult(name=pass_file.name, video=pass_file.video)
    try:
        kinematics, cached, transcoded, warnings = run_backend(
            session, pass_file, mode=mode, force=force
        )
        outcome.kinematics = kinematics
        outcome.cached = cached
        outcome.transcoded = transcoded
        outcome.warnings.extend(warnings)
        outcome.analysis = analyze(
            kinematics,
            operated_side=session.meta.operated_side,
            normbands=normbands,
            speed_class=speed_class or PROVISIONAL_SPEED_CLASS,
        )
    except Exception as exc:  # noqa: BLE001 - one broken pass must not kill the session
        outcome.error = f"{type(exc).__name__}: {exc}"
        logger.warning("pass %s failed: %s", pass_file.name, outcome.error)
        logger.debug("%s", traceback.format_exc())
    outcome.runtime_s = time.perf_counter() - started
    return outcome


def process_session(
    session: Session,
    *,
    mode: str = "balanced",
    force: bool = False,
    normbands: Mapping[str, NormBand] | None = None,
    speed_class: str | None = None,
    progress: bool = False,
) -> list[PassResult]:
    """Process every camera-A pass in order; camera B is listed but never processed."""
    session.derived_dir.mkdir(parents=True, exist_ok=True)
    results: list[PassResult] = []
    for index, pass_file in enumerate(session.passes_a, start=1):
        if progress:
            print(f"[{index}/{len(session.passes_a)}] {pass_file.name} ...", flush=True)
        outcome = process_pass(
            session,
            pass_file,
            mode=mode,
            force=force,
            normbands=normbands,
            speed_class=speed_class,
        )
        if progress:
            state = "cached" if outcome.cached else "computed"
            if outcome.error:
                print(f"    failed: {outcome.error}", flush=True)
            else:
                n = outcome.analysis.n_valid_cycles if outcome.analysis else {}
                print(
                    f"    {state} in {outcome.runtime_s:.1f} s, "
                    f"valid cycles L={n.get('L', 0)} R={n.get('R', 0)}, "
                    f"camera-near side {outcome.camera_near_side}",
                    flush=True,
                )
        results.append(outcome)
    return results
