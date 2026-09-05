# Roadmap

Stand 2026-09-05. Eine Phase gilt als fertig, wenn ihre Definition of Done erfüllt ist. Anton entscheidet Phasenübergänge.

## Phase 0 – Persönliche Baseline (Woche 1–2)

Ziel: Erste eigene Aufnahmen, erste Fehlerabschätzung, Gefühl für die Daten. Noch kein Analyse-Code.

- [ ] Aufnahmeprotokoll festlegen und einmal durchspielen (`docs/PROTOKOLL-AUFNAHME.md`)
- [ ] Session 1: sagittale Aufnahme mit einem iPhone, 60 fps, beide Richtungen, plus zweites iPhone frontal-schräg
- [ ] Session 1 wiederholen am selben Tag nach 30 Minuten (Grundlage für den eigenen Messfehler)
- [ ] Sports2D über alle Videos laufen lassen, Winkelkurven ansehen
- [ ] OpenCap Web-App mit zwei iPhones einmal durchlaufen (Referenz mit 3D-Winkeln)
- [ ] OpenCap Monocular auf einer GCP-GPU-VM über dieselben Videos (Benchmark)
- [ ] Apple-Health-Export ziehen und Gangmetriken der letzten Monate anschauen
- [ ] Kraft-LSI und Hop-Test-Werte vom Physio erfragen
- [ ] Kurzes Fazit in `docs/phase0-ergebnis.md`: Wie groß ist der Unterschied zwischen den Backends, wie groß die Wiederholungsstreuung

Definition of Done: mindestens zwei Sessions verarbeitet, Backend-Vergleich dokumentiert, erster eigener MDC-Schätzwert für Knieflexion und Standphase.

## Phase 1 – Gait-Core (Monat 1–2)

Ziel: Video rein, Zahlen und Kurven raus, reproduzierbar, getestet.

- Datenmodell Session (mehrere Quellen pro Session, siehe ADR-0005)
- Normdatensätze laden, harmonisieren, Normbänder geschwindigkeitsnormiert (Froude)
- Gangereignisse (Zeni 2008), Zyklen, 0–100 % Normierung, Filterung
- Zeit-Weg-Parameter, Symmetrie-Indizes, Abweichungs-Score je Gelenk
- Unsicherheit: MDC pro Parameter, Flag nur oberhalb
- `sports2d`-Backend, CLI `openacl analyze <video>`
- Tests gegen die öffentlichen Datensätze (bekannte Antworten)

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
