<!-- Recherche-Bericht, erstellt 2026-09-05 durch einen Sonnet-5-Research-Agenten. Quellen am Ende. -->

# Ganganalyse per Handy-Video – Landschaftsanalyse 2026

## Methodik-Hinweis
Recherche über ~25 Quellen (Papers, GitHub-APIs, Herstellerseiten, Validierungsstudien), Stand September 2026. Fokus: existiert bereits ein Tool, das (1) Gelenkwinkel mehrerer Gelenke, (2) räumlich-zeitliche Gangparameter, (3) L/R-Symmetrie, (4) Normvergleich, (5) Verlauf über Zeit UND (6) eine Klartext-Interpretationsebene liefert – aus einem einzigen Handy-Video, für Laien nutzbar.

---

## A) Open-Source-Forschungstools

**OpenCap** (Stanford Neuromuscular Biomechanics Lab, opencap.ai) – Web-basiert, cloud-verarbeitet. Standard-Setup: **2 iOS-Geräte** (iPhone/iPad) + 2 Stative + ein bedrucktes A4-Schachbrett (210×175mm) zur Kamerakalibrierung, plus ein Gerät für die Web-App; auch 2–7 Smartphones möglich. Liefert 3D-Kinematik (Gelenkwinkel) und über physikbasierte Simulation geschätzte Kinetik (Gelenkkräfte) via OpenSim, alles in unter 10 Minuten Handling-Zeit und für <700 USD Hardware ([PLOS Comp Biology](https://journals.plos.org/ploscompbiol/article?id=10.1371%2Fjournal.pcbi.1011462), [Stanford PDF](https://nmbl.stanford.edu/wp-content/uploads/OpenCapManuscript_higherRes.pdf)). Das Web-Dashboard zeigt Rohkinematik-Kurven, aber **keine Normvergleiche oder automatisierte Abweichungs-/Empfehlungsschicht** – Interpretation bleibt Aufgabe von Forscher/Kliniker ([ResearchGate zu Validierung](https://www.researchgate.net/publication/395265357_VALIDITY_AND_RELIABILITY_OF_OPENCAP_DURING_SELECTED_LOWER_LIMB_FUNCTIONAL_MOVEMENT_TASKS)). Neu: **OpenCap Monocular** (Univ. of Utah, Preprint März 2026) funktioniert mit **nur einem Smartphone** (nutzt WHAM-Modell + Optimierung), Fehler 4,8° (Rotations-DOF), 3,4cm (Becken-Translation) – open source auf GitHub ([arXiv:2603.24733](https://arxiv.org/abs/2603.24733), [GitHub](https://github.com/utahmobl/opencap-monocular)). Repo `opencap-core`: 362 Stars, aktiv (letzter Push 27.08.2026), Apache-2.0-Lizenz. Ausgerichtet auf Forscher/Kliniker, nicht auf Endnutzer ohne Fachwissen.

**Sports2D** (David Pagnon) – Python-CLI, verarbeitet ein einzelnes Video oder Webcam-Stream zu 2D-Keypoints und 2D-Gelenk-/Segmentwinkeln, seit v0.6.0 (Jan 2025) mit mehreren Pose-Modellen (body/body_with_feet/whole_body) und Marker-Augmentation für Pseudo-3D-Lift; aktuelle Version v0.8.7 (Mai 2025) ([JOSS-Paper](https://joss.theoj.org/papers/10.21105/joss.06849), [GitHub README](https://github.com/davidpagnon/Sports2D/blob/main/README.md)). GitHub-Repo aktiv (294 Stars, letzter Push 25.08.2026, BSD-3-Clause). Berechnet Winkel und einfache Gangevents, aber **keine Normvergleichs- oder Interpretationsschicht** – reine Zahlen-/Kurvenausgabe. Genauigkeit vergleichbarer Pose2Sim-Pipeline: mittlere Winkelfehler 3,0°/4,1°/4,0° (Gehen/Laufen/Radfahren) ([PMC Pose2Sim Part 2](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9002957/)).

**Pose2Sim** (perfanalytics) – Multi-Kamera-Workflow "2D Pose→OpenSim 3D", beliebige Kombination aus Handys/Webcams/GoPros, RTMPose-basiert, mit Kalibrierung, Synchronisation, Marker-Augmentation, Multi-Personen-Tracking ([GitHub](https://github.com/perfanalytics/pose2sim), 799 Stars, aktiv, BSD-3-Clause). Forschungsgrade Genauigkeit, aber **keine Norm-/Interpretationsschicht**, reines Kinematik-Werkzeug für Forscher.

**AddBiomechanics** (Stanford, simtk.org) – Cloud-Service, automatisiert Skalierung eines OpenSim-Modells sowie Inverse Kinematik/Dynamik aus hochgeladenen Marker-/Kraftmessdaten in Minuten; **benötigt aber Marker-Motion-Capture-Daten**, kein reines Handy-Video-Tool ([SimTK](https://simtk.org/projects/addbiomechanics)). Für Forscher, keine Normvergleichsebene.

**OpenSim/OpenSim Moco** – Die zugrundeliegende Simulationssoftware, kein eigenständiges Video-zu-Analyse-Tool, sondern Backend für OpenCap/Pose2Sim ([Wikipedia](https://en.wikipedia.org/wiki/OpenSim_(simulation_toolkit))).

**Kinetics Toolkit (ktk)** (Félix Chénier, UQAM) – Reines Python-Package für Biomechanik-Datenverarbeitung (Filterung, Zyklen-Segmentierung, 3D-Visualisierung), **kein Pose-Estimation- oder Video-Tool**, setzt vorhandene Kinematikdaten voraus ([GitHub](https://github.com/felixchenier/kineticstoolkit), [JOSS](https://joss.theoj.org/papers/10.21105/joss.03714)).

**gaitpy** – Python-Package für Gangparameter aus einem **Lendenwirbel-Beschleunigungssensor** (nicht Video); Original **nicht mehr gepflegt**, Autor empfiehlt Nachfolgeprojekt "Scikit Digital Health" ([GitHub-Issue-Hinweis](https://github.com/openjournals/joss-reviews/issues/1778)).

**pyCGM** – reimplementiert das klassische "Conventional Gait Model" in Python für Lehrzwecke, setzt Marker-Daten voraus, kein Video-Input ([GitHub](https://github.com/cadop/pyCGM)).

**Weitere Github-Nischenprojekte mit klinischem Fokus, ohne Interpretationsschicht:**
- **VisionMD-Gait** (Univ. Florida, Diego Guarin, Publikation Jan 2026): Open Source, **nur ein Frontal-Smartphone-Video**, keine Cloud-Übertragung nötig, validiert an 24 Gesunden + 10 Schwindel-Patienten gegen Wearable-Referenz, mittlerer Fehler <10% bei Ganggeschwindigkeit/Kadenz/Schrittdauer ([Scientific Reports](https://www.nature.com/articles/s41598-025-34912-5)). Kein Normvergleich/Interpretationstext dokumentiert.
- **GaitAnalysis-PoseEstimation** (Jan Stenum, github.com/janstenum): OpenPose-basiert, 2D, ein Video (seitlich oder frontal), gegen 3D-Mocap validiert, Genauigkeit ausreichend zur Erkennung von Gangveränderungen ([PLOS Digital Health](https://journals.plos.org/digitalhealth/article?id=10.1371%2Fjournal.pdig.0000467), [GitHub](https://github.com/janstenum/GaitAnalysis-PoseEstimation)). Reines Forschungs-Skript (MATLAB+Colab), keine Endnutzer-Oberfläche, keine Norm-/Interpretationsschicht.
- **OpenPose-for-2D-Gait-Analysis** (batking24): Kniewinkel-fokussiertes Studentenprojekt, klein, unklarer Pflegestatus ([GitHub](https://github.com/batking24/OpenPose-for-2D-Gait-Analysis)).

**Fazit A:** Es existiert exzellente Open-Source-Infrastruktur für Kinematik aus Video, aber **keines dieser Tools hat eine automatisierte Norm-/Abweichungs-/Empfehlungsschicht** – alle sind "Rohdaten-Lieferanten" für Fachleute.

---

## B) Kommerzielle/klinische Apps

| Tool | Kurzbefund |
|---|---|
| **OneStep** | Smartphone-in-Tasche-IMU-basiert (kein Video), misst Schrittlänge, Kadenz, Doppelstandphase, Gangtempo, Symmetrie. Nutzt Datenbank von **>50 Mio. Gangzyklen** zur Normvergleichs-Berechnung je Kohorte/Diagnose ([OneStep Blog](https://www.onestep.co/resources-blog/leveraging-population-data-in-clinical-practice)) – **hat also tatsächlich eine Normvergleichsebene**. Validiert unter anderem bei Knie-TEP-Reha ([Sensors 2026](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12846111/)) und diversen orthopädischen Populationen ([JOSR 2022](https://josr-online.biomedcentral.com/articles/10.1186/s13018-022-03300-4)). B2C-App direkt für Patienten UND B2B für Kliniken verfügbar, Abo-Modell mit 14-Tage-Test ([Pricing-Seite](https://join.onestep.co/pricing)). **Liefert aber keine Gelenkwinkel**, nur Zeit-/Weg-Parameter.
| **Ochy** | App (iOS/Android), reines Handy-Video, <60 Sek. Analyse, liefert Gelenkwinkel (Knie, Becken), Überstriding, Pronation, Kadenz, mit Feedback-Text ("spot pronation, pelvic tilt, overstride…") ([ochy.io](https://www.ochy.io/runners)). Für Läufer/Coaches/Physios konzipiert, primär **Laufanalyse**, nicht klinische Reha-Ganganalyse. Keine unabhängige Genauigkeitsstudie gefunden.
| **Orthelligent VISION** (OPED GmbH) | CE-registriertes Medizinprodukt, 2D-Video (30 Sek.), Cloud-Auswertung, automatischer Bericht zu Ganggeschwindigkeit und Knieflexion. Validiert an Gesunden, Amputierten und Kniearthrose-Patienten: ROM-Abweichung Knie 3,8°, Hüfte 3,7°, Sprunggelenk 5,4° ggü. optoelektronischem System ([PLOS ONE 2025](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0324499), [Frontiers Kniearthrose-Pilotstudie](https://www.frontiersin.org/journals/bioengineering-and-biotechnology/articles/10.3389/fbioe.2026.1869878/full)). B2B (Orthopädie/Reha-Praxen), kein Direktvertrieb an Patienten.
| **Theia3D** | Multi-Kamera (mehrere handelsübliche 2D-Kameras + neuronale Netze statt Marker), Setup-Zeit -80% ggü. Marker-Mocap, systematisch validiert bei Kindern mit Zerebralparese, Schlaganfall, ACL-Rekonstruktion, ältere Erwachsene ([Sci Reports 2024](https://www.nature.com/articles/s41598-024-62119-7), [systematisches Review](https://www.sciencedirect.com/science/article/pii/S0933365725002672)). Reines B2B-Laborsystem, keine öffentliche Preisangabe, keine Interpretationsschicht dokumentiert – liefert Rohkinematik für Fachpersonal.
| **DARI Motion** | FDA-zugelassenes 3D-Markerless-System (Multi-Kamera), erkennt Asymmetrien/Kompensationen in Minuten, für Kliniken/Reha-Zentren ([darimotion.com](https://darimotion.com/)). Keine öffentliche Preisliste, reines Klinik-/Institutssystem (z.B. MUSC Health).
| **KinaTrax** | Multi-Kamera-Markerless, ursprünglich MLB-Baseball-Analyse, jetzt für klinische Ganganalyse adaptiert; valide für Gang-Zeitparameter nach Schlaganfall ([PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12431465/)). Reines Institutssystem.
| **VALD HumanTrak** | Einzelne Tiefenkamera (IR), primär für diskrete ROM-Bewegungen (Squats, Sprünge) – **liefert explizit KEINE Ganganalyse** laut Hersteller ([valdhealth.com](https://valdhealth.com/news/understanding-markerless-motion-capture-with-humantrak)).
| **Physimax** | Kamerabasiertes Bewegungsscreening für Sportteams (Verletzungsrisiko), Scores relativ zu "Same-Level Norms" – **hat also eine Normvergleichsschicht**, aber ausschließlich B2B für Profi-Sportteams, kein Gang-Fokus ([Athletic Business](https://www.athleticbusiness.com/industry-press-room/article/15146783/physimaxs-real-time-movement-assessment-validates-landing-error-scoring-system)).
| **Kemtai** | Kamerabasierte Bewegungs-KI (111 Keypoints) für Reha-Übungen/ROM in Echtzeit, kein dediziertes Ganganalyse-Modul gefunden, eher Trainingssteuerung/Adhärenz ([kemtai.com](https://kemtai.com/product/computer-vision-rehab/)).
| **Hinge Health** | Digitale MSK-Reha-Plattform (übernahm Wrnch/Computer-Vision-Technologie), primär Übungs-Coaching, nicht dediziertes Ganganalyse-Tool, B2B über Arbeitgeber/Versicherer ([Kontext](https://med-tech.world/news/personalized-care-anywhere-kemtais-vision-for-advanced-physiotherapy/)).
| **Moveshelf** | Keine eigene Analyse-Engine, sondern Cloud-Infrastruktur/Datenbank für bestehende Ganglabore (Speicherung, Reports, Fernüberwachung), genutzt von >30.000 Patienten in Kliniken weltweit ([moveshelf.com](https://moveshelf.com/blog/trusted-worldwide)). Reines B2B-Backend.
| **Vicon/Qualisys (markerless Optionen)** | Etablierte Marker-Mocap-Hersteller bieten inzwischen Markerless-Zusatzmodule in ihrer Ganganalyse-Software an ([Qualisys](https://www.qualisys.com/analysis/gait/), [Vicon Nexus](https://www.vicon.com/software/nexus/)) – Hochpreis-Laborsysteme, nicht handy-basiert.
| **Xsens/Movella Analyze 2025** | IMU-Anzugsystem (nicht Video), 2025 mit "Biomech 2.0" (geschlechtsspezifische anatomische Modelle) für Gang/Haltung optimiert ([Movella Pressemitteilung](https://www.movella.com/company/press-room/xsens-analyze-2025-movella-launches-first-male-and-female-anatomical-models-for-inertial-motion-capture)). Institutspreisklasse.

**Fazit B:** Kommerzielle Systeme mit echter Normvergleichsschicht existieren (OneStep, Physimax) – aber jeweils **entweder ohne Gelenkwinkel** (OneStep) **oder ohne Gang-Fokus** (Physimax). Systeme mit vollständiger Kinematik (Theia3D, DARI, KinaTrax) sind reine B2B-Laborsysteme ohne Patienten-Interpretationsebene und ohne Preistransparenz.

---

## C) Plattform-eingebaute Gangmetriken

**Apple Health/Watch** (benötigt Apple Watch, nicht nur iPhone, für die meisten Metriken; iPhone allein liefert Basis-Gangmetriken aus dem Taschensensor): Walking Speed, Step Length, Double Support Time, Walking Asymmetry, Walking Steadiness. Laut Apples eigenem Whitepaper "starke Übereinstimmung" mit Druckmatten-Referenz für Gangtempo/Schrittlänge/Doppelstand/Asymmetrie ([Apple Whitepaper](https://www.apple.com/healthcare/docs/site/Measuring_Walking_Quality_Through_iPhone_Mobility_Metrics.pdf)); unabhängige Validierung (Kinder/Erwachsene/Senioren gg. APDM Mobility Lab) zeigt aber für **Doppelstandzeit nur ICC 0,42–0,58** (gering bis moderat) ([Scientific Reports 2023](https://www.nature.com/articles/s41598-023-32550-3)). Walking Steadiness: Sensitivität 86%/Spezifität 78% für Sturzrisiko-Klassifikation in einer 2022-Studie, mit starker prädiktiver Genauigkeit für 12-Monats-Sturzrisiko in Folgeauswertungen der Apple Heart & Movement Study ([npj Digital Medicine/AHMS](https://appleheartandmovementstudy.bwh.harvard.edu/celebrating-ahms/)). **Keine Gelenkwinkel, keine automatisierte Reha-Interpretationsschicht** in der nativen Health-App – reine Trendanzeige. Apps, die diese Daten für Reha auswerten, wurden in der Recherche nicht als etabliertes Produkt gefunden (nur einzelne Forschungsnutzungen, z.B. nach Knie-OP, [PRNewswire](https://www.prnewswire.com/news-releases/new-study-uses-apple-health-mobility-data-to-evaluate-outcome-measures-following-lower-extremity-surgery-302396238.html)).

**Google Fit/Pixel Watch:** Google Research zeigt fortgeschrittene IMU-Modelle (Gangtempo, Doppelstand, Schrittlänge, Schwung-/Standzeit **getrennt links/rechts**) auf Basis von Pixel-Watch-Rohdaten ([Google Research Blog](https://research.google/blog/unlocking-health-insights-estimating-advanced-walking-metrics-with-smartwatches/)) – Stand 2025/26 eher Forschungs-/Beta-Feature als breit ausgerolltes, klinisch validiertes Produkt wie bei Apple.

**Garmin Running Dynamics:** "Ground Contact Time Balance" (L/R-Asymmetrie) via Brustgurt/Laufdynamik-Pod, korreliert laut Garmin mit Verletzungsrisiko bei starker Abweichung von 50/50 ([Garmin](https://www.garmin.com/en-US/garmin-technology/running-science/running-dynamics/ground-contact-time-balance/)); unabhängige Validierungsstudie fand aber signifikante Abweichungen der absoluten Bodenkontaktzeiten vom Kraftmessplatten-Goldstandard ([PMC 2023](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10459607/)) – Absolutwerte ungenau, Trend/Symmetrie-Richtung vermutlich brauchbarer. Nur für Laufen, nicht Gehen konzipiert.

**Fazit C:** Plattform-Sensoren liefern brauchbare **Trend**-Symmetriewerte, aber ohne Gelenkwinkel und ohne klinische Interpretation ("was bedeutet das für mein Knie").

---

## D) Physio-Praxis-Tools

Aktuell in der Praxis dominant: **Videoanalyse-Apps ohne biomechanische Auswertung** – reine Aufnahme/Zeitlupen-/Winkel-Mess-Tools per Hand:
- **Kinovea** (Open Source, kostenlos, v2025.1.0): Manuelles Tracking von Gelenkwinkeln/Distanzen/Phasen aus Video, in mehreren Studien gegen 3D-Mocap validiert für ROM und Gangparameter, gilt als reliable, günstige Alternative ([Reliability-Studie](https://www.researchgate.net/publication/341832431_Reliability_of_Kinovea_Software_and_Agreement_with_a_Three-Dimensional_Motion_System_for_Gait_Analysis_in_Healthy_Subjects)). **Keine Automatisierung, keine Normvergleiche** – der Physio zieht die Winkel-Marker selbst per Hand.
- **Dartfish**: Etablierte Profi-Analysesuite, auch für Reha/Gesundheitswesen vermarktet ([dartfish.com/healthcare](https://www.dartfish.com/healthcare/)), Institutspreisklasse, keine automatisierte Interpretation, Werkzeug für manuellen Video-Vergleich/Annotation.
- **OnForm** (übernahm 2024 Hudl Technique, das eingestellt wurde): Mobile-first Video-Coaching mit Feedback/Messaging, für Trainer, nicht klinisch validiert ([Onform-Blog](https://onform.com/blog/onform-acquires-hudl-technique/)).

**Fazit D:** Physios nutzen heute überwiegend **manuelle** Video-Tools (Kinovea kostenlos, Dartfish/OnForm kostenpflichtig) – keines davon rechnet automatisch Gangparameter, vergleicht mit Normwerten oder gibt Handlungsempfehlungen.

---

## Tabelle: Alle untersuchten Tools

| Tool | Input | Output | Interpretationsebene | Open Source | Kosten | Für wen |
|---|---|---|---|---|---|---|
| OpenCap (+Monocular) | 2 iOS-Geräte (klassisch) / 1 Smartphone (Monocular, neu 2026) | 3D-Gelenkwinkel, geschätzte Kinetik | Nein | Ja (Apache-2.0) | Kostenlos (Hardware ~700$) | Forscher/Kliniker |
| Sports2D | 1 Video/Webcam | 2D-Gelenk-/Segmentwinkel, einfache Gangevents | Nein | Ja (BSD-3) | Kostenlos | Forscher/Techn. versierte |
| Pose2Sim | 2+ Kameras/Handys | 3D-Kinematik (OpenSim) | Nein | Ja (BSD-3) | Kostenlos | Forscher |
| AddBiomechanics | Marker-Mocap-Daten | Skaliertes Modell, IK/ID | Nein | Ja | Kostenlos | Forscher |
| Kinetics Toolkit / pyCGM / gaitpy | Vorhandene Kinematik/IMU-Daten | Datenverarbeitung | Nein | Ja | Kostenlos | Forscher (gaitpy: unmaintained) |
| VisionMD-Gait | 1 Smartphone-Video | Gangtempo, Kadenz, Schrittdauer u.a. | Nein (nur Rohwerte) | Ja | Kostenlos | Forscher/Kliniker |
| GaitAnalysis-PoseEstimation (Stenum) | 1 Video | 2D-Kinematik, Gangparameter | Nein | Ja | Kostenlos | Forscher |
| OneStep | Handy in Tasche (IMU) | Schrittlänge, Kadenz, Doppelstand, Symmetrie | **Ja** (Normdatenbank 50 Mio. Zyklen) | Nein | Abo (App-Store, 14 Tage Test) | Patienten + Kliniken |
| Ochy | 1 Handy-Video | Gelenkwinkel (Knie/Becken), Laufform-Feedback | Teilweise (Feedback-Text) | Nein | App (Freemium/Abo vermutet) | Läufer, Coaches, Physios |
| Orthelligent VISION | 1 Handy-Video (30s), Cloud | Ganggeschwindigkeit, Knieflexion, Bericht | Teilweise (automat. Bericht) | Nein (CE-Medizinprodukt) | B2B, keine Preisangabe | Orthopädie-/Reha-Praxen |
| Theia3D | Multi-Kamera | Volle 3D-Kinematik | Nein | Nein | B2B, k.A. | Labore/Kliniken |
| DARI Motion | Multi-Kamera | 3D-Kinematik, Asymmetrien | Teilweise (Risiko-Scores) | Nein | B2B, k.A. | Kliniken |
| KinaTrax | Multi-Kamera | Kinematik, Gangzeitparameter | Nein | Nein | B2B, k.A. | Kliniken/Profisport |
| VALD HumanTrak | 1 Tiefenkamera | ROM diskreter Bewegungen (kein Gang!) | Teilweise | Nein | B2B | Kliniken |
| Physimax | Kamera-Screening | Bewegungs-/Verletzungsrisiko-Score | **Ja** (Alters-/Level-Normen) | Nein | B2B | Profisport-Teams |
| Kemtai | Kamera (Echtzeit) | Übungsausführung/ROM | Teilweise (Echtzeit-Korrektur) | Nein | B2B/Abo | Reha-Praxen |
| Hinge Health | Kamera+Sensorik | Übungs-Coaching | Teilweise | Nein | B2B (Arbeitgeber/Versicherer) | Patienten (arbeitgeberfinanziert) |
| Apple Health/Watch | iPhone/Watch-Sensoren | Gangtempo, Schrittlänge, Doppelstand, Asymmetrie, Walking Steadiness | Nein (nur Trendanzeige) | Nein | Inklusive (Gerät nötig) | Alle iPhone/Watch-Nutzer |
| Garmin Running Dynamics | Uhr/Brustgurt/Pod | Bodenkontaktzeit-Balance u.a. | Nein | Nein | Inklusive (Gerät nötig) | Läufer |
| Kinovea | 1 Video (manuell ausgewertet) | Manuell gemessene Winkel/Distanzen/Zeiten | Nein | Ja (GPL) | Kostenlos | Physios/Trainer |
| Dartfish / OnForm | Video | Annotierter Videovergleich | Nein | Nein | Institution/Abo | Physios/Trainer/Institutionen |

---

## 2. Was kann der Nutzer HEUTE konkret nutzen?

Für sein Profil (6 Monate nach VKB-Rekonstruktion, spürbare Asymmetrie, Ziel: Gelenkwinkel + Gangparameter + Symmetrie + Verlaufsmonitoring) ist die pragmatischste **sofort umsetzbare Kombination**:

1. **OneStep-App** (iOS/Android, Abo) – täglich per Handy-in-Tasche-Gehen: liefert Schrittlänge, Kadenz, Doppelstandphase und **Symmetrie-Index mit Normvergleich**, Verlaufsgraphen über Wochen, minimaler Aufwand (Handy einstecken, laufen). Deckt Gangparameter + Symmetrie + Verlauf + Teil-Interpretation ab, aber **keine Gelenkwinkel**.
2. **OpenCap (2 alte iPhones + ausgedrucktes Schachbrett, ~30–60 Min. Einrichtungsaufwand)** oder – sobald öffentlich nutzbar – **OpenCap Monocular (1 Handy)** – für periodische (z.B. monatliche) Tiefenanalyse der 3D-Gelenkwinkel von Knie/Hüfte/Sprunggelenk/Becken/Rumpf im Seitenvergleich. Erfordert Eigeninterpretation der Kurven (kein automatisches "das ist zu viel/zu wenig") oder Rücksprache mit Physio.
3. Ergänzend **Kinovea** (kostenlos) für schnelle manuelle Winkelmessung einzelner Videoframes, falls OpenCap zu aufwendig erscheint.

Realistischer Aufwand: OneStep sofort (Minuten), OpenCap einmaliges Setup (2 alte/geliehene iPhones + Drucker für Schachbrett, danach <10 Min. pro Aufnahme). Kein Tool liefert die vom Nutzer gewünschte fertige Interpretation ("dein rechtes Knie kompensiert X, mach Y") – diese Lücke muss der Nutzer selbst (mit Physio) schließen, z.B. indem er OpenCap-Kurven + OneStep-Symmetriewerte einem Physiotherapeuten vorlegt.

## 3. Die tatsächliche Lücke

**Was NICHT neu gebaut werden sollte:** Pose-Estimation-Engines, Kalibrierungs-Workflows, 3D-Kinematik-aus-Video-Pipelines (OpenCap, Sports2D, Pose2Sim, VisionMD-Gait, OpenCap Monocular decken das technisch bereits solide und offen ab) sowie IMU-Gangparameter-Erfassung (OneStep, Apple/Google/Garmin-Plattformsensoren).

**Die echte Lücke:** Es fehlt die **Interpretations-/Übersetzungsschicht**, die (a) Rohkinematik aus einem Open-Source-Tool wie OpenCap/Sports2D **und** Gangparameter/Symmetrie in ein gemeinsames Datenmodell überführt, (b) gegen alters-/geschlechts-/aktivitätsangepasste **Normbänder** je Gelenk/Parameter vergleicht (nicht nur Rohwerte anzeigt), (c) klinisch bekannte Kompensationsmuster erkennt (z.B. "reduzierte Knieflexion in der Standphase + erhöhte Hüftabduktion rechts = typisches VKB-Vermeidungsmuster"), und (d) daraus in Klartext plausible Ursachen-Hypothesen und Handlungsvorschläge ableitet, longitudinal über Wochen. Kein untersuchtes Tool – weder Open Source noch kommerziell – bietet das für Laien nutzbar aus einem einzigen Handy-Video. Genau diese Lücke (Interpretationsschicht auf bestehender offener Kinematik-Infrastruktur) wäre der sinnvolle Ansatzpunkt für ein neues Projekt, nicht eine weitere Pose-Estimation-Pipeline.

## 4. Quellenliste

- https://journals.plos.org/ploscompbiol/article?id=10.1371%2Fjournal.pcbi.1011462
- https://nmbl.stanford.edu/wp-content/uploads/OpenCapManuscript_higherRes.pdf
- https://www.opencap.ai/
- https://github.com/stanfordnmbl/opencap-core (API-Abfrage)
- https://arxiv.org/abs/2603.24733
- https://github.com/utahmobl/opencap-monocular
- https://www.researchgate.net/publication/395265357_VALIDITY_AND_RELIABILITY_OF_OPENCAP_DURING_SELECTED_LOWER_LIMB_FUNCTIONAL_MOVEMENT_TASKS
- https://joss.theoj.org/papers/10.21105/joss.06849
- https://github.com/davidpagnon/Sports2D
- https://github.com/perfanalytics/pose2sim
- https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9002957/
- https://simtk.org/projects/addbiomechanics
- https://github.com/felixchenier/kineticstoolkit
- https://joss.theoj.org/papers/10.21105/joss.03714
- https://github.com/openjournals/joss-reviews/issues/1778
- https://github.com/cadop/pyCGM
- https://www.nature.com/articles/s41598-025-34912-5
- https://github.com/janstenum/GaitAnalysis-PoseEstimation
- https://journals.plos.org/digitalhealth/article?id=10.1371%2Fjournal.pdig.0000467
- https://github.com/batking24/OpenPose-for-2D-Gait-Analysis
- https://www.onestep.co/resources-blog/leveraging-population-data-in-clinical-practice
- https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12846111/
- https://josr-online.biomedcentral.com/articles/10.1186/s13018-022-03300-4
- https://join.onestep.co/pricing
- https://www.ochy.io/runners
- https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0324499
- https://www.frontiersin.org/journals/bioengineering-and-biotechnology/articles/10.3389/fbioe.2026.1869878/full
- https://www.nature.com/articles/s41598-024-62119-7
- https://www.sciencedirect.com/science/article/pii/S0933365725002672
- https://darimotion.com/
- https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12431465/
- https://valdhealth.com/news/understanding-markerless-motion-capture-with-humantrak
- https://www.athleticbusiness.com/industry-press-room/article/15146783/physimaxs-real-time-movement-assessment-validates-landing-error-scoring-system
- https://kemtai.com/product/computer-vision-rehab/
- https://med-tech.world/news/personalized-care-anywhere-kemtais-vision-for-advanced-physiotherapy/
- https://moveshelf.com/blog/trusted-worldwide
- https://www.qualisys.com/analysis/gait/
- https://www.vicon.com/software/nexus/
- https://www.movella.com/company/press-room/xsens-analyze-2025-movella-launches-first-male-and-female-anatomical-models-for-inertial-motion-capture
- https://www.apple.com/healthcare/docs/site/Measuring_Walking_Quality_Through_iPhone_Mobility_Metrics.pdf
- https://www.nature.com/articles/s41598-023-32550-3
- https://appleheartandmovementstudy.bwh.harvard.edu/celebrating-ahms/
- https://research.google/blog/unlocking-health-insights-estimating-advanced-walking-metrics-with-smartwatches/
- https://www.garmin.com/en-US/garmin-technology/running-science/running-dynamics/ground-contact-time-balance/
- https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10459607/
- https://www.researchgate.net/publication/341832431_Reliability_of_Kinovea_Software_and_Agreement_with_a_Three-Dimensional_Motion_System_for_Gait_Analysis_in_Healthy_Subjects
- https://www.dartfish.com/healthcare/
- https://onform.com/blog/onform-acquires-hudl-technique/
