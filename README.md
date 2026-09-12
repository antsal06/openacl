# OpenACL

Ganganalyse aus Handy-Video für die Reha nach Kreuzband-Rekonstruktion (ACLR).
Misst Gelenkwinkel und Gangparameter, vergleicht mit Normbändern und der Gegenseite,
zeigt den Verlauf über Wochen und erklärt Auffälligkeiten mit Quelle.

**Status (2026-09-12):** Phase 0 abgeschlossen, Phase 1 weitgehend. Die Kette Langvideo →
Segmentierung → Sports2D → Gait-Core → Normband, Symmetrie, eigener Messfehler → Report läuft
lokal auf CPU und wurde an einer echten Session ausgewertet (42 Durchgänge, 84 Zyklen, vier
Bedingungen, Test-Retest, OpenCap-3D als Referenz; Lehren in `docs/phase0-ergebnis.md`). Die
Interpretationsschicht (Regeln mit Quelle und Evidenzgrad) fehlt noch. Für Dritte nutzbar mit
Python-Kenntnissen und dem Aufnahmeprotokoll; keine App, kein Support.

## Was OpenACL ist und nicht ist

- Es ist ein Werkzeug zur Selbstbeobachtung und zur Vorbereitung von Physio-Terminen.
- Es stellt keine Diagnose und gibt keine Therapieempfehlung. Es ist kein Medizinprodukt.
- Es misst Kinematik (Winkel, Zeiten, Längen). Kräfte, Gelenkmomente und Muskelaktivierung
  sieht keine Kamera. Ein unauffälliger Befund heißt nicht, dass alles in Ordnung ist.

## Grenzen, die wir kennen

- Eine Seitenkamera koppelt die kameranahe Seite an die Gehrichtung. Jede richtungsabhängige
  Verzerrung sieht aus wie ein Seitenunterschied. Sprunggelenkwinkel sind damit in diesem Aufbau
  nicht interpretierbar, Kniewinkel nur mit Vorsicht (`docs/phase0-ergebnis.md`).
- Die Normbänder stammen aus Marker-Laborsystemen. Die 2D-Videomessung liest die Standphase des
  Knies um einige Grad gebeugter; der Seitenvergleich ist davon frei, der Normvergleich nicht.
- Der eigene Messfehler aus einer Wiederholung am selben Tag ist die Untergrenze; zwischen Tagen
  ist er größer. Beide Werte stehen im Report.
- Fünf Meter Messbereich liefern zwei Zyklen je Seite und Durchgang. Zwanzig Durchgänge sind
  das Minimum für einen Mittelwert, dem man trauen kann.

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

## Eine ganze Session: Langvideo → Segmentierung → Session → Vergleich

Die Kamera läuft während einer Bedingung durch (10 bis 20 Durchgänge hin und her,
`docs/PROTOKOLL-AUFNAHME.md`), `openacl segment` schneidet daraus die einzelnen Durchgänge
(ADR-0010), `openacl session` verarbeitet die Session (ADR-0009), `openacl compare` vergleicht
zwei Sessions (z. B. Test-Retest) und schreibt den eigenen MDC95.

```bash
# 1. Langvideo einer Bedingung in Durchgänge schneiden; --dry-run zeigt nur die Erkennung
.venv/bin/openacl segment A_socken.mov --out data/sessions/2026-09-11_socken \
    --meta data/sessions/2026-09-11_socken_quelle/meta.yaml --condition socken

# 2. Session verarbeiten (Sports2D je Durchgang, Gait-Core, gepoolte Kennzahlen, Report)
.venv/bin/openacl session data/sessions/2026-09-11_socken

# 3. Zwei Sessions vergleichen (z. B. Wiederholung am selben Tag -> eigener MDC95)
.venv/bin/openacl compare data/sessions/2026-09-11_socken data/sessions/2026-09-11_socken-2
```

`openacl segment` erkennt Durchgänge ohne Pose-Modell aus der Bewegung (Vordergrundfläche und
Schwerpunkt-Drift gegen einen Median-Hintergrund) und schreibt `A_pass<NN>.mp4` plus
`passes.yaml` (Zeitfenster, Richtung, Drift). `openacl session` übersetzt die Richtung jedes
Durchgangs über `meta.yaml` `cameras.A.near_side_when_walking_plus_x` in Sports2Ds
`visible_side`, statt sich auf dessen Pro-Video-Heuristik zu verlassen (die bei einem Video mit
beiden Gehrichtungen falsch liegt). Details und Schwellwerte: ADR-0010, ADR-0011 in
`docs/DECISIONS.md`.

## Lizenz

Apache 2.0. Der Produktionspfad nutzt ausschließlich permissiv lizenzierte Komponenten
(RTMPose, Sports2D, Pose2Sim, OpenSim). SMPL-basierte Modelle werden nur privat und
zum Benchmarken verwendet, nie im veröffentlichten Verarbeitungspfad.
