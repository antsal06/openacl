# Roadmap

Stand 2026-09-05. Eine Phase gilt als fertig, wenn ihre Definition of Done erfüllt ist. Anton entscheidet Phasenübergänge.

## Phase 0 – Persönliche Baseline (Woche 1–2)

Ziel: Erste eigene Aufnahmen, erste Fehlerabschätzung, Gefühl für die Daten. Noch kein Analyse-Code.

- [x] Aufnahmeprotokoll festlegen (`docs/PROTOKOLL-AUFNAHME.md`), Schritt-für-Schritt-Checkliste in `docs/phase0-anleitung.md`
- [ ] Protokoll einmal durchspielen
- [ ] Session 1: sagittale Aufnahme mit einem iPhone, 60 fps, beide Richtungen, plus zweites iPhone frontal-schräg
- [ ] Session 1 wiederholen am selben Tag nach 30 Minuten (Grundlage für den eigenen Messfehler)
- [ ] Sports2D über alle Videos laufen lassen, Winkelkurven ansehen
- [ ] OpenCap Web-App mit zwei iPhones einmal durchlaufen (Referenz mit 3D-Winkeln)
- [ ] OpenCap Monocular über dieselben Videos (Benchmark): zuerst die gehostete Beta auf opencap.ai probieren, GPU-VM nur als Fallback (`research/opencap-monocular/SETUP.md`)
- [ ] Apple-Health-Export ziehen und Gangmetriken der letzten Monate anschauen
- [ ] Kraft-LSI und Hop-Test-Werte vom Physio erfragen
- [ ] Kurzes Fazit in `docs/phase0-ergebnis.md`: Wie groß ist der Unterschied zwischen den Backends, wie groß die Wiederholungsstreuung

Definition of Done: mindestens zwei Sessions verarbeitet, Backend-Vergleich dokumentiert, erster eigener MDC-Schätzwert für Knieflexion und Standphase.

## Phase 1 – Gait-Core (Monat 1–2)

Ziel: Video rein, Zahlen und Kurven raus, reproduzierbar, getestet.

Stand 2026-09-05 (erste Bauwelle, vor Antons erster Aufnahme vorgezogen, weil ohne Video testbar):

- [ ] Datenmodell Session (mehrere Quellen pro Session, siehe ADR-0005); mehrere Durchgänge je Session bündeln, dort auch MDC aus Wiederholungen
- [x] Normdatensätze laden, harmonisieren, Normbänder geschwindigkeitsnormiert (Froude): Fukuchi 2018 (CC BY 4.0, n=42, 3 Froude-Klassen) und Van Criekinge 2023 (CC0, n=138) in `src/openacl/norm/data/normbands_v1.parquet`; Schreiber 2019 Loader fehlt noch
- [x] Gangereignisse (Zeni 2008), Zyklen, 0–100 % Normierung, Filterung (`openacl.core`)
- [x] Zeit-Weg-Parameter, Symmetrie-Indizes (Robinson SI, Plotnik GA), Abweichungs-Score je Gelenk (GVS/GPS nach Baker 2009)
- [x] Unsicherheit: MDC-Rechnung (ICC(2,1), SEM, MDC95) und Literatur-Platzhalter; eigene Werte fehlen bis Wiederholungsmessung
- [x] `sports2d`-Backend, CLI `openacl analyze <video>` (getestet mit Sports2D-Demovideo auf dem M2: lightweight 1,3× Echtzeit, balanced 4×)
- [x] Tests: 131 (synthetischer Gang mit bekannten Antworten, Parser-Fixtures, Normband-Format)
- [ ] Test gegen echte Markerdaten (Fukuchi-Zyklen als `KinematicsResult` durch Gait-Core, Standphase und Peaks müssen mit den publizierten Werten übereinstimmen)
- [ ] Sub-Frame-Genauigkeit der Toe-Off-Erkennung (aktuell ~1 Frame zu früh, ca. 1 % Standphase)
- [ ] Pixel-zu-Meter-Skalierung für Schrittlänge und Geschwindigkeit (Körpergröße oder Referenzmaß), dann automatische Froude-Klasse
- [ ] Apple-Health-Export-Loader (ADR-0005)

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
