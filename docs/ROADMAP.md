# Roadmap

Stand 2026-09-12. Eine Phase gilt als fertig, wenn ihre Definition of Done erfüllt ist. Anton entscheidet Phasenübergänge.

## Phase 0 – Persönliche Baseline (Woche 1–2)

Ziel: Erste eigene Aufnahmen, erste Fehlerabschätzung, Gefühl für die Daten. Noch kein Analyse-Code.

- [x] Aufnahmeprotokoll festlegen (`docs/PROTOKOLL-AUFNAHME.md`), Schritt-für-Schritt-Checkliste in `docs/phase0-anleitung.md`
- [x] Protokoll einmal durchspielen (2026-09-07, Turnhalle)
- [x] Session 1: sagittale Aufnahme mit einem iPhone, 60 fps, beide Richtungen, plus zweites iPhone frontal-schräg (2026-09-07; 45°-Videos noch unausgewertet)
- [x] Session 1 wiederholen am selben Tag nach 30 Minuten (Grundlage für den eigenen Messfehler): `data/subject/mdc.yaml`, 18 Kennzahlen
- [x] Sports2D über alle Videos laufen lassen, Winkelkurven ansehen (42 Durchgänge, 84 Zyklen, 2026-09-11)
- [x] OpenCap Web-App mit zwei iPhones einmal durchlaufen (Referenz mit 3D-Winkeln): 2 Gehtrials, 3 Sprung-/Lauftrials
- [ ] OpenCap Monocular über dieselben Videos (Benchmark): zuerst die gehostete Beta auf opencap.ai probieren, GPU-VM nur als Fallback (`research/opencap-monocular/SETUP.md`). Zurückgestellt: die Zwei-Kamera-Variante hat die Referenzfrage beantwortet
- [x] Apple-Health-Export ziehen und Gangmetriken der letzten Monate anschauen (Export 2026-09-05, Verlauf ab Juli 2024)
- [x] Kraft-LSI vom Mai liegt vor (`data/baseline/strength.yaml`, privat); Hop-Tests fehlen
- [x] Kurzes Fazit in `docs/phase0-ergebnis.md`: Backend-Vergleich, Wiederholungsstreuung, Artefakte

Definition of Done: mindestens zwei Sessions verarbeitet, Backend-Vergleich dokumentiert, erster eigener MDC-Schätzwert für Knieflexion und Standphase. **Erfüllt 2026-09-11** (vier Sessions, `docs/phase0-ergebnis.md`, `data/subject/mdc.yaml`).

## Phase 1 – Gait-Core (Monat 1–2)

Ziel: Video rein, Zahlen und Kurven raus, reproduzierbar, getestet.

Stand 2026-09-05 (erste Bauwelle, vor Antons erster Aufnahme vorgezogen, weil ohne Video testbar):

- [x] Datenmodell Session (ADR-0009): Ordner je Session und Bedingung, Durchgänge gebündelt, MDC aus Wiederholungen (`openacl compare`)
- [x] Normdatensätze laden, harmonisieren, Normbänder geschwindigkeitsnormiert (Froude): Fukuchi 2018 (CC BY 4.0, n=42, 3 Froude-Klassen) und Van Criekinge 2023 (CC0, n=138) in `src/openacl/norm/data/normbands_v1.parquet`; Schreiber 2019 Loader fehlt noch
- [x] Gangereignisse (Zeni 2008), Zyklen, 0–100 % Normierung, Filterung (`openacl.core`)
- [x] Zeit-Weg-Parameter, Symmetrie-Indizes (Robinson SI, Plotnik GA), Abweichungs-Score je Gelenk (GVS/GPS nach Baker 2009)
- [x] Unsicherheit: MDC-Rechnung (ICC(2,1), SEM, MDC95) und Literatur-Platzhalter; eigene Werte fehlen bis Wiederholungsmessung
- [x] `sports2d`-Backend, CLI `openacl analyze <video>` (getestet mit Sports2D-Demovideo auf dem M2: lightweight 1,3× Echtzeit, balanced 4×)
- [x] Tests: 131 (synthetischer Gang mit bekannten Antworten, Parser-Fixtures, Normband-Format)
- [x] Test gegen echte Markerdaten: 12 Fukuchi-Probanden × 3 Geschwindigkeiten gegen Kraftmessplatten (`docs/validation/core_vs_fukuchi.md`). Geschwindigkeit Bias −0,02 m/s, Kadenz −0,3/min, Peak Knie +1,4°. **Standphase +5,5 ± 1,3 Prozentpunkte** (Heel Strike 37 ms zu früh, Toe Off 19 ms zu spät). Als `KNOWN_STANCE_BIAS_PCT` dokumentiert und als Warnung ausgegeben; Symmetrie ist davon unberührt
- [ ] Ausreißerregel auf Session-Ebene über die gepoolten Stride-Dauern (ein falscher Fersenkontakt in 42 Durchgängen blieb unentdeckt, `docs/phase0-ergebnis.md`)
- [ ] Ereigniserkennung verbessern: Fersen-Vorwärtsgeschwindigkeit unter Schwelle für Heel Strike, Zehen-Geschwindigkeit über Schwelle für Toe Off (Zeni-Methode 2), Ziel Standphasen-Bias < 2 Prozentpunkte, Nachweis mit `scripts/validate_core_fukuchi.py`
- [x] Pixel-zu-Meter-Skalierung über `subject.height_m` (Sports2D), automatische Froude-Klasse in `openacl session`; Klasse pro Person fixieren (`--speed-class`), siehe `docs/phase0-ergebnis.md`
- [x] Apple-Health-Export-Loader (`python -m openacl.health`, Streaming-Parser, Tages-/Wochenmediane, Perioden vor/nach OP, Plot)
- [x] Session-Schicht nach ADR-0009: `openacl session`, `openacl compare`, Report
- [x] Pass-Segmentierung nach ADR-0010: `openacl segment` (Langvideo → Durchgänge), 180°-Unwrap für Knie- und Sprunggelenkwinkel nach falschem Sichtseiten-Flip, Richtung aus `passes.yaml` → Sports2D `visible_side`, `cameras.A.distance_m` → Sports2D-Perspektivkorrektur
- [x] OpenCap-Backend nach ADR-0011: `openacl.backends.opencap`, Clipping-Erkennung pro Kanal, Frontalebenen-Kanäle (`pelvis_list_deg`, `hip_adduction_deg`, `hip_rotation_deg`)

## Phase 2 – Interpretation und Report (Monat 2–3)

- Wissensbasis aus `docs/research/02` als Regeln mit Quelle, Evidenzgrad, Schwellwert
- Report für Physio (Markdown und PDF): Kurven, Tabellen, Beobachtungen, offene Fragen
- Verlaufsansicht über Sessions mit Konfidenzband
- LLM nur als Schreiber über den deterministischen Befunden
- Erste Runde mit Antons Physio

## Phase 3 – Web-App und Cloud (Monat 3–5)

- `pose2sim`-Backend für zwei iPhones, GPU auf Cloud Run
- Upload vom Handy, Mehrbenutzer, Auth
- Open-Source-Release mit Beispieldaten und Doku

## Phase 4 – Validierung, Sensoren, Daten (ab Monat 5, optional)

- Kooperation mit Physio-Praxis oder Uni-Ganglabor, Vergleich gegen Marker-System
- CoreMotion-Backend, EMG-Experiment (ADR-0005)
- Unüberwachter Abweichungs-Score mit ML, eventuell Paper
