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

## ADR-0010 Pass-Segmentierung: Langvideo → Durchgänge, Bedingung als eigene Session
Status: angenommen 2026-09-11 (Anton hat die Integration beauftragt; Prototyp aus dem Scratchpad als `openacl segment` ins Repo überführt, getestet)

**Kontext.** Antons Aufnahmen vom 2026-09-07 sind je ein durchlaufendes Video pro Bedingung (Socken, Socken-Wiederholung, Schuhe, schnell), 96 bis 265 s lang, mit 6 bis 18 Durchgängen abwechselnd in beide Richtungen. Das Session-Modell (ADR-0009) erwartet ein Video pro Durchgang (`A_pass01.mov`). Sports2D bestimmt die sichtbare Seite für die Pixel-zu-Meter-Umrechnung **einmal pro Video** aus der Gehrichtung (`Sports2D/process.py`, `visible_side='auto'`); ein Video mit beiden Richtungen liefert dort `front` und damit falsche Skalierung. Außerdem ist die kamerafern Seite je Durchgang eine andere, das Pooling (`camera_near`) braucht die Richtung pro Durchgang.
**Entscheidung (Vorschlag).**
- `openacl segment <video> --out <session_dir> --condition <name>` schneidet ein Langvideo mit statischer Kamera in Durchgänge. Erkennung ohne Pose-Modell: ffmpeg dekodiert auf 320×180 bei 10 fps, Median-Hintergrund über das ganze Video, Vordergrundfläche und x-Schwerpunkt je Frame. Ein Durchgang ist ein zusammenhängender Lauf mit Fläche > 1 % des Bilds, ≥ 3 s lang, Lücken < 0,5 s überbrückt, und mit einer Schwerpunktdrift von ≥ 120 px (verhindert, dass Aufstellen oder Umdrehen im Bildrand als Durchgang zählt). Richtung = Vorzeichen der Drift. Jeder Durchgang wird frame-genau als H.264 (`A_pass<NN>.mp4`, 0,15 s Vor- und Nachlauf) neu kodiert; `passes.yaml` hält Zeitfenster, Richtung und Drift fest.
- Jede Aufnahmebedingung ist eine eigene Session `data/sessions/YYYY-MM-DD_<condition>/` mit kopierter `meta.yaml` plus `condition` und `source_video`. Bedingungen werden nicht gepoolt; Socken-Wiederholung gegen Socken ist das Test-Retest-Paar für `openacl compare`.
- Qualitätsgate für die kamerafern Seite: Sports2D liefert für den kamerafernen Fuß Sprunggelenkwinkel um 180° (Fersen-Zehen-Vertauschung bei Verdeckung, beobachtet am 2026-09-11). Der Backend-Adapter setzt Sprunggelenkwinkel außerhalb −60…+60° auf NaN und warnt, statt sie in den GPS laufen zu lassen.
**Konsequenzen.** Ein 10-Durchgänge-Video liefert ca. 10 kameranahe Zyklen pro Seite (2 pro Durchgang bei 5 m Messbereich), 18 Durchgänge ca. 18. Für die 20 bis 40 Zyklen aus `docs/00-SYNTHESE.md` braucht es also 20 bis 40 Durchgänge oder einen längeren Messbereich. Die Segmentierung setzt eine unbewegte Kamera und eine einzelne Person im Bild voraus; das Protokoll verlangt beides schon.

**Umsetzung (2026-09-11).** `src/openacl/session/segment.py`: `decode_grayscale`/`foreground_timeseries` (ffmpeg-Dekodierung, 320x180 @ 10 fps, Median-Hintergrund über ~200 Frames) sind von der reinen Erkennungslogik `find_passes` getrennt, damit Letztere ohne ffmpeg testbar ist. Alle Schwellwerte sind benannte Modulkonstanten mit Einheit (`MIN_PASS_AREA_FRACTION`, `MIN_PASS_DURATION_S`, `MAX_GAP_S`, `MIN_DRIFT_PX`, `PASS_PAD_S`, `CUT_CRF`) und Funktionsparameter zugleich. `cut_passes` schneidet mit ffmpeg (`libx264`, crf 18, yuv420p, kein Ton) nach `<camera>_pass<NN>.mp4`; ein fehlendes ffmpeg-Binary gibt `RuntimeError` (Muster wie `openacl.backends.video.transcode_to_h264`). CLI: `openacl segment <video> --out <session_dir> [--meta ...] [--condition ...] [--dry-run]` in `src/openacl/cli.py`. Die kamerafernen-Sprunggelenk-180°-Qualitätsgate ist als `WRAP_RULES_DEG`/`unwrap_angles` in `src/openacl/backends/sports2d.py` umgesetzt (Shift statt NaN, weil die Bewegungsamplitude dabei erhalten bleibt, siehe Modul-Docstring dort). Die Richtungs-zu-`visible_side`-Übersetzung sitzt in `openacl.session.model.resolve_near_side_from_direction` plus `SessionMeta.near_side_when_walking_plus_x` (`meta.yaml` `cameras.A.near_side_when_walking_plus_x`, Default `R`, Warnung wenn eine `passes.yaml` existiert und das Feld fehlt) und wird in `openacl.session.process.run_backend` angewendet. `cameras.A.distance_m` wird dort als Sports2D-`px_to_meters_conversion.perspective_value` durchgereicht (Sports2D-Default 10 m).

## ADR-0011 OpenCap (2 Handys, 3D) als Vergleichsquelle, nicht als Produktionsbackend
Status: angenommen 2026-09-11 (Anton hat die Integration beauftragt; Wegwerf-Adapter aus Session 2026-09-10 im Scratchpad als `openacl.backends.opencap` ins Repo überführt, getestet)

**Kontext.** Antons OpenCap-Session vom 2026-09-07 (LaiUhlrich2022-Modell, HRNet, LSTM-Augmenter) liefert `.mot` mit 3D-Gelenkwinkeln inklusive Frontal- und Transversalebene (`pelvis_list`, `hip_adduction`, `hip_rotation`) und `.trc` mit Markern in Metern. Das ist die einzige Quelle, die „gerade gehen“ (seitliche Abweichung, Schrittbreite, Beckenkippung) direkt misst. OpenCap-Daten liegen auf Stanford-Servern, das Web-Tool ist für Forschung und private Nutzung frei; der Verarbeitungscode ist nicht Teil des Produktionspfads (ADR-0002).
**Entscheidung (Vorschlag).** `openacl.backends.opencap` liest OpenCap-Exporte (`.mot` + `.trc`) in `KinematicsResult`, mit Mapping `knee_angle→knee_flexion_deg`, `hip_flexion→hip_flexion_deg`, `ankle_angle→ankle_dorsiflexion_deg` (Vorzeichen gegen einen Gehtrial geprüft: Flexion positiv), `camera_near_side=None`. Frames, die exakt auf einer OpenSim-Koordinatengrenze sitzen (`knee_angle` 0,00°, `hip_flexion` −30,00°, `ankle_angle` −50,00°), sind IK-Sättigung und werden als NaN markiert; standardmäßig wird auf den Bereich beschnitten, in dem keine Sättigung auftritt (bei Antons Aufbau x ≥ −4 m vom Kalibrierursprung). Zusätzliche Kanäle `pelvis_list_deg`, `hip_adduction_deg`, `hip_rotation_deg` kommen als neue kanonische Namen ins Schema (ADR-0007 sieht das vor); die Interpretationsschicht nutzt sie nur, wenn das Backend sie liefert.
**Konsequenzen.** OpenCap bleibt Referenz- und Frontalebenen-Quelle, kein Ersatz für Sports2D. Die Zahl der Zyklen je OpenCap-Trial ist mit 2 bis 3 gering, weil der kalibrierte Bereich kurz ist; für Frontalebenen-Aussagen reicht das, für Kniewinkel-Mittelwerte nicht.

**Umsetzung (2026-09-11).** `src/openacl/backends/opencap.py`: `load_opencap(trial_dir, trial, x_min_m=None) -> KinematicsResult`, `backend="opencap"`. Clipping ist jetzt pro Kanal und Frame: `_clip_to_nan` setzt exakt auf der Koordinatengrenze liegende Werte (`np.isclose`, Toleranz 0,05°) in genau diesem Kanal auf NaN, statt nur eine aggregierte Maske zu zählen; die Zählung pro Kanal steht in `meta["clipped_frames"]`. Zusätzliche Kanäle `pelvis_list_deg` (ohne Seite), `hip_adduction_deg_L/R`, `hip_rotation_deg_L/R` sind in `src/openacl/schema.py` `ANGLE_CHANNELS` ergänzt (ADR-0007); ihr Vorzeichen ist unverändert aus OpenSim übernommen und *nicht* gegen eine klinische Konvention geprüft (anders als die sagittale Triade Knie/Hüfte/Sprunggelenk, siehe Modul-Docstring). Tests in `tests/backends/test_opencap.py` gegen handgeschriebene `.mot`/`.trc`-Fixtures im Format von `src/openacl/backends/_trc_mot.py`.
