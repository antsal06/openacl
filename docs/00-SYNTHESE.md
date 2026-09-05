# Gangprojekt – Synthese der Recherche und Projektvorschlag

Stand: 2026-09-05. Basis: vier Recherche-Berichte in `docs/research/` (Tool-Landschaft, klinische Biomechanik nach ACLR, Technik/Lizenzen, Datensätze/ML/Regulatorik). Alle Zahlen dort mit Quelle.

---

## 1. Kurzantwort auf die Kernfragen

**Gibt es das schon?** Die Messschicht ja, die Analyseschicht nein.

- Kinematik aus Video ist gelöst und offen: OpenCap (2 iPhones), **OpenCap Monocular** (seit März 2026, 1 Handy, Fehler beim Gehen 5,6° vs. 5,2° mit 2 Kameras), Sports2D (1 Handy, 2D), Pose2Sim (mehrere Handys, 3D + OpenSim).
- Kein einziges Tool, weder Open Source noch kommerziell, macht daraus für ein einzelnes Handy-Video: Normvergleich + Seitenvergleich + Verlauf + erklärte Abweichungen mit Quelle. Das Nächste sind OneStep (IMU in der Hosentasche, Normdatenbank, aber keine Gelenkwinkel) und Orthelligent VISION (CE-Medizinprodukt, nur für Praxen).
- Die Lücke ist also genau die, die du beschreibst. Sie ist real und sie ist nicht die Pose-Estimation.

**Was kannst du heute sofort für dein Knie nutzen?**

1. OpenCap Monocular lokal oder auf einer GCP-GPU laufen lassen (Apache 2.0 Code, SMPL-Modell nur für Forschung/privat – für dich persönlich okay).
2. Falls du zwei iOS-Geräte auftreibst: OpenCap Web-App (kostenlos für Forschung/Bildung), Schachbrett drucken, 10 Minuten Setup, 3D-Winkel aller Gelenke.
3. Sports2D auf deinem M2 für schnelle 2D-Sagittalwinkel.
4. OneStep-App für tägliche Zeit-/Weg-Symmetrie mit Normvergleich (Abo, 14 Tage Test). Apple Health „Gehasymmetrie“ und „Doppelstützzeit“ falls iPhone, als grober Trend.

Nichts davon interpretiert. Die Kurven musst du mit dem Physio lesen. Genau das soll das Projekt ändern.

---

## 2. Ehrliches Feedback

### 2.1 Das Messproblem ist größer als das Interpretationsproblem

Das ist der wichtigste Punkt der ganzen Recherche.

| Größe | Wert | Quelle |
|---|---|---|
| Typischer Unterschied Peak-Knieflexion ACLR vs. Gegenseite, 6–12 Monate | ca. 2,6°, SMD −0,52 | Sajedi 2025, Meta-Analyse |
| Messfehler Knieflexion, 1 Handy sagittal | 5–11° RMSE | mehrere Validierungen |
| Messfehler Knieflexion, 2 Handys | ca. 5° RMSE | OpenCap |
| Minimal Detectable Change Peak-Knieflexion (Marker-Labor) | ca. 9° | Gait & Posture 2017 |

Der Effekt, den du suchst, ist kleiner als das Rauschen einer einzelnen Messung. Das heißt nicht, dass es nicht geht, aber es diktiert das Design:

- **Symmetrie innerhalb eines Videos** ist robuster als Absolutwerte, weil systematische Kamerafehler beide Seiten gleich treffen.
- **Viele Gangzyklen mitteln.** 20 bis 40 Zyklen pro Session, nicht 3.
- **Zeit-Weg-Parameter** (Standphase, Doppelstütz, Schrittlänge) sind aus Video zuverlässiger als Winkel und bei ACLR ebenfalls auffällig.
- **Nur flaggen, was über dem Messfehler liegt.** Das Tool muss seinen eigenen MDC kennen und ausgeben.
- **Zweites Handy halbiert den Fehler** (9,8° auf 4,9° in einer Vergleichsstudie). Für dich persönlich lohnt sich das.

### 2.2 Was du fühlst, sieht Video wahrscheinlich nicht

Die Evidenz zu „fühlt sich falsch an, sieht normal aus“ ist konsistent und liegt fast vollständig außerhalb der Kinematik:

- Kniewinkel normalisieren im Mittel bis ca. 12–16 Monate. Bei 6 Monaten sind Reste zu erwarten, aber klein.
- **Kniemomente** (Quadriceps avoidance) bleiben Jahre reduziert. Mit 5 Jahren: Extensormoment 0,04 vs. 0,23 Nm/kg·m. Aus Video nicht messbar, nur modellgeschätzt.
- **Arthrogene Muskelinhibition**, kortikale Reorganisation, veränderte Aktivierung noch 3 Jahre nach OP. Das ist mit hoher Wahrscheinlichkeit der Grund für dein Gefühl. Unsichtbar für jede Kamera.
- **Kontralaterale Überlastung** ist dokumentiert: das nicht-operierte Bein trägt mehr Last, kumulativ pro Kilometer messbar mehr, schnelleres Gehen erhöht vor allem dessen Belastung. Das passt zu deinem Backpacking-Schmerz und ist ein bekanntes Muster, nicht Einbildung.

Konsequenz: Das Tool muss ehrlich sagen können „Kinematik im Normband, Symmetrie unauffällig“, und das wäre trotzdem ein nützlicher Befund. Es würde die Aufmerksamkeit von „ich gehe falsch“ zu „Kraft und neuromuskuläre Kontrolle“ lenken, wo die Leitlinien ohnehin hinschauen: Quadrizeps-Kraft-LSI ≥ 90 % und Hop-Tests sind die validierten Marker, kein Gangwinkel. Frag deinen Physio nach deinem Kraft-LSI, das ist wahrscheinlich die aussagekräftigste Einzelzahl, die du gerade bekommen kannst.

### 2.3 Das „Ideal“ aus dem Sport überträgt sich nicht

- Zwischenpersonen-Variabilität beim Gehen ist ca. 3× größer als die innerhalb einer Person. 90 %-Bänder für Knieflexion bei Gesunden: ±15°.
- Gangmuster sind individuell wiedererkennbar wie eine Signatur.
- Ganglabore vergleichen deshalb nie nur gegen ein Populationsmittel, sondern immer: Normband + Gegenseite + eigener Verlauf + klinischer Kontext.

Dein Einwand gegen die reine Verlaufsidee ist berechtigt: Wer heute falsch geht, sieht im Verlauf nur, dass es stabil falsch bleibt. Die Antwort ist nicht „Ideal“, sondern **Normband ab Session 1** plus **Seitenvergleich ab Session 1** plus Verlauf. Damit erkennt man ein festgefahrenes Muster sofort, ohne so zu tun, als gäbe es den einen richtigen Gang.

Aber: nach ACLR ist die Gegenseite kein sauberer Referenzwert. Sie kompensiert, und Limb-Symmetry-Indizes überschätzen die Funktion. Das Tool muss das als Warnhinweis mitführen.

### 2.4 ML-Klassifikator „ACLR vs. gesund“ ist mit öffentlichen Daten nicht seriös

- Einziger öffentlicher Datensatz mit klar gelabelten ACL-Patienten beim Gehen: COMPWALK-ACL 2025, N = 40, IMU-basiert. Für klassische Baselines okay, für Deep Learning zu klein.
- Publizierte Genauigkeiten > 90 % stammen fast alle aus Sprung-/Lauf-Tests mit Marker- oder IMU-Präzision, nicht aus Gehen mit Video-Rauschen.
- Realistisch und sinnvoll: ein **unüberwachter Abweichungs-Score** nach dem Vorbild von Gait Profile Score / Gait Deviation Index (RMS-Abstand pro Gelenkkurve zum Normband), eventuell später ein Autoencoder auf Normgang. Kein binärer Detektor.

### 2.5 Lizenz-Falle: SMPL

Fast alle modernen Monokular-3D-Methoden (WHAM, TRAM, GVHMR, 4D-Humans, auch OpenCap Monocular intern) laden das SMPL-Körpermodell. Dessen Lizenz verbietet jede kommerzielle Nutzung, unabhängig von der MIT-Lizenz des Codes. OpenPose schließt Sportanwendungen sogar explizit aus.

Für ein Open-Source-Projekt, das Physios und Kliniken später nutzen dürfen sollen, ist die saubere Kette: **RTMPose/RTMW oder MediaPipe (Apache 2.0) → Sports2D (BSD-3) bzw. Pose2Sim (BSD-3) → OpenSim (Apache 2.0)**, optional AddBiomechanics (CC-BY). SAM 3D Body von Meta mit eigenem Körpermodell ist ein interessanter Kandidat, Lizenz muss noch geprüft werden.

Empfehlung: Die Kinematik-Engine als austauschbares Backend bauen. OpenCap Monocular als „Forschungs-Backend“ für dich selbst und zum Benchmarken, der permissive Stack als Produktionspfad.

### 2.6 Regulatorik

Solange das Tool Messwerte, Normbänder und Verlauf zeigt und Auffälligkeiten mit Quelle erklärt, bleibt es Information/Self-Tracking. Sobald es „du hast X“ oder „mach Übung Y“ ausgibt, wird es in der EU nach MDR Regel 11 mindestens Klasse IIa. Das ist der Grund, warum OpenCap sich als „research use only“ positioniert. Formulierung ist keine Kosmetik, sondern entscheidet über die Produktklasse. Für den Physio-Report heißt das: „Beobachtungen und Hypothesen zur Besprechung“, keine Diagnose.

### 2.7 Es gibt eine echte Forschungslücke

Keine Studie hat monokulare Handy-Ganganalyse spezifisch bei ACLR-Patienten beim Gehen validiert. MCID-Werte für Kniewinkel im ACLR-Kontext fehlen. Das ist Risiko (du betrittst Neuland) und Chance (ein Uni-Projekt oder Paper ist möglich, und Physio-Praxen könnten Interesse an einer Pilotierung haben).

---

## 3. Vorgeschlagene Architektur

Fünf Schichten, jede einzeln nutzbar und testbar. Python-Monorepo, Apache-2.0-Lizenz.

```
Handy-Video(s)
   │
   ▼
[1] Aufnahmeprotokoll ── Anleitung, Qualitätscheck (fps, Perspektive, Beleuchtung, Anzahl Zyklen)
   │
   ▼
[2] Kinematik-Engine (austauschbare Backends, gemeinsames Ausgabeschema)
      a) sports2d-Backend:   1 Handy, sagittal, RTMPose → 2D-Winkel      (permissiv, CPU)
      b) pose2sim-Backend:   2 Handys → Triangulation → OpenSim IK        (permissiv, GPU sinnvoll)
      c) opencap-mono-Backend: 1 Handy → 3D + Kinetikschätzung           (nur Forschung/privat, Benchmark)
   Ausgabe: Zeitreihen je Gelenk/Seite, Fuß-Keypoints, Konfidenz je Frame, Metadaten
   │
   ▼
[3] Gait-Core (das Herz des Projekts, reines Python, keine ML-Abhängigkeit)
      - Filterung (Butterworth 4. Ordnung, 6 Hz), Links/Rechts-Konsistenzcheck
      - Gangereignisse (Zeni 2008 aus Fersen-/Zehen-Trajektorie), Zyklus-Segmentierung, 0–100 % Normierung
      - Zeit-Weg-Parameter: Geschwindigkeit, Kadenz, Schrittlänge, Standphase, Doppelstütz
      - Symmetrie: Symmetry Index (Robinson), Gait Asymmetry (Plotnik), Kurven-Symmetrie
      - Normbänder: Fukuchi 2018 + Schreiber/Moissenet 2019 + Van Criekinge 2023, gepoolt,
        geschwindigkeitsnormiert (Froude), Alter als Kovariate
      - Abweichungs-Score je Gelenk (GVS/GPS-Logik) und gesamt
      - Unsicherheit: MDC pro Parameter aus eigenen Wiederholungsmessungen, Flag nur oberhalb
      - Session-Speicher und Verlaufskurven mit Konfidenzband
   │
   ▼
[4] Interpretation
      - Regelbasierte Wissensbasis: bekannte ACLR-Muster mit Quelle
        (z. B. „reduzierte Knieflexion in Loading Response operierte Seite“ → Sajedi 2025, Pfile 2025)
      - Jede Regel: Bedingung, Schwellwert relativ zum MDC, Evidenzgrad, Quelle, was Video NICHT sieht
      - LLM ausschließlich als Report-Schreiber über den deterministischen Befunden,
        nie als Befundquelle; Ausgabe zeigt immer die Zahlen
      - Physio-Report (PDF/Markdown): Kurven, Tabellen, Beobachtungen, offene Fragen für den Termin
   │
   ▼
[5] Oberfläche
      Phase 1: CLI + lokales Dashboard (Streamlit o. ä.)
      Phase 3: Web-App, Upload vom Handy, Verarbeitung auf GCP Cloud Run mit L4-GPU (Skalierung auf null),
               Cloud Storage für Videos, Postgres/Firestore für Sessions, Auth
```

**Warum diese Reihenfolge:** Schicht 3 ist das, was fehlt und was ohne Video testbar ist (mit den öffentlichen Datensätzen als Eingabe). Schicht 2 ist Integration bestehender Tools. Schicht 4 ist Fachwissen in Code. Schicht 5 ist austauschbar.

---

## 4. Roadmap

**Phase 0 – Baseline für dich (Woche 1–2)**
- Aufnahmeprotokoll festlegen, dich selbst filmen (mehrere Durchgänge in beide Richtungen, 60 fps, ideal 2 Handys).
- OpenCap Monocular und Sports2D über dieselben Videos laufen lassen, Ergebnisse vergleichen. Das liefert gleich die erste Fehlerabschätzung.
- Wiederholungsmessung am selben Tag für einen ersten eigenen MDC.

**Phase 1 – Gait-Core (Monat 1–2)**
- Öffentliche Normdatensätze laden, harmonisieren, Normbänder berechnen.
- Events, Zyklen, Parameter, Symmetrie, Abweichungs-Score, Tests gegen die Datensätze.
- sports2d-Backend anbinden. CLI: Video rein, Bericht raus.

**Phase 2 – Interpretation (Monat 2–3)**
- Wissensbasis aus `docs/research/02` in Regeln überführen, jede mit Quelle.
- Report-Generator, Verlaufsansicht, Physio-Export.
- Erste Runde mit deinem Physio: liest er den Report, hilft er, was fehlt.

**Phase 3 – Web und Cloud (Monat 3–5)**
- pose2sim-Backend für 2 Handys, GPU-Verarbeitung auf Cloud Run.
- Upload-Flow, Mehrbenutzer, Open-Source-Release mit Beispieldaten.

**Phase 4 – Validierung und Daten (ab Monat 5, optional)**
- Kooperation mit Physio-Praxis oder Uni-Ganglabor, Vergleich gegen Marker-System, kleine Kohorte mit Einwilligung.
- Erst dann: ML-Abweichungsmodell, eventuell Paper.

---

## 5. Was ich von dir brauche

1. **Hardware:** iPhone oder Android? Zugriff auf ein zweites Handy oder iPad? Laufband verfügbar?
2. **Dein Fall:** Welches Knie, welches Transplantat (Hamstring, Quadrizeps, Patellasehne)? Kennst du deinen Quadrizeps-Kraft-LSI oder Hop-Test-Werte? Das steuert die Wissensbasis und den ersten Report.
3. **Ziel-Reihenfolge:** Zuerst Werkzeug für dich, dann Open Source für andere? Oder von Anfang an Physio-tauglich? Das entscheidet, wie streng wir bei SMPL-basierten Backends sind.
4. **Physio-Zugang:** Würde dein Physio einen Report lesen und Feedback geben? Gibt es eine Uni oder ein Ganglabor in Reichweite für Phase 4?
5. **Rollen:** Programmierst du mit oder soll ich den Großteil bauen und du testest? Python ist gesetzt, Frontend-Präferenz?
6. **Name und Lizenz:** Projektname? Apache 2.0 ist mein Vorschlag.
7. **GCP:** Welches Projekt und welche Region sollen wir nutzen? Aktuell ist `pace-mcp` als Default konfiguriert, das ist vermutlich ein anderes Projekt.
