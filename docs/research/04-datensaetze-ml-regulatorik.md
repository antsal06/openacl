<!-- Recherche-Bericht, erstellt 2026-09-05 durch einen Sonnet-5-Research-Agenten. Quellen am Ende. -->

# Forschungsbericht: Datengrundlagen & ML für Gang-Analyse-App (Referenzvergleich, ACLR-Erkennung)

## 1. Öffentliche Datensätze

**Gesunde Erwachsene (Kinematik/Kinetik, Overground/Laufband, mehrere Geschwindigkeiten)**

- **Fukuchi et al. 2018 (PeerJ)**: 42 gesunde Probanden (24 jung, 18 älter), 3D-Kinematik + Kinetik (Marker + Kraftmessplatten/instrumentiertes Laufband), Overground UND Laufband, mehrere Geschwindigkeiten, Formate C3D + ASCII, auf Figshare (DOI 10.6084/m9.figshare.5722711), CC-Lizenz. Explizit als Referenzdatensatz für Geschwindigkeitseffekte konzipiert. [PeerJ](https://peerj.com/articles/4640/) · [Figshare](https://figshare.com/articles/dataset/A_public_data_set_of_overground_and_treadmill_walking_kinematics_and_kinetics_of_healthy_individuals/5722711/4)
- **Schreiber & Moissenet 2019 (Scientific Data)**: 50 gesunde Erwachsene, 52 Marker Ganzkörper-Kinematik, 3D-GRF/Momente, EMG, 5 Geschwindigkeitsstufen (0–0,4 / 0,4–0,8 / 0,8–1,2 m/s, spontan, schnell) in einer Session. Figshare DOI 10.6084/m9.figshare.7734767. [Nature](https://www.nature.com/articles/s41597-019-0124-4)
- **Gutenberg Gait Database (Horst et al. 2021)**: 350 Gesunde (11–64 Jahre), **nur** GRF/COP (keine Kinematik/EMG trotz Namensähnlichkeit zu anderen Datensätzen), zwei Schritte pro Person, Overground, Selbstwahlgeschwindigkeit. [Nature](https://www.nature.com/articles/s41597-021-01014-6)
- **Lencioni et al. 2019 ("Bovi-Datensatz")**: Kinematik + Kinetik + EMG bei Ebenengehen, Zehen-/Fersengang, Treppauf/-ab, gesunde Probanden verschiedener Altersgruppen, als Normreferenz für pathologischen Gang gedacht, Figshare DOI 10.6084/m9.figshare.c.4494755. [Nature](https://www.nature.com/articles/s41597-019-0323-z)
- **Camargo et al. 2021 (Georgia Tech EPIC Lab)**: 22 gesunde Erwachsene, 3D-Biomechanik + IMU + EMG + Goniometer, viele Terrains (Ebene, Treppen, Rampen, Übergänge), Mendeley Data (3 Teile). [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0021929021001007) · [Mendeley](https://data.mendeley.com/datasets/fcgm3chfff/1)
- **Moore et al. 2015**: 15 Probanden, Laufband, 3 Geschwindigkeiten, mit/ohne longitudinale mechanische Perturbationen, Ganzkörper-Marker + GRF, >5000 normale + >20 000 perturbierte Gangzyklen, PeerJ. [PeerJ](https://peerj.com/articles/918/)
- **Van Criekinge et al. 2023**: 138 gesunde Erwachsene (21–86 J., Lebensspanne) **plus 50 Schlaganfallpatienten**, Ganzkörper-Vicon-Kinematik (PiG), Kinetik, EMG (14 Muskeln), barfuß, Vorzugsgeschwindigkeit, C3D + prozessierte MAT/Excel-Dateien. [Nature](https://www.nature.com/articles/s41597-023-02767-y)
- **MoVi (Ghorbani et al. 2021)**: 90 Akteure, 20 Alltagsbewegungen (u. a. Gehen), synchronisiert Mocap (9 h) + Video (17 h, 4 Kameras) + IMU (6,6 h) – primär für Pose-Estimation/Body-Shape, nicht klinisch. [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC8211257/) · [BioMotionLab](https://www.biomotionlab.ca/movi/)
- **Human3.6M / 3DPW / AMASS / BEDLAM**: reine Computer-Vision-Datensätze (3,6 Mio. Posen bzw. Outdoor-Sequenzen bzw. vereinheitlichte Mocap-Sammlung >300 Probanden/40 h bzw. synthetische Bilder) – nützlich nur als Pretraining-Basis für Pose-Estimation-Modelle, **keine klinische Gangdiagnostik/Norm-Referenz**.

**Pathologisch – Knie/größere Kohorten**

- **GaitRec (Horsak et al. 2020)**: **2084 Patienten** (Hüfte/Knie/Sprunggelenk/Calcaneus, Gelenkersatz, Frakturen, Bandrupturen) + 211 gesunde Kontrollen, bilaterale GRF, 75 732 Gehversuche, CC-BY 4.0, PHAIDRA-Repository. Die Knie-Klasse "K_R" (Bandrupturen/Meniskus) **enthält ACL-Rupturen implizit**, aber nur als Teil einer gemischten Kategorie (mit PCL, Kollateralbändern, Meniskus) – **keine reine, gelabelte ACL-Kohorte**, und nur GRF, keine Gelenkwinkel-Kinematik. [Nature](https://www.nature.com/articles/s41597-020-0481-z) · [PHAIDRA](https://phaidra.fhstp.ac.at/detail/o:4084)
- **GaitRec-VR (2024, Folgearbeit)**: ergänzende 3D-Kinematik-Erhebung (Overground vs. VR-HMD) an gesunden Probanden. [Nature](https://www.nature.com/articles/s41597-024-03939-0)

**Speziell ACLR/ACL-Kinematik – die zentrale Frage**

- **COMPWALK-ACL (2025, Scientific Data)** – bislang der einzige mir bekannte **öffentliche 3D-Kinematik-Gang-Datensatz mit klar gelabelten ACL-Patienten**: 92 Teilnehmer (25 gesunde Erwachsene, 27 gesunde Jugendliche, 40 ACL-Verletzte, davon 27 mit Follow-up 3 Monate nach ACLR), IMU-basiert (Xsens Awinda), Gelenkwinkel + Spatiotemporal-Parameter, drei Ganggeschwindigkeiten (langsam/normal/schnell), Overground. Zenodo DOI 10.5281/zenodo.15624356. **N=40 ACL ist für "echtes" Deep Learning klein, aber ausreichend für klassische ML/Baselines und Proof-of-Concept.** [Nature](https://www.nature.com/articles/s41597-025-06307-8) · [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12764956/)
- **Delaware-Oslo ACL Cohort**: prospektive Kohorte, 300 Athleten (USA/Norwegen), sehr gut publiziert (Kinematik/Kinetik in Dutzenden Papers), aber **die Rohdaten selbst sind nicht öffentlich als Datensatz downloadbar** – nur aggregierte Ergebnisse in Papers. [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC11291834/)
- Weitere ACL-Studien mit z. T. großen N (156 ACLR-Patienten bei Richter et al. 2019, PLOS ONE) beruhen auf **klinikinternen, nicht offen publizierten** Rohdaten. [PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6650047/)
- Cross-sectional ACL-Rupture-Gait-Studien (z. B. Gait deviations bei ACL-Ruptur, männliche Patienten) liefern Befunde, aber meist keine offenen Rohdaten. [PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8709949/)

**Knie-OA**

- **OAI (Osteoarthritis Initiative)**: 4796 Probanden, große Radiologie-/Klinik-/Biospecimen-Datenbank, öffentlich (NIH), **aber keine systematische 3D-Ganganalyse-Kinematik** – nur vereinzelte Sub-Studien (Akzelerometer, Gangtempo) nutzen OAI-Daten für gangbezogene Sekundäranalysen. [NIA](https://www.nia.nih.gov/research/resource/osteoarthritis-initiative-oai)

**Video-Datensätze für abnormalen Gang (Computer Vision)**

- **GAVD (Gait Abnormality Video Dataset, Ranjan et al. 2024)**: größter Video-Datensatz, 1874 Sequenzen, >400 Probanden, klinisch annotiert (normal/abnormal/pathologisch), RGB aus Online-Quellen (Kliniken + Outdoor), nur Links zu Videos (GitHub), keine 3D-Kinematik. Action-Recognition-Modelle (TSN/SlowFast) erreichen 92–94 % Abnormalitätserkennung. **Kein ACL-spezifisches Label bekannt.** [arXiv](https://arxiv.org/abs/2407.04190) · [GitHub](https://github.com/Rahmyyy/GAVD)
- **KOA-PD-NM**: Vision-Datensatz Knie-OA (3 Schweregrade) + Parkinson (3 Schweregrade) + Normal, Mendeley Data. [Mendeley](https://data.mendeley.com/datasets/44pfnysy89/1)
- **PathoGait / MMGS**: Kinect-basierte, überwiegend **simulierte** pathologische Gangarten (Antalgic, Steppage, Trendelenburg, Limping, Knee-Rigidity) von gesunden Probanden nachgestellt – nicht "echte" Patienten. [GitHub](https://github.com/kooksung/pathological_gait_datasets)

**Kinder/CP-Referenz**

- **Gillette/Schwartz-Datenbank** (Basis für GDI): 3351 Kinder/6702 Seiten, Gillette Children's Specialty Healthcare 1994–2007 – **nicht als Rohdatensatz frei downloadbar**, nur als eingebettete Referenzbasis der GDI-Software/Publikationen. [PubMed](https://pubmed.ncbi.nlm.nih.gov/18565753/)

**AddBiomechanics / OpenCap (moderne, große Datensätze)**

- **AddBiomechanics Dataset (Stanford, 2024)**: 273 Probanden, >70 h Motion-/Kraftmessplatten-Daten, >24 Mio. Frames, OpenSim-Skalierung/IK/ID automatisiert, öffentlich unter addbiomechanics.org/download_data.html – **gemischte Population** (auch pathologisch, je nach eingereichten Studien), CC0/offene Lizenz laut Projektziel. [arXiv](https://arxiv.org/html/2406.18537v1) · [AddBiomechanics](https://addbiomechanics.org/)
- **OpenCap (Uhlrich et al. 2023)**: kein "Datensatz" im klassischen Sinn, sondern offene Software (2 iPhones + Laptop) zur markerlosen Kinematik-Erhebung; Validierung **explizit inklusive gesunder und Post-ACLR-Probanden** bei Gehen/Laufen/Hopping, RMSE ≈ 6° (sagittal Knie/Hüfte am besten, r > 0,94). Für das Projekt hoch relevant als Aufnahme-Pipeline, nicht als vorgefertigter Datensatz. [PubMed](https://pubmed.ncbi.nlm.nih.gov/37856442/?dopt=Abstract) · [MDPI-Review](https://www.mdpi.com/2673-7078/5/4/88)
- **OpenCapBench (2024)**: Benchmark, das Pose-Estimation-Backbones gegen biomechanische Kinematik-Genauigkeit testet; Ende-zu-Ende-Training verbessert Fehler von 5,44° auf 3,54°. Direkt relevant, um die eigene Video→Kinematik-Pipeline zu validieren. [ResearchGate](https://www.researchgate.net/publication/381471056_OpenCapBench_A_Benchmark_to_Bridge_Pose_Estimation_and_Biomechanics)

**Fazit zu Frage 1:** Es gibt **einen** öffentlichen Datensatz mit hinreichend klar gelabelten ACLR-Gangdaten (COMPWALK-ACL, N=40 ACL, IMU-Kinematik), sonst nur Ansammlungen, in denen ACL-Fälle in Sammelkategorien "verschwinden" (GaitRec) oder Studien mit größeren N, deren Rohdaten aber nicht offen sind (Delaware-Oslo, Richter et al.). Video-mit-3D-Kinematik-ACL-Datensätze mit ausreichendem N für Deep Learning existieren öffentlich **nicht**.

## 2. Normwert-Kurven ("Normband")

Am besten geeignet als permissiv lizenzierte Normband-Basis:
- **Schreiber & Moissenet 2019** (5 Geschwindigkeiten, Ganzkörper, CC) – deckt Geschwindigkeitsabhängigkeit explizit ab.
- **Fukuchi 2018** (jung + älter, Overground/Laufband) – gut für Alterseffekte und Overground-vs-Laufband-Bias.
- **Van Criekinge 2023** (Lebensspanne 21–86) – gut für Altersnormierung über große Spanne.
- **Lencioni 2019** – zusätzlich EMG als Kontext.

Geschwindigkeitsabhängigkeit: Gangkinematik (v. a. Zeit-Distanz-Parameter, Gelenk-ROM) verändert sich systematisch mit der Geschwindigkeit; Standard-Normierungsansatz ist der **dimensionslose Froude-Ansatz nach Hof** (Fr = v²/(g·L), L = Beinlänge), der "dynamische Ähnlichkeit" zwischen Personen unterschiedlicher Körpergröße herstellt und in Kinderstudien nachweislich Alters-/Größeneffekte in Zeit-Distanz-Parametern eliminiert. [ScienceDirect – Dimensionless Scaling](https://www.sciencedirect.com/science/article/abs/pii/S0167945709000165)

Praktisch für die App: Referenzkurven sollten nicht als einzelnes fixes Band, sondern als **geschwindigkeitsabhängige Regressionsfunktion** (z. B. GAMM/Polynom über Froude-normierte Geschwindigkeit) hinterlegt werden – das deckt sich mit der Fukuchi-Motivation, dass der klassische Vergleich "schnellere Gesunde vs. langsamere Patienten" verzerrt ist.

## 3. Bestehende Analyse-Scores (GDI, GPS, MAP, EVGS, GAI)

- **Gait Deviation Index (GDI, Schwartz & Rozumalski 2008)**: Singulärwertzerlegung (SVD/PCA) auf 3D-Kinematik-Kurven der Gillette-Referenzdatenbank (n=3351 Kinder), projiziert 9 Kinematikkurven auf 15 orthogonale "Gait Features", GDI = Distanzmaß (0–100, 100 = keine Pathologie, 10-Punkte-Schritte = 1 SD). [PubMed](https://pubmed.ncbi.nlm.nih.gov/18565753/)
- **Gait Profile Score (GPS, Baker et al. 2009)**: RMS-Abweichung über 9 Kinematikkurven relativ zu Kontrollmittel, zerlegbar in 9 **Gait Variable Scores (GVS)**, dargestellt als **Movement Analysis Profile (MAP)** (Radar-/Balkendiagramm pro Gelenk/Ebene). [PubMed](https://pubmed.ncbi.nlm.nih.gov/19632117/)
- **Edinburgh Visual Gait Score (EVGS)**: rein visuelle/beobachtende Skala, 17 Items pro Bein über 6 Körperregionen, 3-Punkte-Skala; wurde bereits **automatisiert via OpenPose + Smartphone-Video** reproduziert – direkt relevant als Blaupause für die eigene Video-Pipeline. [PMC – Automated EVGS](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10220686/)
- **Gait Abnormality Index (GAI, 2023)**: neuere, einfachere Alternative auf Z-Score-Basis (statt PCA), korreliert stark mit GPS (r≥0,896), gute Test-Retest-Reliabilität (ICC 0,83), unterscheidet z. B. Knie-OA von Hüft-TEP-Patienten. [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0966636223013097)
- **Open-Source-Implementierung**: **pyCGM2** (Python) implementiert das Conventional Gait Model und wird in Forschung genutzt; GDI/GPS-Berechnung ist damit technisch nachbaubar (SVD/RMS auf Standard-Kinematikkurven), es gibt aber keine "fertige" allgemein anerkannte pip-installierbare GDI/GPS-Bibliothek – Eigenimplementierung nach den publizierten Formeln ist Standardpraxis. [GitHub pyCGM2](https://github.com/pyCGM2/pyCGM2)
- Alle diese Scores wurden ursprünglich auf **markerbasierter** 3D-Ganganalyse entwickelt, sind aber methodisch (PCA/RMS auf normierte Kurven) übertragbar auf Video-Kinematik, sofern die Kurvenqualität ausreichend ist (vgl. OpenCapBench-Fehler ~3,5–6°, vergleichbar mit Inter-Rater-Variabilität klinischer Systeme). Es existieren bereits GDI-/GVI-Vergleiche zwischen marker-basiert und markerlos bei Kindern mit CP. [ScienceDirect – GDI/GVI marker vs. markerless](https://www.sciencedirect.com/science/article/abs/pii/S0966636224006489)

## 4. ML-Ansätze für pathologischen Gang / ACL

- **Halilaj et al. 2018 (Review, J Biomech)**: Grundlagenreview zu Best Practices/Pitfalls von ML in Bewegungsanalyse (Overfitting bei kleinen N, Datenlecks zwischen Trials derselben Person, Notwendigkeit von Interpretierbarkeit). Pflichtlektüre für Projektdesign. [Stanford PDF](https://nmbl.stanford.edu/wp-content/uploads/Halilaj_2018-1.pdf)
- **Horst et al. 2019 (Scientific Reports)**: DNN + Layer-wise Relevance Propagation zeigt, dass Personen anhand von GRF/Gelenkwinkeln **individuell wiedererkennbar** sind ("Gait Signature") – zentral für das "Ideal-Problem" (siehe Punkt 5). Code auf GitHub. [Nature](https://www.nature.com/articles/s41598-019-38748-8) · [GitHub](https://github.com/sebastian-lapuschkin/interpretable-deep-gait)
- **ACL-spezifische ML-Klassifikation**:
  - Richter et al. 2019 (PLOS ONE, N=62 gesund + 156 ACLR): Klassifikationsgenauigkeit 52–81 % (bestes Ergebnis bei Drop-Jump, nicht Gehen). [PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6650047/)
  - Erklärbares ML zur Identifikation ACL-relevanter Gangparameter (2022, Scientific Reports). [Nature](https://www.nature.com/articles/s41598-022-10666-2)
  - Neuere Arbeit (2026, Scientific Reports) zur Klassifikation von ACL-Verletzungsprofilen anhand von Laufanalyse: KNN erreicht bal. accuracy 0,98/AUC 0,99 (Laufen, nicht Gehen); SVM 94,95 % / NN 92,89 % auf 21 biomechanischen Parametern; temporale Variablen (Stride-/Stance-/Swing-Zeit) am wichtigsten. [Nature](https://www.nature.com/articles/s41598-026-44264-3)
  - **Wichtig**: Die meisten hohen Genauigkeiten (>90 %) stammen aus **Jump-/Hop-/Lauf-Aufgaben**, nicht aus Gehen – beim reinen Gehen sind ACLR-Abweichungen deutlich subtiler (kompensiertes "normales" Gangbild), Genauigkeiten bei reinen Gehstudien liegen niedriger.
- **Anomalie-Detektion / One-Class**: One-Class-SVM auf IMU-Gangdaten zur automatisierten Erkennung pathologischer Muster inkl. Erklärbarkeit. [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0268003321001820); LSTM-Autoencoder, nur auf Normgang trainiert, generalisiert über Pathologien hinweg (kein pathologiespezifisches Label nötig) – methodisch der naheliegendste Ansatz für ein Projekt ohne großen ACLR-Datensatz. [Nature Sci Rep](https://www.nature.com/articles/s41598-025-26169-9)
- **Foundation Models für Bewegung**: MotionGPT (NeurIPS 2023) behandelt Bewegung als "Fremdsprache" (Tokenisierung + LLM), trainiert u. a. auf HumanML3D (14 616 Sequenzen aus AMASS/HumanAct12) – bislang **Text-zu-Bewegung-Generierung/-Beschreibung**, nicht klinische Biomechanik-Diagnostik; Transfer auf medizinische Kinematik-Anomalien ist unerprobt. [GitHub](https://github.com/OpenMotionLab/MotionGPT)
- **XAI-Systematic-Review 2025**: 31 Studien zu SHAP/LIME/Grad-CAM/LRP in Gananalyse; Kernprobleme: kleine Stichproben, fehlende Standardisierung/Validierung, kaum reale Deployments. [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12611957/)

**Übertragbarkeit auf Video-Kinematik**: Alle genannten ML-Studien basieren auf Marker-/IMU-Daten mit Winkelfehlern nahe 0. Video-Kinematik (OpenCap-artig) hat 3–6° RMSE – das ist in der Größenordnung der bei Gehen typischen ACLR-vs-gesund-Unterschiede (oft 2–5°, s. u.), d. h. der Messfehler der Video-Pipeline kann echte Effekte teilweise verdecken. Das ist ein **substanzielles Risiko** für ML auf reinen Gehdaten aus Video.

## 5. Das "Ideal"-Problem

- Horst et al. 2019 zeigen, dass **individuelle Gangmuster stabil und identifizierend** sind – ein reines Populationsmittel ("Ideal") ignoriert, dass gesunde Personen sich systematisch und dauerhaft voneinander unterscheiden. [Nature](https://www.nature.com/articles/s41598-019-38748-8)
- Interindividuelle Variabilität bei Gesunden ist beträchtlich: 90 %-Prädiktionsbänder für Knie-Kinematik liegen bei ca. ±15° (Flexion/Extension), ±10° (Innen-/Außenrotation), ±6° (Ab-/Adduktion) – deutlich breiter als viele pathologische Effektgrößen. [PubMed – Knee Kinematics Biplane](https://pubmed.ncbi.nlm.nih.gov/32491153/)
- Klinische Ganglabore interpretieren daher praktisch **nie** nur gegen ein Populationsmittel, sondern kombinieren: Normband (± SD/Prädiktionsintervall) **+ Gegenseite** (sofern nicht mitbetroffen) **+ Verlauf** (Longitudinalvergleich zur eigenen Baseline) **+ klinischer Kontext** (Anamnese, Kraft, Beweglichkeit, PROMs).
- Für ACLR ist die **Gegenseite als Referenz problematisch**: Meta-Analysen zeigen signifikante Kompensationseffekte im nicht-operierten Bein (Peak-Knieflexion ACLR vs. kontralateral: −2,63° im Mittel, aber auch veränderte Belastung des "gesunden" Beins mit erhöhtem späteren OA-Risiko dort). D. h. "die andere Seite ist gesund" ist nach ACLR eine unsichere Annahme, besonders akut/mittelfristig postoperativ. [PMC – Meta-Analyse](https://pmc.ncbi.nlm.nih.gov/articles/PMC12733360/) · [PMC – Aberrant Gait Biomechanics](https://pmc.ncbi.nlm.nih.gov/articles/PMC8976749/)
- **Personalisierte Normmodelle**: Die Literatur favorisiert zunehmend regressionsbasierte, auf Alter/Größe/Geschlecht/Geschwindigkeit konditionierte Normkurven statt einfacher Populationsmittel (vgl. GDI/GPS-Ansatz selbst, der pro-Kurve-PCA nutzt, sowie Froude-Normierung). Ein "prä-Verletzungs-Baseline"-Ansatz (eigene Kinematik vor der Verletzung) wäre ideal, ist aber in der Praxis fast nie verfügbar (niemand filmt sich prophylaktisch).

**Praktische Konsequenz fürs Projekt**: Der defensibelste Vergleichsansatz ist eine Kombination aus (a) geschwindigkeits-/alterskonditioniertem Normband aus mehreren gepoolten Gesunden-Datensätzen, (b) Longitudinalverlauf der eigenen Werte über Wochen (stärkstes Signal bei Reha-Fortschritt), (c) Seitenvergleich als Zusatzinformation (mit Vorsicht bei akuten ACLR-Fällen), und (d) ein unüberwachter Anomalie-Score (Autoencoder/Distanzmaß wie GDI/GAI) statt eines "harten" ACLR-Klassifikators.

## 6. LLM-basierte Interpretation

- Erste explorative Arbeit: ChatGPT-4o wurde getestet, biomechanische Ganganalysen aus 3D-Mocap-Daten zu erzeugen; Vergleich der Bewertungen mit Streuung menschlicher Rater. Ergebnis: LLM-Output ist plausibel, aber Variabilität/Fehleranfälligkeit ähnlich der menschlichen Beurteilervarianz – kein etabliertes "GaitGPT"-Produkt. [ResearchGate](https://www.researchgate.net/publication/395231655_Exploring_Large_Language_Models_for_Automated_Gait_Analysis)
- Parkinson-Gang-Projekt: Kombiniert Videoanalyse-Output + Patienten-Metadaten → Embeddings → TinyLlama-1.1B zur Generierung natürlichsprachlicher klinischer Berichte samt Empfehlungen – ein konkretes Beispiel für die angedachte Architektur "Kinematik-Layer → LLM-Report". [arXiv](https://arxiv.org/pdf/2512.04425)
- Generelles Risiko (auch in Radiologie-LLM-Reviews dokumentiert): Halluzination, Bias, mangelnde Validierung – explizite Warnung, dass Trustworthiness/Fidelity vor klinischem Einsatz sichergestellt werden muss. Kein GaitGPT/BioMechGPT-Produkt mit Marktreife bekannt; das Feld ist 2025/2026 noch explorativ (Preprints, kleine Studien).
- Fazit: LLM-Report-Generierung ist technisch machbar und es gibt erste Prototypen, aber **ausschließlich als "Übersetzungsschicht"** über bereits berechnete, deterministische Scores (GDI/GPS/Z-Scores) – nicht als eigenständige Diagnosequelle, gerade wegen Halluzinationsrisiko.

## 7. Regulatorik (kurz)

- **EU MDR**: Software gilt als Medizinprodukt, sobald sie für einen "medizinischen Zweck" bestimmt ist (Diagnose, Prävention, Überwachung, Prognose, Behandlung). Reine Wellness-/Fitness-/Lifestyle-Information (Schrittzähler, allgemeine Trends) fällt **nicht** darunter. Sobald Software klinische Daten verarbeitet/interpretiert, um Diagnose- oder Therapieentscheidungen zu unterstützen (Regel 11), landet sie mindestens in **Klasse IIa** – höher, wenn Fehlentscheidungen zu Tod/irreversiblem Schaden führen könnten. [NAMSA](https://namsa.com/resources/blog/eu-mdr-and-ivdr-classifying-medical-device-software-mdsw/) · [Quickbird Medical](https://quickbirdmedical.com/en/medical-device-class-software-app-mdr/)
- **USA/FDA**: Analog über SaMD/510(k)-Pfad; digitale Gang-Biomarker werden zunehmend eingereicht, aber häufige Mängel sind fehlende Validierung unter Alltagsbedingungen (z. B. nur Laufband-validiert, nicht "real world"). [FDA-Guidance-Kontext](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/deciding-when-submit-510k-software-change-existing-device)
- **Open-Source-Praxis (OpenCap-Modell)**: Positioniert sich klar als **Forschungswerkzeug** (vergleichbar "Research Use Only" bei IVD-Produkten – "nicht für Diagnostik"), was Entwicklern erlaubt, ohne Zulassungsverfahren zu iterieren, solange keine Diagnose-/Therapieaussage getroffen wird. [FDA RUO-Leitfaden (Analogie)](https://www.fda.gov/files/medical%20devices/published/Distribution-of-In-Vitro-Diagnostic-Products-Labeled-for-Research-Use-Only-or-Investigational-Use-Only---Guidance-for-Industry-and-FDA-Staff.pdf)
- **Empfehlung fürs Projekt**: Explizite Positionierung als "Wellness/Self-Tracking/Informationsangebot" (Verlauf zeigen, Normband zum Vergleich, "kein Ersatz für ärztliche/physiotherapeutische Diagnose") hält das Projekt voraussichtlich außerhalb MDR/FDA-Pflicht – sobald aber ein "ACLR-Risiko-Score" oder eine explizite Therapieempfehlung ausgegeben wird, kippt die Einordnung in Richtung Medizinprodukt.

## Tabelle: Datensätze im Überblick

| Name | N | Population | Modalität | Lizenz | ACL? | URL |
|---|---|---|---|---|---|---|
| Fukuchi 2018 | 42 | gesund (jung+alt) | Kinematik+Kinetik, Overground+Laufband | CC (Figshare) | Nein | [Figshare](https://figshare.com/articles/dataset/A_public_data_set_of_overground_and_treadmill_walking_kinematics_and_kinetics_of_healthy_individuals/5722711/4) |
| Schreiber & Moissenet 2019 | 50 | gesund | Ganzkörper-Kin., GRF, EMG, 5 Speeds | CC (Figshare) | Nein | [Nature](https://www.nature.com/articles/s41597-019-0124-4) |
| Gutenberg Gait DB 2021 | 350 | gesund (11–64J) | nur GRF/COP | Figshare | Nein | [Nature](https://www.nature.com/articles/s41597-021-01014-6) |
| Lencioni 2019 | mehrere Altersgruppen | gesund | Kin.+Kin.+EMG, Ebene/Treppe | Figshare | Nein | [Nature](https://www.nature.com/articles/s41597-019-0323-z) |
| Camargo 2021 | 22 | gesund | Kin.+Kin.+IMU+EMG, Terrains | Mendeley (offen) | Nein | [Mendeley](https://data.mendeley.com/datasets/fcgm3chfff/1) |
| Moore 2015 | 15 | gesund | Vollmarker+GRF, Perturbation | PeerJ/Dataverse | Nein | [PeerJ](https://peerj.com/articles/918/) |
| Van Criekinge 2023 | 138+50 | gesund + Stroke | Vollkörper-Kin.+Kin.+EMG | Figshare | Nein | [Nature](https://www.nature.com/articles/s41597-023-02767-y) |
| AddBiomechanics 2024 | 273 | gemischt | OpenSim IK/ID, Mocap+GRF | offen (addbiomechanics.org) | teilweise möglich | [arXiv](https://arxiv.org/html/2406.18537v1) |
| MoVi 2021 | 90 | gesund | Mocap+Video+IMU (Alltag) | offen | Nein | [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC8211257/) |
| GaitRec 2020 | 2084 Pat. + 211 gesund | Hüfte/Knie/Sprg./Calcaneus | bilaterale GRF | CC-BY 4.0 | indirekt (K_R-Sammelklasse) | [PHAIDRA](https://phaidra.fhstp.ac.at/detail/o:4084) |
| COMPWALK-ACL 2025 | 92 (40 ACL) | gesund + ACL(D/R) | IMU-Kinematik, 3 Speeds | Zenodo (offen) | **Ja, explizit** | [Zenodo/Nature](https://www.nature.com/articles/s41597-025-06307-8) |
| Delaware-Oslo ACL Cohort | 300 | ACLR-Athleten | Kin./Kin. (nur publiziert) | nicht offen als Rohdatensatz | Ja | [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC11291834/) |
| OAI | 4796 | Knie-OA | klinisch/Bildgebung, kaum Gang-Kin. | öffentlich (NIH) | Nein (OA, nicht ACL) | [NIA](https://www.nia.nih.gov/research/resource/osteoarthritis-initiative-oai) |
| GAVD 2024 | >400 | gemischt pathologisch | Video (RGB, online) | Links/GitHub | unbekannt/unwahrscheinlich | [arXiv](https://arxiv.org/abs/2407.04190) |
| KOA-PD-NM | – | Knie-OA, Parkinson, gesund | Video-Skelett | Mendeley | Nein | [Mendeley](https://data.mendeley.com/datasets/44pfnysy89/1) |
| PathoGait/MMGS | 27+ | gesund, simulierte Pathologie | Kinect-Skelett | GitHub | Nein | [GitHub](https://github.com/kooksung/pathological_gait_datasets) |
| Gillette/Schwartz-Ref. | 3351 Kinder | gemischt pädiatrisch | Kin. (GDI-Basis) | nicht als Rohdaten offen | Nein | [PubMed](https://pubmed.ncbi.nlm.nih.gov/18565753/) |
| Human3.6M/3DPW/AMASS/BEDLAM | groß | allgemeine Bewegung | Video/Mocap (CV) | teils offen, teils registrierungspflichtig | Nein | – |

## Empfehlung

**Als Normband nutzen:** Kombination aus Fukuchi 2018 (Alters-/Geschwindigkeitseffekte, Overground+Laufband), Schreiber & Moissenet 2019 (Ganzkörper, 5 Geschwindigkeiten, EMG optional) und Van Criekinge 2023 (Lebensspanne). Gepoolt und Froude-normiert ergibt das ein robustes, permissiv lizenziertes Normband über Alter und Geschwindigkeit hinweg.

**Für ML-Prototyp:** GaitRec (für allgemeine "gesund vs. Knie-pathologisch"-Unterscheidung, große Fallzahl, aber nur GRF, keine reine ACL-Klasse) und COMPWALK-ACL (für den spezifischen ACL-Anwendungsfall, aber klein und IMU- statt videobasiert). Realistisch ist ein **Anomalie-/Distanz-Score** (GDI/GAI-artig oder Autoencoder auf Normgang) deutlich eher zu erreichen als ein belastbarer, video-basierter "ACLR-vs-gesund"-Klassifikator – dafür fehlt schlicht ein ausreichend großer, öffentlicher Video-Kinematik-ACL-Datensatz. Die in der Literatur berichteten hohen Genauigkeiten (>90 %) stammen fast durchgängig aus Sprung-/Lauf-/Change-of-Direction-Aufgaben mit Marker-/IMU-Präzision, nicht aus reinem Gehen mit Video-Kinematik-Rauschen von 3–6°.

**Ehrliche Einschätzung des robustesten Vergleichsdesigns:** Für den Anwendungsfall (Handy-Video, Reha-Verlauf, ACLR-Kontext) ist ein reiner "ACLR-Klassifikator" mit öffentlichen Daten aktuell **nicht seriös realisierbar** – zu wenig Daten, zu großes Signal-Rausch-Problem bei Video-Kinematik im Gehen. Am belastbarsten ist eine **vierschichtige Kombination**: (1) Populations-Normband (geschwindigkeits-/altersnormiert) für Grobeinordnung, (2) Seitenvergleich als Zusatzsignal (mit Warnhinweis bei akuten Fällen, da Gegenseite kompensiert), (3) individueller Verlauf über Wochen als Hauptsignal für Reha-Fortschritt (umgeht das "Ideal-Problem" komplett, da man gegen sich selbst vergleicht), (4) ein unüberwachter Abweichungs-Score (GDI/GAI-artig, ggf. Autoencoder) statt eines binären ACLR-Detektors. Ein echter ACLR-Klassifikator wäre nur nach eigener Datenerhebung (Kooperation mit Physiotherapiepraxen/Uni-Sportmedizin, idealerweise mit OpenCap-artiger Doppel-Handy-Aufnahme validiert gegen Referenzsystem) realistisch – dafür liefert COMPWALK-ACL immerhin ein methodisches Vorbild (IMU + drei Geschwindigkeiten + Follow-up-Design).

Für LLM-Interpretation: als reine Report-Generierungsschicht über deterministische Scores sinnvoll und in ersten Prototypen erprobt, aber mit Halluzinationsrisiko – Ausgabe sollte immer die zugrundeliegenden Zahlen mit Quelle zeigen, nie freie Diagnoseaussagen treffen, um regulatorisch im Wellness-Bereich zu bleiben.

---

### Vollständige Quellenliste

- [PeerJ – Fukuchi 2018](https://peerj.com/articles/4640/) · [Figshare Fukuchi](https://figshare.com/articles/dataset/A_public_data_set_of_overground_and_treadmill_walking_kinematics_and_kinetics_of_healthy_individuals/5722711/4)
- [Nature – Schreiber & Moissenet 2019](https://www.nature.com/articles/s41597-019-0124-4)
- [Nature – GaitRec 2020](https://www.nature.com/articles/s41597-020-0481-z) · [PHAIDRA GaitRec](https://phaidra.fhstp.ac.at/detail/o:4084) · [Nature GaitRec-VR 2024](https://www.nature.com/articles/s41597-024-03939-0)
- [Nature – Gutenberg Gait Database 2021](https://www.nature.com/articles/s41597-021-01014-6)
- [ScienceDirect – Camargo 2021](https://www.sciencedirect.com/science/article/abs/pii/S0021929021001007) · [Mendeley Camargo](https://data.mendeley.com/datasets/fcgm3chfff/1)
- [arXiv – AddBiomechanics Dataset](https://arxiv.org/html/2406.18537v1) · [AddBiomechanics.org](https://addbiomechanics.org/) · [PLOS ONE AddBiomechanics Methode](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0295152)
- [PubMed – OpenCap Uhlrich 2023](https://pubmed.ncbi.nlm.nih.gov/37856442/?dopt=Abstract) · [MDPI – OpenCap Review](https://www.mdpi.com/2673-7078/5/4/88) · [Frontiers – OpenCap Scoping Review](https://www.frontiersin.org/journals/digital-health/articles/10.3389/fdgth.2026.1882536/full)
- [ResearchGate – OpenCapBench](https://www.researchgate.net/publication/381471056_OpenCapBench_A_Benchmark_to_Bridge_Pose_Estimation_and_Biomechanics)
- [Nature – COMPWALK-ACL 2025](https://www.nature.com/articles/s41597-025-06307-8) · [PMC COMPWALK-ACL](https://pmc.ncbi.nlm.nih.gov/articles/PMC12764956/)
- [arXiv – GAVD](https://arxiv.org/abs/2407.04190) · [GitHub GAVD](https://github.com/Rahmyyy/GAVD)
- [PeerJ – Moore 2015](https://peerj.com/articles/918/)
- [Nature – Van Criekinge 2023](https://www.nature.com/articles/s41597-023-02767-y)
- [Nature – Lencioni 2019](https://www.nature.com/articles/s41597-019-0323-z)
- [PMC – Delaware-Oslo ACL Cohort](https://pmc.ncbi.nlm.nih.gov/articles/PMC11291834/)
- [NIA – Osteoarthritis Initiative](https://www.nia.nih.gov/research/resource/osteoarthritis-initiative-oai)
- [PubMed – GDI Schwartz & Rozumalski 2008](https://pubmed.ncbi.nlm.nih.gov/18565753/)
- [PubMed – GPS Baker 2009](https://pubmed.ncbi.nlm.nih.gov/19632117/)
- [GitHub – pyCGM2](https://github.com/pyCGM2/pyCGM2)
- [Stanford PDF – Halilaj 2018 Review](https://nmbl.stanford.edu/wp-content/uploads/Halilaj_2018-1.pdf)
- [Nature – Horst 2019 Gait Signature](https://www.nature.com/articles/s41598-019-38748-8) · [GitHub interpretable-deep-gait](https://github.com/sebastian-lapuschkin/interpretable-deep-gait)
- [Nature – ACL-Klassifikation Laufanalyse 2026](https://www.nature.com/articles/s41598-026-44264-3)
- [Nature – Explainable ML ACL Injury Parameters 2022](https://www.nature.com/articles/s41598-022-10666-2)
- [PMC – Richter et al. 2019 ACL Klassifikation](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6650047/)
- [PMC – Kotsifaki Biomechanical Assessment Tools Review](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12553509/)
- [ScienceDirect – One-Class SVM IMU pathologischer Gang](https://www.sciencedirect.com/science/article/pii/S0268003321001820)
- [Nature Sci Rep – LSTM-Autoencoder Gait Anomaly](https://www.nature.com/articles/s41598-025-26169-9)
- [ResearchGate – LLM Automated Gait Analysis](https://www.researchgate.net/publication/395231655_Exploring_Large_Language_Models_for_Automated_Gait_Analysis)
- [arXiv – LLM Parkinson Gait TinyLlama](https://arxiv.org/pdf/2512.04425)
- [NAMSA – EU MDR/IVDR Software-Klassifikation](https://namsa.com/resources/blog/eu-mdr-and-ivdr-classifying-medical-device-software-mdsw/)
- [Quickbird Medical – MDR Software-Klassen](https://quickbirdmedical.com/en/medical-device-class-software-app-mdr/)
- [FDA – RUO/IUO Guidance](https://www.fda.gov/files/medical%20devices/published/Distribution-of-In-Vitro-Diagnostic-Products-Labeled-for-Research-Use-Only-or-Investigational-Use-Only---Guidance-for-Industry-and-FDA-Staff.pdf)
- [FDA – 510(k) Software Change Guidance](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/deciding-when-submit-510k-software-change-existing-device)
- [ScienceDirect – Dimensionless Scaling Gait (Hof/Froude)](https://www.sciencedirect.com/science/article/abs/pii/S0167945709000165)
- [PubMed – Knee Kinematics Variabilität (Biplane)](https://pubmed.ncbi.nlm.nih.gov/32491153/)
- [ScienceDirect – Gait Abnormality Index 2023](https://www.sciencedirect.com/science/article/pii/S0966636223013097)
- [PMC – Automated EVGS via OpenPose](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10220686/)
- [ScienceDirect – GDI/GVI marker vs. markerless CP](https://www.sciencedirect.com/science/article/abs/pii/S0966636224006489)
- [GitHub – MotionGPT](https://github.com/OpenMotionLab/MotionGPT)
- [PMC – MoVi Dataset](https://pmc.ncbi.nlm.nih.gov/articles/PMC8211257/) · [BioMotionLab MoVi](https://www.biomotionlab.ca/movi/)
- [PMC – Meta-Analyse ACLR vs. Kontralaterales Bein](https://pmc.ncbi.nlm.nih.gov/articles/PMC12733360/)
- [PMC – Aberrant Gait Biomechanics ACLR Treadmill](https://pmc.ncbi.nlm.nih.gov/articles/PMC8976749/)
- [PMC – XAI Gait Systematic Review 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12611957/)
- [PMC – Gait Deviations ACL Rupture Cross-Sectional](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8709949/)
- [Mendeley – KOA-PD-NM Dataset](https://data.mendeley.com/datasets/44pfnysy89/1)
- [GitHub – PathoGait/MMGS pathological_gait_datasets](https://github.com/kooksung/pathological_gait_datasets)
