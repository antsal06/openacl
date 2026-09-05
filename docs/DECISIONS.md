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
Status: vorgeschlagen 2026-09-05

**Kontext.** Viel GCP-Guthaben, sporadische Analysejobs, keine 24/7-Last. Aktuelle gcloud-Default-Konfig zeigt auf `pace-mcp`, das ist ein anderes Projekt.
**Entscheidung (Vorschlag).** Neues Projekt `openacl`, Region `europe-west4` (Niederlande, Cloud-Run-GPU L4 verfügbar; `europe-west1` als Alternative). Phase 1 und 2 laufen lokal, GCP wird erst in Phase 3 für die Web-App und für GPU-Backends gebraucht. Ausnahme: OpenCap Monocular in Phase 0 auf einer Compute-Engine-VM mit einer L4 oder T4, weil das auf dem M2 ohne CUDA nicht sinnvoll läuft.
**Konsequenzen.** Setup-Anleitung in `infra/GCP-SETUP.md`. Kein Service-Account-Key im Repo, lokal über `gcloud auth application-default login`.
