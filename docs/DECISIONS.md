# Entscheidungen (ADR-Log)

Format: Kontext, Entscheidung, Konsequenzen. Status `vorgeschlagen` heißt: Anton hat noch nicht zugestimmt.

---

## ADR-0001 Name und Lizenz
Status: angenommen 2026-09-05

**Kontext.** Projektname gesucht, Open Source geplant.
**Entscheidung.** Name `OpenACL`, Lizenz Apache 2.0, GitHub public unter `antsal06/openacl`, PyPI-Name `openacl` (frei, Stand 2026-09-05).
**Konsequenzen.** „ACL“ heißt in der IT auch Access Control List. Im Medizinkontext ist der Name eindeutig, in GitHub-Suchen konkurriert er mit Zugriffskontroll-Repos. Untertitel im README hält den Kontext klar. `OpenGait` war keine Option, das ist ein bestehendes Gait-Recognition-Projekt mit über 1000 Sternen.

## ADR-0002 Kinematik-Engine als austauschbares Backend, permissiver Produktionspfad
Status: angenommen 2026-09-05

**Kontext.** Die genauesten Monokular-3D-Methoden (WHAM, TRAM, OpenCap Monocular) laden das SMPL-Körpermodell, dessen Lizenz kommerzielle Nutzung verbietet. OpenPose schließt Sport aus. Anton will erst ein Werkzeug für sich, dann Open Source für Physios.
**Entscheidung.** Schicht 2 definiert ein gemeinsames Ausgabeschema (Zeitreihen je Gelenk und Seite, Fuß-Keypoints, Konfidenz je Frame, Metadaten). Backends:
- `sports2d`: 1 Handy sagittal, RTMPose, 2D-Winkel. Produktionspfad, CPU-fähig.
- `pose2sim`: 2 Handys, Triangulation, OpenSim IK. Produktionspfad, GPU sinnvoll.
- `opencap_mono`: 1 Handy, 3D und Kinetikschätzung. Nur `research/`, privat und als Benchmark.
**Konsequenzen.** Gait-Core und Interpretation sind backend-unabhängig. Wir können Genauigkeit der Backends gegeneinander messen, bevor wir uns festlegen.

## ADR-0003 Vergleichslogik: Normband + Gegenseite + Verlauf, kein „Ideal“, kein ACLR-Klassifikator
Status: angenommen 2026-09-05

**Kontext.** Gesunde streuen beim Knie um ±15°, dreimal mehr zwischen Personen als innerhalb. Nach ACLR kompensiert die Gegenseite. Öffentliche ACL-Gangdaten reichen nicht für einen Klassifikator.
**Entscheidung.** Drei Referenzen gleichzeitig: geschwindigkeitsnormiertes Normband (Fukuchi 2018, Schreiber/Moissenet 2019, Van Criekinge 2023), Seitenvergleich mit Warnhinweis, eigener Verlauf. Abweichung als Score nach Gait-Profile-Score-Logik. Jedes Flag nur oberhalb des Messfehlers (MDC), der aus eigenen Wiederholungsmessungen bestimmt wird.
**Konsequenzen.** Kein binärer „ACLR erkannt“-Output. ML frühestens in Phase 4 und nur als unüberwachter Abweichungs-Score.

## ADR-0004 Keine diagnostische Sprache
Status: angenommen 2026-09-05

**Kontext.** EU MDR Regel 11: Software, die Diagnose oder Therapie unterstützt, ist mindestens Klasse IIa.
**Entscheidung.** Alle Ausgaben sind Beobachtungen und Hypothesen zur Besprechung mit Fachpersonal, mit Quelle. Ein LLM darf Reports formulieren, aber nur über deterministisch berechneten Befunden, und muss die Zahlen zeigen.
**Konsequenzen.** Wortlisten und Review der Report-Templates gehören zur Definition of Done in Phase 2.

## ADR-0005 Sensor-Track als eigene, spätere Schiene
Status: vorgeschlagen 2026-09-05

**Kontext.** Anton fragt nach iPhone-Sensoren, Rhythmus, Elektroden. Die Recherche zeigt: was sich nach ACLR „falsch anfühlt“, ist überwiegend neuromuskulär (arthrogene Muskelinhibition, Aktivierung), also unsichtbar für Video, aber teilweise sichtbar für EMG.
**Entscheidung (Vorschlag).**
- Phase 1 nimmt Apple-Health-Gangmetriken (Gehasymmetrie, Doppelstützzeit, Schrittlänge, Gehgeschwindigkeit) über den Health-Export als zweite Datenquelle in den Session-Speicher. Kostet nichts, das iPhone misst sie ohnehin täglich. Genauigkeit ist mäßig (Doppelstütz ICC 0,4 bis 0,6), als Trend brauchbar.
- CoreMotion-Rohdaten (iPhone in der Hosentasche) als eigenes Backend erst, wenn Gait-Core steht. Das wäre der OneStep-Ansatz, selbst gebaut.
- Oberflächen-EMG (Vastus medialis, Hamstrings, Seitenvergleich beim Gehen) als Phase-4-Experiment mit günstiger Hardware. Genau die Größe, die den Unterschied zwischen „sieht normal aus“ und „fühlt sich falsch an“ erklären könnte. Hardware und Validierung sind ein eigenes Projekt, deshalb erst später.
**Konsequenzen.** Session-Datenmodell muss von Anfang an mehrere Quellen pro Session erlauben (Video, Health-Export, später IMU, EMG).

## ADR-0006 GCP: eigenes Projekt, Region Europa, Cloud Run mit GPU, Skalierung auf null
Status: angenommen 2026-09-05 (Projekt `openacl1` von Anton angelegt, Billing verknüpft, APIs aktiviert)

**Kontext.** Viel GCP-Guthaben, sporadische Analysejobs, keine 24/7-Last. Aktuelle gcloud-Default-Konfig zeigt auf `pace-mcp`, das ist ein anderes Projekt.
**Entscheidung.** Projekt `openacl1` (Projektnummer 748303749622), Region `europe-west4` (Niederlande, Cloud-Run-GPU L4 verfügbar; `europe-west1` als Alternative). Phase 1 und 2 laufen lokal, GCP wird erst in Phase 3 für die Web-App und für GPU-Backends gebraucht. Ausnahme: OpenCap Monocular in Phase 0 auf einer Compute-Engine-VM mit einer L4 oder T4, weil das auf dem M2 ohne CUDA nicht sinnvoll läuft.
**Konsequenzen.** Setup-Anleitung in `infra/GCP-SETUP.md`. Kein Service-Account-Key im Repo, lokal über `gcloud auth application-default login`.

## ADR-0007 Gemeinsames Kinematik-Schema und Paketstruktur
Status: angenommen 2026-09-05

**Kontext.** ADR-0002 verlangt austauschbare Backends. Damit Gait-Core und Interpretation backend-unabhängig testbar sind, braucht es einen festen Vertrag zwischen Schicht 2 und 3, bevor Code entsteht.
**Entscheidung.** `src/openacl/schema.py` definiert `KinematicsResult`: Zeitachse `time_s`, Winkelkanäle `angles_deg` mit kanonischen Namen (`knee_flexion_deg_L`, `hip_flexion_deg_R`, ...), Keypoints (`heel_L`, `big_toe_R`, ...) in px (2D) oder m (3D), Konfidenz je Keypoint, Gehrichtung, kameranahe Seite, Provenienz-Metadaten. NaN für fehlende Werte, keine Interpolation im Backend. Klinische Vorzeichen: Knieflexion, Hüftflexion, Dorsalextension positiv. Persistenz als `.npz` + `.json` ohne Pickle.
Paketstruktur: `openacl.backends` (Adapter → `KinematicsResult`), `openacl.core` (Filter, Events, Zyklen, Parameter, Symmetrie, Normvergleich, MDC; importiert nie ein Backend), `openacl.norm` (Normdaten-Loader und -Bänder), `openacl.interpret` (Regeln, Report), `openacl.cli`.
**Konsequenzen.** Jedes Backend ist ein Adapter von ca. 100 Zeilen. Gait-Core-Tests laufen mit synthetischen `KinematicsResult`-Objekten und mit den Marker-Datensätzen, ganz ohne Video. Wenn später ein 3D-Backend Frontalebenen-Winkel liefert, kommen neue kanonische Kanäle dazu (`hip_adduction_deg`), das Schema bleibt.

## ADR-0008 Normdaten: Rohdaten lokal, abgeleitete Normbänder im Repo
Status: angenommen 2026-09-05

**Kontext.** Die Normdatensätze (Fukuchi 2018, Schreiber/Moissenet 2019, Van Criekinge 2023) sind einige Gigabyte C3D. Das Repo soll klein bleiben, ein Nutzer soll aber ohne Download analysieren können.
**Entscheidung.** Rohdaten nach `data/norm/<dataset>/` (ignoriert), reproduzierbar per `scripts/build_normbands.py`. Im Repo liegen nur die abgeleiteten, kleinen Normbänder (Mittelwert, SD, Perzentile je Gelenkkanal über 0–100 % Gangzyklus, je Geschwindigkeitsklasse nach Froude-Zahl, plus Zeit-Weg-Parameter) als Parquet oder JSON unter `src/openacl/norm/data/`, mit Attribution und Lizenzhinweis je Quelle. Jede Datei nennt Datensatz, Version, Anzahl Probanden, Verarbeitungsschritte.
**Konsequenzen.** Lizenzprüfung der Datensätze gehört zur Definition of Done des Normband-Pakets. Wenn ein Datensatz nur „für Forschung“ lizenziert ist, gehen seine Ableitungen nicht ins öffentliche Repo.

## ADR-0009 Session-Datenmodell: Ordner pro Session, mehrere Durchgänge und Quellen, Aggregation über Zyklen
Status: vorgeschlagen 2026-09-05 (wird für Antons erste Aufnahme gebaut, Anton kann bis zum Review noch ändern)

**Kontext.** Ein `KinematicsResult` ist ein Durchgang (ein Video). Eine Session hat 10 bis 20 Durchgänge in beide Richtungen, dazu Metadaten (Schmerz, Schuhe, Post-OP-Woche), später Health-Export, IMU, EMG (ADR-0005). Der MDC entsteht aus zwei Sessions am selben Tag. Das alles braucht einen Container.
**Entscheidung (Vorschlag).**
- Eine Session ist ein Ordner `data/sessions/YYYY-MM-DD_HHMM/` mit `meta.yaml` (Schema aus `docs/PROTOKOLL-AUFNAHME.md`, ergänzt um `subject: {height_m, mass_kg, operated_side}`), Videos `A_pass01.mov` … (Kamera A sagittal) und optional `B_pass01.mov` (Kamera B). Nichts davon geht ins Repo.
- `openacl session <dir>` verarbeitet jeden Durchgang einzeln (Backend-Ergebnis wird als `derived/<pass>/kinematics.npz` gecacht, Rerun überspringt fertige Durchgänge), führt Gait-Core je Durchgang aus und poolt dann alle gültigen Zyklen der Session je Seite. Session-Kennzahlen (Zeit-Weg, Peaks, SI, GVS/GPS) werden über die gepoolten Zyklen gebildet, mit n Zyklen, SD und 95-%-Konfidenzintervall des Mittelwerts. Die kameranahe Seite je Durchgang wird mitgeführt; Standard ist, nur kameranahe Zyklen zu poolen, mit Schalter für beide.
- Ausgabe: `derived/session.json` (alle Kennzahlen, maschinenlesbar), `derived/report.md` mit PNGs (Mittelkurven ± SD gegen Normband, Seitenvergleich, Tabelle). Sprache im Report: Beobachtung, nie Diagnose (ADR-0004).
- `openacl compare <dirA> <dirB>` berechnet aus zwei Sessions den Test-Retest-Unterschied je Kennzahl und, sobald mindestens zwei Wiederholungen vorliegen, den eigenen MDC95 (Durchgänge als Targets, Sessions als Wiederholungen). Der MDC wird in `data/subject/mdc.yaml` gespeichert und bei späteren Sessions zum Flaggen benutzt.
- Weitere Quellen hängen als Unterordner an der Session (`health/`, später `imu/`), jede mit eigenem Loader; die Session-Zusammenfassung referenziert sie.
**Konsequenzen.** Der MDC hängt davon ab, was als Wiederholung gilt. Wir nehmen Durchgänge (nicht Einzelzyklen) als Targets, Sessions als Rater, weil das der klinischen Test-Retest-Logik entspricht und Zyklen innerhalb eines Durchgangs korreliert sind. Das steht so im Code und im Report. Ein Verlauf über Wochen ist dann eine Liste von `session.json`.
