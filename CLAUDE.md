# OpenACL – Arbeitsregeln für Claude

## Projekt
Ganganalyse aus Handy-Video für ACLR-Reha. Schichten: Aufnahme → Kinematik-Engine (Backends) → Gait-Core → Interpretation → Report/App. Lies `docs/00-SYNTHESE.md` und `docs/DECISIONS.md` vor Architekturarbeit. Anton gestaltet die Architektur aktiv mit: größere Strukturentscheidungen erst als ADR in `docs/DECISIONS.md` vorschlagen, dann bauen.

## Konventionen
- Sprache: Doku und Kommunikation Deutsch, Code und Bezeichner Englisch, Docstrings Englisch.
- Python ≥ 3.12, `uv` für Umgebung und Abhängigkeiten, `src/openacl/` Layout, `pytest`, `ruff`.
- Keine Videos, Rohdaten, Keys oder Konfig mit Secrets ins Repo. `data/` ist ignoriert. Das Repo wird public.
- Lizenz Apache 2.0. Keine Abhängigkeit im Produktionspfad, die SMPL/SMPL-X, OpenPose, Sapiens, GVHMR, EasyMocap oder AGPL-Komponenten braucht. SMPL-basierte Tools (OpenCap Monocular, WHAM) nur in `research/` und lokal.
- Formulierungen in Reports und UI nie diagnostisch oder therapeutisch („Beobachtung“, „Hypothese zur Besprechung“, nie „du hast“, „mach Übung“). Grund: MDR Regel 11.
- Jede Regel in der Interpretationsschicht trägt Quelle, Evidenzgrad und Schwellwert relativ zum Messfehler (MDC). Nichts flaggen, was unter dem MDC liegt.
- Jede Zahl im Gait-Core hat eine Einheit im Namen oder im Typ (`knee_flexion_deg`, `stance_pct`).

## Kontext zu Anton (für Interpretation und Tests)
Vorderes Kreuzband, Semitendinosus-Gracilis-Transplantat (STG/Hamstring), OP ca. März 2026. Mehrere iPhones verfügbar. Ziel zuerst persönliche Baseline, dann Open Source.

- Trenne Beobachtung und Schlussfolgerung. Erst was konkret im Code
  steht (mit Datei:Zeile), dann die Interpretation, sichtbar getrennt.
- Kennzeichne die Quelle jeder Aussage über das Verhalten des Codes:
  [ausgeführt] / [gelesen] / [vermutet]. Ohne Ausnahme.
- Nenne bei jeder Diagnose entweder eine zweite plausible Ursache
  oder sag explizit, dass du keine siehst.
- Nenne bei jeder Diagnose, wie ich sie selbst in 30 Sekunden
  überprüfen kann.
- Sag, was du NICHT angeschaut hast, bevor du ein Fazit ziehst.
- "Ich weiß es nicht" ist eine vollständige und akzeptable Antwort.
  Rate nicht, um hilfreich zu wirken.
- Verboten: "ehrlich gesagt", "um ehrlich zu sein", "das muss ich
  zugeben", "in der Tat", "genau das ist der Punkt".
- Keine Zusammenfassung am Ende, wenn die Antwort unter 20 Zeilen ist.