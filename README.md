# OpenACL

Ganganalyse aus Handy-Video für die Reha nach Kreuzband-Rekonstruktion (ACLR).
Misst Gelenkwinkel und Gangparameter, vergleicht mit Normbändern und der Gegenseite,
zeigt den Verlauf über Wochen und erklärt Auffälligkeiten mit Quelle.

**Status:** Phase 0, persönliche Baseline. Noch kein nutzbares Tool.

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

## Schnellstart (Phase 0)

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python sports2d
# Aufnahmeprotokoll: docs/PROTOKOLL-AUFNAHME.md
```

## Lizenz

Apache 2.0. Der Produktionspfad nutzt ausschließlich permissiv lizenzierte Komponenten
(RTMPose, Sports2D, Pose2Sim, OpenSim). SMPL-basierte Modelle werden nur privat und
zum Benchmarken verwendet, nie im veröffentlichten Verarbeitungspfad.
