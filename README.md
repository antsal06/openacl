# OpenACL

Ganganalyse aus Handy-Video für die Reha nach Kreuzband-Rekonstruktion (ACLR).
Misst Gelenkwinkel und Gangparameter, vergleicht mit Normbändern und der Gegenseite,
zeigt den Verlauf über Wochen und erklärt Auffälligkeiten mit Quelle.

**Status:** Phase 0/1. Die Kette Video → Kinematik → Gangparameter → Normvergleich läuft
lokal auf CPU, ist aber noch nicht an echten Aufnahmen validiert. Kein nutzbares Tool für Dritte.

## Was OpenACL ist und nicht ist

- Es ist ein Werkzeug zur Selbstbeobachtung und zur Vorbereitung von Physio-Terminen.
- Es stellt keine Diagnose und gibt keine Therapieempfehlung. Es ist kein Medizinprodukt.
- Es misst Kinematik (Winkel, Zeiten, Längen). Kräfte, Gelenkmomente und Muskelaktivierung
  sieht keine Kamera. Ein unauffälliger Befund heißt nicht, dass alles in Ordnung ist.

## Aufbau

```
Video ─► [2] Kinematik-Engine ─► [3] Gait-Core ─► [4] Interpretation ─► [5] Report / App
            (austauschbar)         (Normband, Symmetrie,   (Regeln mit Quelle,
                                    Verlauf, Unsicherheit)   LLM nur als Schreiber)
```

Details: `docs/00-SYNTHESE.md`. Entscheidungen: `docs/DECISIONS.md`. Roadmap: `docs/ROADMAP.md`.
Recherche mit Quellen: `docs/research/`.

## Schnellstart

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -e ".[dev,norm,sports2d]"
.venv/bin/pytest -q
.venv/bin/openacl probe   video.mov
.venv/bin/openacl analyze video.mov --mode balanced --operated-side L --out out/session1
```

`analyze` schreibt `kinematics.npz/.json` (Schema in `src/openacl/schema.py`), `angles.png` und druckt
Zyklenzahl, Warnungen und den Gait Profile Score gegen das mitgelieferte Normband
(`src/openacl/norm/README.md`). Aufnahmeprotokoll: `docs/PROTOKOLL-AUFNAHME.md`,
Checkliste für die erste Session: `docs/phase0-anleitung.md`.

Normbänder neu bauen (lädt ca. 1 GB nach `data/norm/`):

```bash
.venv/bin/python scripts/download_normdata.py --dataset fukuchi2018
.venv/bin/python scripts/build_normbands.py
```

## Lizenz

Apache 2.0. Der Produktionspfad nutzt ausschließlich permissiv lizenzierte Komponenten
(RTMPose, Sports2D, Pose2Sim, OpenSim). SMPL-basierte Modelle werden nur privat und
zum Benchmarken verwendet, nie im veröffentlichten Verarbeitungspfad.
