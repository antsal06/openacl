"""Session metadata and pass discovery (ADR-0009).

A session folder looks like this::

    data/sessions/2026-09-05_1930/
        meta.yaml
        A_pass01.mov ... A_pass10.mov      # camera A, sagittal, the production path
        B_pass01.mov ...                   # camera B, listed only, not processed here
        derived/                           # everything this layer writes
            A_pass01/kinematics.npz|json
            session.json
            report.md

Parsing is deliberately tolerant: a missing or malformed field produces a warning on
:attr:`SessionMeta.warnings` instead of an exception, because a report from an incompletely
documented session is still more useful than no report at all. Only a missing ``meta.yaml``
or a session without any pass is an error.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Literal

import yaml

from openacl.schema import Side
from openacl.session.segment import PASSES_FILENAME

VIDEO_SUFFIXES: tuple[str, ...] = (".mov", ".mp4", ".m4v", ".avi")
"""Accepted container suffixes, matched case-insensitively (iPhone writes ``.MOV``)."""

DERIVED_DIRNAME = "derived"
META_FILENAME = "meta.yaml"
KINEMATICS_STEM = "kinematics"

DEFAULT_NEAR_SIDE_WHEN_WALKING_PLUS_X: Side = "R"
"""Fallback for ``meta.yaml`` ``cameras.A.near_side_when_walking_plus_x`` (ADR-0010): which
subject side is camera-near while walking in the ``+x`` direction. Aufbau-abhängig; Antons
Aufbau vom 2026-09-07 matches this default, but a differently placed camera A does not."""

_PASS_PATTERN = re.compile(r"^(?P<camera>[A-Za-z])_pass(?P<number>\d+)$")

SCALAR_META_FIELDS: dict[str, type | tuple[type, ...]] = {
    "date": (str, object),
    "time": (str, object),
    "post_op_weeks": (int, float),
    "location": str,
    "shoes": str,
    "pain_now_0_10": (int, float),
    "pain_contra_0_10": (int, float),
    "fatigue_0_10": (int, float),
    "sleep_hours": (int, float),
    "activity_yesterday": str,
    "notes": str,
}
"""Fields of ``docs/PROTOKOLL-AUFNAHME.md``; every one of them may be absent."""


@dataclass(frozen=True)
class SessionSubject:
    """Subject block of ``meta.yaml`` (ADR-0009).

    ``height_m`` drives Sports2D's pixel-to-metre conversion and the Froude speed class,
    ``operated_side`` decides which limb the symmetry index calls "operated".
    """

    height_m: float | None = None
    mass_kg: float | None = None
    operated_side: Side | None = None
    surgery_date: str | None = None
    graft: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "height_m": self.height_m,
            "mass_kg": self.mass_kg,
            "operated_side": self.operated_side,
            "surgery_date": self.surgery_date,
            "graft": self.graft,
            **self.extra,
        }


@dataclass(frozen=True)
class SessionMeta:
    """Everything ``meta.yaml`` says about one recording session."""

    date: str | None = None
    time: str | None = None
    post_op_weeks: float | None = None
    location: str | None = None
    shoes: str | None = None
    pain_now_0_10: float | None = None
    pain_contra_0_10: float | None = None
    fatigue_0_10: float | None = None
    sleep_hours: float | None = None
    activity_yesterday: str | None = None
    notes: str | None = None
    subject: SessionSubject = field(default_factory=SessionSubject)
    cameras: dict[str, dict[str, Any]] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    @property
    def operated_side(self) -> Side | None:
        return self.subject.operated_side

    @property
    def height_m(self) -> float | None:
        return self.subject.height_m

    @property
    def near_side_when_walking_plus_x(self) -> Side:
        """``cameras.A.near_side_when_walking_plus_x``, or :data:`DEFAULT_NEAR_SIDE_WHEN_WALKING_PLUS_X`.

        Used to translate a segmented pass's ``direction`` (ADR-0010, ``passes.yaml``) into
        Sports2D's ``visible_side`` (ADR-0010, ``openacl.session.process.run_backend``).
        """
        camera_a = self.cameras.get("A")
        value = (
            camera_a.get("near_side_when_walking_plus_x") if isinstance(camera_a, dict) else None
        )
        if isinstance(value, str) and value.strip().upper() in ("L", "R"):
            return value.strip().upper()  # type: ignore[return-value]
        return DEFAULT_NEAR_SIDE_WHEN_WALKING_PLUS_X

    def camera_fps(self, camera: str = "A") -> float | None:
        """Nominal frame rate the protocol says camera ``camera`` was set to."""
        entry = self.cameras.get(camera) or {}
        value = entry.get("fps")
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def camera_distance_m(self, camera: str = "A") -> float | None:
        """``cameras.<camera>.distance_m`` (``docs/PROTOKOLL-AUFNAHME.md``), or ``None``.

        Fed into Sports2D's ``px_to_meters_conversion.perspective_value`` (its own
        camera-to-person distance perspective correction, default 10 m) so it does not silently
        use that default for a 4.5-5 m setup.
        """
        entry = self.cameras.get(camera) or {}
        value = entry.get("distance_m")
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def as_dict(self) -> dict[str, Any]:
        return {
            **{name: getattr(self, name) for name in SCALAR_META_FIELDS},
            "subject": self.subject.as_dict(),
            "cameras": self.cameras,
        }


@dataclass(frozen=True)
class PassFile:
    """One walking pass: its name, its camera and (when present) its video file."""

    name: str
    """Stem of the video, e.g. ``"A_pass01"``; also the name of the derived sub-folder."""
    camera: str
    """``"A"``, ``"B"``, ... taken from the file name prefix."""
    number: int
    video: Path | None
    """``None`` for a pass that only exists as a cached ``derived/<name>/kinematics.npz``."""

    @property
    def has_video(self) -> bool:
        return self.video is not None


@dataclass(frozen=True)
class Session:
    """A session folder with its metadata and its discovered passes."""

    root: Path
    meta: SessionMeta
    passes_a: tuple[PassFile, ...]
    """Camera-A passes, sorted by name; these are the ones that get processed."""
    passes_b: tuple[PassFile, ...]
    """Camera-B (and any other camera) passes, listed for the report only."""
    warnings: tuple[str, ...] = ()

    @property
    def derived_dir(self) -> Path:
        return self.root / DERIVED_DIRNAME

    def pass_dir(self, pass_file: PassFile) -> Path:
        return self.derived_dir / pass_file.name

    def kinematics_path(self, pass_file: PassFile) -> Path:
        """Path *without* suffix; ``KinematicsResult.save`` appends ``.npz`` / ``.json``."""
        return self.pass_dir(pass_file) / KINEMATICS_STEM

    @property
    def data_dir(self) -> Path | None:
        """The ``data/`` folder two levels above the session, if the layout matches ADR-0009."""
        parent = self.root.parent
        if parent.name == "sessions":
            return parent.parent
        return None


def _coerce_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_subject(raw: Any, warnings: list[str]) -> SessionSubject:
    if raw is None:
        warnings.append(
            "meta.yaml has no 'subject' block; without subject.height_m no metric scale "
            "(step length, speed, Froude speed class) and without subject.operated_side no "
            "operated-vs-contralateral labelling is possible"
        )
        return SessionSubject()
    if not isinstance(raw, dict):
        warnings.append(f"meta.yaml 'subject' is a {type(raw).__name__}, expected a mapping")
        return SessionSubject()

    known = {"height_m", "mass_kg", "operated_side", "surgery_date", "graft"}
    height_m = _coerce_number(raw.get("height_m"))
    if raw.get("height_m") is not None and height_m is None:
        warnings.append(f"subject.height_m is not a number: {raw.get('height_m')!r}")
    if height_m is not None and not (1.0 <= height_m <= 2.3):
        warnings.append(
            f"subject.height_m = {height_m} is outside 1.0-2.3 m; is it given in metres?"
        )
        height_m = None
    if height_m is None:
        warnings.append(
            "subject.height_m is missing: keypoints stay in pixels, so step length and "
            "walking speed cannot be computed and the norm band falls back to 'comfortable'"
        )

    side_raw = raw.get("operated_side")
    operated_side: Side | None = None
    if isinstance(side_raw, str) and side_raw.strip().upper() in ("L", "R"):
        operated_side = side_raw.strip().upper()  # type: ignore[assignment]
    elif side_raw is not None:
        warnings.append(f"subject.operated_side must be 'L' or 'R', got {side_raw!r}")
    if operated_side is None:
        warnings.append(
            "subject.operated_side is missing; symmetry is reported without an "
            "operated/contralateral label"
        )

    surgery_date = raw.get("surgery_date")
    return SessionSubject(
        height_m=height_m,
        mass_kg=_coerce_number(raw.get("mass_kg")),
        operated_side=operated_side,
        surgery_date=str(surgery_date) if surgery_date is not None else None,
        graft=str(raw["graft"]) if raw.get("graft") is not None else None,
        extra={k: v for k, v in raw.items() if k not in known},
    )


def parse_meta(raw: dict[str, Any] | None) -> SessionMeta:
    """Turn the parsed YAML mapping into a :class:`SessionMeta`, collecting warnings."""
    warnings: list[str] = []
    if raw is None:
        raw = {}
        warnings.append("meta.yaml is empty")
    if not isinstance(raw, dict):
        warnings.append(f"meta.yaml is a {type(raw).__name__}, expected a mapping; ignored")
        raw = {}

    values: dict[str, Any] = {}
    for name, expected in SCALAR_META_FIELDS.items():
        value = raw.get(name)
        if value is None:
            if name not in ("notes", "activity_yesterday"):
                warnings.append(f"meta.yaml field {name!r} is missing")
            values[name] = None
            continue
        if expected in ((int, float),):
            number = _coerce_number(value)
            if number is None:
                warnings.append(f"meta.yaml field {name!r} is not a number: {value!r}")
            values[name] = number
        else:
            values[name] = str(value)

    cameras_raw = raw.get("cameras")
    cameras: dict[str, dict[str, Any]] = {}
    if isinstance(cameras_raw, dict):
        for key, entry in cameras_raw.items():
            cameras[str(key)] = dict(entry) if isinstance(entry, dict) else {"value": entry}
    elif cameras_raw is not None:
        warnings.append("meta.yaml 'cameras' is not a mapping; ignored")

    subject = _parse_subject(raw.get("subject"), warnings)
    return SessionMeta(
        **values,
        subject=subject,
        cameras=cameras,
        raw=dict(raw),
        warnings=tuple(warnings),
    )


def _warn_if_near_side_config_missing(meta: SessionMeta, session_dir: Path) -> SessionMeta:
    """Append a warning when a ``passes.yaml`` exists but the near-side config does not (ADR-0010).

    Segmented passes (``openacl segment``) need ``cameras.A.near_side_when_walking_plus_x`` to
    turn each pass's walking direction into Sports2D's ``visible_side``; silently defaulting to
    :data:`DEFAULT_NEAR_SIDE_WHEN_WALKING_PLUS_X` without saying so would make a wrong camera
    setup fail quietly.
    """
    if not (session_dir / PASSES_FILENAME).exists():
        return meta
    camera_a = meta.cameras.get("A")
    configured = (
        camera_a.get("near_side_when_walking_plus_x") if isinstance(camera_a, dict) else None
    )
    if configured is not None:
        return meta
    warning = (
        f"{session_dir / PASSES_FILENAME} exists but meta.yaml has no "
        "cameras.A.near_side_when_walking_plus_x; defaulting to "
        f"{DEFAULT_NEAR_SIDE_WHEN_WALKING_PLUS_X!r} (ADR-0010). This is setup-dependent -- set "
        "it explicitly if camera A is not positioned like Anton's 2026-09-07 recording."
    )
    return replace(meta, warnings=meta.warnings + (warning,))


def read_meta(session_dir: Path | str) -> SessionMeta:
    """Read ``<session_dir>/meta.yaml``; a missing file yields an empty, warned-about meta."""
    path = Path(session_dir) / META_FILENAME
    if not path.exists():
        empty = parse_meta({})
        meta = SessionMeta(
            **{name: getattr(empty, name) for name in SCALAR_META_FIELDS},
            subject=empty.subject,
            cameras=empty.cameras,
            raw={},
            warnings=(f"no {META_FILENAME} in {path.parent}",) + empty.warnings,
        )
        return _warn_if_near_side_config_missing(meta, path.parent)
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        parsed = parse_meta({})
        meta = SessionMeta(
            **{name: getattr(parsed, name) for name in SCALAR_META_FIELDS},
            subject=parsed.subject,
            cameras=parsed.cameras,
            raw={},
            warnings=(f"{META_FILENAME} could not be parsed: {exc}",),
        )
        return _warn_if_near_side_config_missing(meta, path.parent)
    return _warn_if_near_side_config_missing(parse_meta(raw), path.parent)


def _pass_from_stem(stem: str, video: Path | None) -> PassFile | None:
    match = _PASS_PATTERN.match(stem)
    if match is None:
        return None
    return PassFile(
        name=stem,
        camera=match.group("camera").upper(),
        number=int(match.group("number")),
        video=video,
    )


def discover_passes(session_dir: Path | str) -> tuple[list[PassFile], list[str]]:
    """Find every ``<camera>_pass<NN>`` of a session, from videos and from cached results.

    Videos are matched case-insensitively against :data:`VIDEO_SUFFIXES`. A pass that has no
    video but already has ``derived/<name>/kinematics.npz`` is discovered too, so a session can
    be re-reported (or tested) without the raw footage.
    """
    root = Path(session_dir)
    warnings: list[str] = []
    found: dict[str, PassFile] = {}

    for entry in sorted(root.iterdir()) if root.exists() else []:
        if not entry.is_file() or entry.suffix.lower() not in VIDEO_SUFFIXES:
            continue
        pass_file = _pass_from_stem(entry.stem, entry)
        if pass_file is None:
            warnings.append(
                f"video {entry.name!r} does not follow the '<camera>_pass<NN>' naming of "
                "docs/PROTOKOLL-AUFNAHME.md and is ignored"
            )
            continue
        if pass_file.name in found:
            warnings.append(
                f"pass {pass_file.name!r} exists more than once (different container "
                f"suffixes); {found[pass_file.name].video} is used"
            )
            continue
        found[pass_file.name] = pass_file

    derived = root / DERIVED_DIRNAME
    if derived.is_dir():
        for entry in sorted(derived.iterdir()):
            if not entry.is_dir() or entry.name in found:
                continue
            if not (entry / f"{KINEMATICS_STEM}.npz").exists():
                continue
            pass_file = _pass_from_stem(entry.name, None)
            if pass_file is not None:
                found[pass_file.name] = pass_file

    return [found[name] for name in sorted(found)], warnings


def load_session(session_dir: Path | str) -> Session:
    """Load metadata and discover the passes of ``session_dir``.

    Raises
    ------
    FileNotFoundError
        If the directory does not exist.
    ValueError
        If no camera-A pass (video or cached result) can be found at all.
    """
    root = Path(session_dir).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"session directory not found: {root}")

    meta = read_meta(root)
    passes, warnings = discover_passes(root)
    passes_a = tuple(p for p in passes if p.camera == "A")
    passes_b = tuple(p for p in passes if p.camera != "A")

    if not passes_a:
        raise ValueError(
            f"no camera-A pass found in {root}. Expected files like 'A_pass01.mov' "
            f"(suffixes {', '.join(VIDEO_SUFFIXES)}) or cached "
            f"'{DERIVED_DIRNAME}/A_pass01/{KINEMATICS_STEM}.npz'."
        )
    if passes_b:
        warnings.append(
            f"{len(passes_b)} camera-B pass(es) found "
            f"({', '.join(p.name for p in passes_b)}); this layer only processes camera A "
            "(sagittal). Camera B is kept for a later multi-camera backend."
        )
    return Session(
        root=root,
        meta=meta,
        passes_a=passes_a,
        passes_b=passes_b,
        warnings=tuple(warnings),
    )


def read_pass_directions(session_dir: Path | str) -> dict[str, Literal["+x", "-x"]]:
    """Map pass name (e.g. ``"A_pass01"``) -> walking ``direction`` from ``passes.yaml``.

    Returns an empty mapping when there is no ``passes.yaml`` (a session recorded the old way,
    one video per pass) or it cannot be parsed.
    """
    path = Path(session_dir) / PASSES_FILENAME
    if not path.exists():
        return {}
    try:
        entries = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return {}
    if not isinstance(entries, list):
        return {}
    directions: dict[str, Literal["+x", "-x"]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        file_name = entry.get("file")
        direction = entry.get("direction")
        if not file_name or direction not in ("+x", "-x"):
            continue
        directions[Path(str(file_name)).stem] = direction
    return directions


def resolve_near_side_from_direction(
    direction: Literal["+x", "-x"], near_side_when_walking_plus_x: Side
) -> Side:
    """Translate a pass's walking ``direction`` into the camera-near side (ADR-0010).

    Empirical for a static sagittal camera: whichever side is camera-near while walking ``+x``
    is camera-far while walking ``-x``, and vice versa.
    """
    if direction == "+x":
        return near_side_when_walking_plus_x
    return "L" if near_side_when_walking_plus_x == "R" else "R"


PoolingMode = Literal["camera_near", "all_sides"]
