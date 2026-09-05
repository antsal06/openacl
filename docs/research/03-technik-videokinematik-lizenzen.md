<!-- Recherche-Bericht, erstellt 2026-09-05 durch einen Sonnet-5-Research-Agenten. Quellen am Ende. -->

Der session-weite WebSearch-Kontingent ist erschöpft (200/200, geteilt über alle fünf parallelen Recherche-Agenten). Ich habe aber bereits sehr umfangreiches, gut belegtes Material aus den fünf abgeschlossenen Recherchen und fasse es jetzt zum vollständigen Bericht zusammen. Wo Lücken bleiben (z.B. exakte FPS-Zahlen für WHAM/GVHMR auf bestimmten GPUs, Apple-Vision-Framework-Validierungsstudien, Primärquelle der 6-Hz-Konvention), kennzeichne ich das explizit statt zu spekulieren.

---

# Markerlose Videokinematik für Kreuzband-Reha — Stand der Technik 2025/2026

## 1. Stand der Technik

### 1a) 2D-Pose-Schätzung

| Modell | Keypoints/Fuß | Genauigkeit | Geschwindigkeit | Lizenz |
|---|---|---|---|---|
| **RTMPose/RTMW/RTMO** (MMPose) | Halpe-26 oder COCO-WholeBody-133 (Ferse+Zehen nur in Wholebody/Halpe-Varianten) | RTMW: 67,0% AP COCO-WholeBody; RTMPose-x: 65,3% AP [arXiv 2407.08634](https://arxiv.org/pdf/2407.08634) | Echtzeitfähig, 130+ FPS (RTMW) | **Apache 2.0** [GitHub](https://github.com/open-mmlab/mmpose/tree/main/projects/rtmpose) |
| **ViTPose/ViTPose++** | über MoE auch COCO-WholeBody (Fuß möglich) | ViTPose++: 81,1 AP COCO test-dev; ViTPose-H: 79,1 AP bei 241 FPS [arXiv 2212.04246](https://arxiv.org/pdf/2212.04246), [arXiv 2204.12484](https://arxiv.org/pdf/2204.12484) | GPU nötig für Echtzeit bei großen Varianten | **Apache 2.0** [GitHub](https://github.com/ViTAE-Transformer/ViTPose/blob/main/LICENSE) |
| **Sapiens** (Meta) | bis 308 Keypoints inkl. Füße | 300 Mio. Bilder pretrained, 1024×1024 nativ, sehr hohe Auflösung [arXiv 2408.12569](https://arxiv.org/html/2408.12569v1) | GPU nötig (1B-Parameter-Modelle) | **CC-BY-NC-SA 4.0 — nicht kommerziell** [HuggingFace](https://huggingface.co/facebook/sapiens-pose-0.6b) |
| **MediaPipe Pose/BlazePose** | 33 Keypoints, **explizit Ferse+Zehenspitze** je Fuß | ~78% COCO-Genauigkeit (unter GPU-Modellen), aber praxistauglich | Läuft on-device (CPU/Mobile) [Google Research Blog](https://research.google/blog/on-device-real-time-body-pose-tracking-with-mediapipe-blazepose/) | **Apache 2.0** |
| **OpenPose** (CMU) | BODY_25: 6 Fuß-Keypoints (Ferse+Groß-/Kleinzehe je Seite) — historischer Biomechanik-Standard | solide, aber überholt | mittel | **Nicht-kommerziell**, kommerzielle Lizenz 25.000 USD/Jahr, **Sport-Anwendungen explizit ausgeschlossen** [GitHub LICENSE](https://github.com/CMU-Perceptual-Computing-Lab/openpose/blob/master/LICENSE) — für ein Reha/Gang-Projekt besonders ungünstig |
| **DWPose** | COCO-WholeBody | DWPose-l: 66,5% AP (übertrifft Lehrer RTMPose-x); DWPose-m: 60,6 AP bei 2,2 GFLOPs [arXiv 2307.15880](https://arxiv.org/pdf/2307.15880) | leicht, auch schwächere Hardware | **Apache 2.0** |
| **HRNet** | nur COCO-17 (kein Fuß nativ) | 77,0 AP COCO test-dev2017 [CVPR-Paper](https://openaccess.thecvf.com/content_CVPR_2019/papers/Sun_Deep_High-Resolution_Representation_Learning_for_Human_Pose_Estimation_CVPR_2019_paper.pdf) | mittel | vermutlich MIT-artig, im Einzelfall verifizieren |
| **YOLO11/YOLOv8-Pose** (Ultralytics) | COCO-17 | YOLO11m übertrifft YOLOv8m bei 22% weniger Parametern [Ultralytics](https://www.ultralytics.com/blog/how-to-use-ultralytics-yolo11-for-pose-estimation) | schnell, CPU-tauglich | **AGPL-3.0** oder kostenpflichtige Enterprise-Lizenz [Ultralytics Docs](https://docs.ultralytics.com/models/yolo11) |

**Kernaussage:** Für Gangereignis-Erkennung sind Fuß-Keypoints (Ferse/Zehen) essenziell — das schließt reine COCO-17-Modelle (HRNet, YOLO-Standard) aus und favorisiert MediaPipe, RTMW/DWPose (Wholebody) oder OpenPose BODY_25.

### 1b) Monokulare 3D-Methoden (körpermodellbasiert)

| Methode | Ansatz | Code-Lizenz | Abhängigkeit |
|---|---|---|---|
| **WHAM** (CVPR 2024) | 2D-Keypoint-Sequenz + Mocap-Prior + SLAM (DPVO/DROID-SLAM) für Weltkoordinaten [arXiv 2312.07531](https://arxiv.org/pdf/2312.07531) | **MIT** | lädt SMPL-Gewichte |
| **TRAM** (ECCV 2024) | SLAM+ZoeDepth für Kamera/Skalierung, VIMO-Transformer für Körperbewegung, −60% globaler Fehler ggü. Vorgängern [Projektseite](https://yufu-wang.github.io/tram4d/) | **MIT** | lädt SMPL-Gewichte |
| **GVHMR** (SIGGRAPH Asia 2024/TPAMI 2026) | "Gravity-View"-Koordinatensystem, SOTA bei Genauigkeit UND Geschwindigkeit [GitHub](https://github.com/zju3dv/GVHMR) | **Eigene Lizenz: nicht-kommerziell, Derivate müssen offen bleiben** [LICENSE](https://github.com/zju3dv/GVHMR/blob/main/LICENSE) | SMPL |
| **4D-Humans/HMR2.0** (Berkeley) | vollständig transformerbasiert, Tracking über Zeit [arXiv 2305.20091](https://arxiv.org/html/2305.20091v3) | **MIT**, benötigt separat lizenziertes SMPL | SMPL |
| **MotionBERT** (ICCV 2023) | Dual-stream Spatio-Temporal Transformer, 2D→3D-Lifting-Pretraining [arXiv 2210.06551](https://arxiv.org/abs/2210.06551) | **Apache 2.0** | kein SMPL zwingend |
| **SMPLer-X** (NeurIPS 2023) | Generalist-Foundation-Modell, ViT-Huge, 4,5M Trainingsinstanzen [arXiv 2309.17448](https://arxiv.org/abs/2309.17448) | nicht eindeutig als Apache bestätigt | SMPL-X |
| **Multi-HMR / Multi-HMR 2** (NAVER, ECCV 2024/2026) | Single-Shot Multi-Person SMPL-X-Mesh [arXiv 2402.14654](https://arxiv.org/abs/2402.14654) | **CC BY-NC-SA 4.0 — nicht kommerziell** | SMPL-X |
| **TokenHMR** (CVPR 2024, MPI) | tokenisierte Pose-Repräsentation | **nur Forschung** | SMPL |
| **NLF** (NeurIPS 2024, Sárándi/Pons-Moll) | kontinuierliche Punktabfrage im Körpervolumen [GitHub](https://github.com/isarandi/nlf) | **nur nicht-kommerzielle Forschung** | eigenes Modell |
| **PromptHMR** (CVPR 2025) | promptbar via Bounding-Box/Sprache, robust bei Okklusion [arXiv 2504.06397](https://arxiv.org/abs/2504.06397) | — | SMPL |
| **CoMotion** (Apple 2024) | Multi-Personen-Tracking direkt aus neuem Frame [Apple ML Research](https://machinelearning.apple.com/research/comotion-concurrent-3d-motion) | eigene Apple-Lizenz | eigenes Modell |
| **SAM 3D Body** (Meta, CVPR 2026 Oral) | neue **Momentum Human Rig (MHR)**-Repräsentation, entkoppelt Skelett/Form, übertrifft z.T. Video-Methoden trotz Single-Image [arXiv 2602.15989](https://arxiv.org/abs/2602.15989) | **explizit open-source** (Code+Modell) | eigenes Modell (MHR statt SMPL!) |

Weitere 2025/2026-Neuerscheinungen: RAM ([arXiv 2603.19929](https://arxiv.org/pdf/2603.19929)), DuoMo ([arXiv 2603.03265](https://arxiv.org/pdf/2603.03265)), SAM-Body4D ([arXiv 2512.08406](https://arxiv.org/pdf/2512.08406)), OnlineHMR ([arXiv 2603.17355](https://arxiv.org/pdf/2603.17355)), Human3R ([arXiv 2510.06219](https://arxiv.org/pdf/2510.06219)).

**Kritischer Punkt:** Die MIT/Apache-Code-Lizenz von WHAM/TRAM/4D-Humans ändert nichts daran, dass zur Laufzeit SMPL-Modelldateien geladen werden — und deren Lizenz verbietet jede kommerzielle Nutzung (siehe Lizenzkapitel). **SAM 3D Body** ist die einzige aktuelle Methode in dieser Liste, die ein eigenes, explizit offenes Körpermodell (MHR) statt SMPL nutzt — damit potenziell der interessanteste Kandidat für ein permissiv lizenziertes Projekt, sofern die MHR-Lizenzbedingungen sich bestätigen.

**Biomechanische Validierung — der eigentlich entscheidende Punkt:**

- **OpenCapBench** (Gozlan/Falisse/Uhlrich/Delp et al., WACV 2025) bewertet Pose-Modelle nicht nach MPJPE, sondern nach dem resultierenden Gelenkwinkelfehler nach OpenSim-IK. Kernaussage: Standard-Keypoint-Sets (z.B. COCO-17) sind **zu spärlich für präzise Biomechanik**. Ihr Modell **SynthPose** (dichtere, anatomisch-informierte Keypoints) halbiert den Gelenkwinkelfehler gegenüber Standard-Pipelines ("~2x reduziert") [arXiv 2406.09788](https://arxiv.org/abs/2406.09788).
- **Warum MPJPE ≠ Winkelfehler:** MPJPE misst euklidische Distanz von (oft virtuellen, aus Vertex-Regressoren abgeleiteten) Gelenkzentren in mm. Ein klinischer Gelenkwinkel ist die Differenz zweier Segmentorientierungen um eine definierte anatomische Achse. Ein SMPL-Kugelgelenk am Knie hat z.B. keine echte anatomische Flexionsachse — ein Modell mit niedrigem MPJPE kann trotzdem großen Winkelfehler produzieren, wenn die Rotationsachse falsch definiert ist. Das ist der methodische Grund, warum OpenCapBench explizit auf Nach-IK-Winkelfehler umgestellt hat [arXiv 2406.09788](https://arxiv.org/abs/2406.09788).
- **Direct Clinical Joint Angle Extraction** (arXiv 2607.17639, ~2026): extrahiert Winkel direkt aus Rotationsmatrizen eines Körpermodells via kleiner Kalibriertabelle statt vollem OpenSim-IK. MAE gg. Marker: Knieflexion 4,3–5,3° (r≈0,98), Hüftflexion 7,5–8,0° (r≈0,98), Sprunggelenk 4,0–4,8° (r≈0,81–0,83), Mittel über 15 Freiheitsgrade 4,50°. Kreuzvalidiert mit **SAM 3D Body/MHR** [arXiv 2607.17639](https://arxiv.org/html/2607.17639).
- **"3D Kinematics Estimation from Video with a Biomechanical Model and Synthetic Training Data"**: biomechanik-bewusstes Framework, übertrifft laut Abstract SOTA-Mocap-Methoden bei Winkel- UND Positionsfehler [arXiv 2402.13172](https://arxiv.org/html/2402.13172v4) — merkt selbst an, dass die Validierung bei **pathologischen Bewegungsmustern** (z.B. Reha-Patienten) noch unzureichend ist, ein wichtiger Vorbehalt für den Kreuzband-Use-Case.
- Weitere OpenCap-Zahlen: RMSE Knieflexion 5,7°/6,6° beim Gehen, beim Radfahren (schwierigere Bewegung) 9,3°±3,8° (links)/10,2°±4,3° (rechts) [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0021929024002781).

### 1c) Multi-View-Pipelines (2+ Kameras)

**OpenCap** (Stanford, Uhlrich/Delp/Falisse-Gruppe, PLOS Comp Biol 2023): Pipeline intern = 2D-Pose (OpenPose oder HRNet) → Multi-View-Triangulation zu spärlichen 3D-Keypoints → **LSTM-"Marker Augmenter"** rekonstruiert 43 anatomische Marker aus 20 Video-Keypoints → OpenSim-Scaling + Inverse Kinematics. Der Marker-Augmenter reduziert den mittleren Kinematikfehler von 9,6° (Max 43,1°, nur rohe Keypoints) auf 4,1° (Max 8,7°) [PMC12198419](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12198419/), [GitHub marker-enhancer](https://github.com/stanfordnmbl/marker-enhancer). Code (opencap-core, opencap-processing): **Apache 2.0**. Gehosteter Web-Service (app.opencap.ai) ist "freely available for **educational and research use only**", kommerzielle Anfragen laufen über einen separaten "commercial arm" [Nutzungsbedingungen](https://www.opencap.ai/terms-conditions).

Besonders relevant für den 1-Handy-Use-Case: **"OpenCap Monocular"** (Utah MOBL Lab, 2026) — Kinematik UND Kinetik (inkl. Bodenreaktionskräfte) aus **einem** Smartphone-Video. Gelenkwinkelfehler beim Gehen: **5,6° monokular vs. 5,2° bei Zwei-Kamera-OpenCap** — nur geringer Genauigkeitsverlust, bei Kinetik teils sogar besser [Projektseite](https://utahmobl.github.io/OpenCap-monocular-project-page/), [GitHub](https://github.com/utahmobl/opencap-monocular).

**Pose2Sim** (David Pagnon, Sensors 2021/22): OpenPose (Multi-View) → Kalibrierung → robuste Triangulation/Filterung → OpenSim-IK auf physisch konsistentem Vollkörpermodell. Schritt-zu-Schritt-SD 1,7°–3,2°, MAE 0,35°–1,6° (Multi-View-intern) [MDPI](https://www.mdpi.com/1424-8220/22/7/2712). Lizenz: **BSD-3-Clause**. Empfiehlt ≥2 Kameras, Front + 45°-Seitenwinkel auf Hüfthöhe [GitHub](https://github.com/perfanalytics/pose2sim).

**Sports2D** (Pagnon): monokulare 2D-Winkelberechnung direkt aus Keypoints (RTMLib/RTMPose-Familie), optionale `--do_ik`-3D-Erweiterung via Pose2Sim-Integration; erfordert Bewegung parallel zur Bildebene. Lizenz: **BSD-3-Clause**. Standard-Filter: Butterworth 4. Ordnung, **6 Hz Cutoff** [GitHub](https://github.com/davidpagnon/Sports2D).

**EasyMocap** (ZJU3DV): Lizenz **explizit nicht-kommerziell**, Ableitungen müssen offen bleiben — für ein kommerzialisierbares Projekt ungeeignet [LICENSE](https://github.com/zju3dv/EasyMocap/blob/master/LICENSE).

**FreeMocap**: **AGPL-3.0/GPL-3.0+**, community-getrieben, für jede Webcam [freemocap.org](https://freemocap.org/).

**Anipose**: primär für Tierverhalten (DeepLabCut-basiert), Lizenz nicht eindeutig verifiziert, Triangulations-/Kalibrierungsmodule (aniposelib) technisch übertragbar.

**Kamera-Anzahl vs. Genauigkeit:** Eine Medicina-2026-Studie fand für Knieflexion beim Gehen RMSE **9,83° (1 Kamera) vs. 4,92° (Multi-Kamera)** [PMC12942615](https://pmc.ncbi.nlm.nih.gov/articles/PMC12942615/) — grob eine Halbierung des Fehlers durch die zweite Kamera (Okklusionsproblem des hinteren Beins wird gelöst). Gegenläufig zeigt die OpenCap-Kamerakonfigurationsstudie aber, dass der Sprung von 2 auf 3 oder 5 Kameras kaum noch etwas bringt (<0,3° Verbesserung) [PLOS Comp Biol](https://journals.plos.org/ploscompbiol/article?id=10.1371%2Fjournal.pcbi.1011462) — der große Sprung liegt zwischen 1 und 2 Kameras, nicht zwischen 2 und mehr.

### 1d) Biomechanische Nachverarbeitung

| Tool | Zweck | Lizenz |
|---|---|---|
| **OpenSim IK+Scaling** | klassischer Scale-Tool+IK-Workflow, gewichtete Least-Squares-Passung [Tutorial](https://opensimconfluence.atlassian.net/wiki/spaces/OpenSim/pages/53089741/) | **Apache 2.0** |
| **AddBiomechanics** (Werling/Delp, Stanford) | automatisierte Skalierung+IK+inverse Dynamik via bilevel-Optimierung; Marker-RMSE <2cm, Residualkräfte <2% Peak [PLOS ONE](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0295152), [PMC10688959](https://pmc.ncbi.nlm.nih.gov/articles/PMC10688959/) | **CC-BY** — grundsätzlich frei nutzbar |
| **OpenSim Moco** | Kinetik/Muskelkräfte via Trajektorienoptimierung, rechenintensiv | Apache 2.0 (Teil von opensim-core) |
| **Nimble Physics** (Werling) | differenzierbarer DART-Fork, PyTorch-kompatibel [arXiv 2103.16021](https://arxiv.org/abs/2103.16021) | **BSD** (Rajagopal-Modell separat **MIT**) |
| **MyoSuite/MyoSkeleton** (Meta) | MSK-RL-Simulation, ~4000x schneller als klassische MSK-Software [GitHub](https://github.com/MyoHub/myosuite) | **Apache 2.0** |
| **SKEL** (MPI) | SMPL-Oberfläche + anatomisches Skelett, echte Gelenkachsen statt Kugelgelenk | **strikt nicht-kommerziell**, SMPL-Abhängigkeit [skel.is.tue.mpg.de](https://skel.is.tue.mpg.de/license.html) |
| **OSSO** (Bogo/Keller, CVPR 2022) | Skelett aus Body-Scan (STAR-Modell, 2000 DXA-Scans) [arXiv 2204.10129](https://arxiv.org/abs/2204.10129) | vermutlich MPI-Non-Commercial (STAR-Abhängigkeit) |

**Praktikabilitäts-Einschätzung:** OpenSim+AddBiomechanics+Nimble Physics+MyoSuite sind alle permissiv lizenziert und kombinierbar — das ist der praktikable Kern für eine kommerzialisierbare Pipeline. SKEL/OSSO sind wegen SMPL/STAR-Abhängigkeit ausgeschlossen.

### 1e) Direkte Video→Winkel-Ansätze der Biomechanik-Community

Neben OpenCap/OpenCap-Monocular/OpenCapBench (s.o.) und Pose2Sim/Sports2D:

- **PhysCap** (MPI-Inf, TOG 2020): Echtzeit-physikalisch-plausible monokulare Mocap bei 25fps, CNN→2D/3D→IK→Physik-Optimierer (Bodenkontakt, Schwerkraft) [arXiv 2008.08880](https://arxiv.org/abs/2008.08880) — reduziert Fußgleiten/Jitter, kein klinischer Gang-Fokus.
- **PhysPT** (CVPR 2024): Physics-aware Pretrained Transformer, verbessert kinematikbasierte Schätzungen nachträglich via Euler-Lagrange-Loss [arXiv 2404.04430](https://arxiv.org/abs/2404.04430).
- Explizit für pathologisches Gehen relevant: **"A gait lab in your pocket? Accuracy and reliability of monocular smartphone-based markerless 3D gait analysis in pathological gait"** [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0966636225003583) — direkt einschlägig für die Kreuzband-Reha-Zielgruppe, sollte vor Projektstart im Volltext gelesen werden.

---

## 2. Genauigkeitszahlen (Video vs. Marker-Goldstandard)

| Messgröße | Setup | Fehler |
|---|---|---|
| Knieflexion (sagittal) | Multi-View (OpenCap/Theia3D) | **2,3°–7°**, meist ~5–6° RMSE [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0021929024002781), [Theia3D-Studie](https://www.sciencedirect.com/science/article/abs/pii/S0021929021004346) |
| Knieflexion (sagittal) | Monokular, 1 Kamera | **5,1°–11°** (Peak bis 11,3°) [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0021929024001040), [PMC10803458](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10803458/) |
| Knieflexion (Medicina-2026-Vergleich) | 1 Kamera vs. Multi-Kamera | **9,83° vs. 4,92°** [PMC12942615](https://pmc.ncbi.nlm.nih.gov/articles/PMC12942615/) |
| Knieflexion (OpenCap Monocular vs. 2-Kamera) | 1 Kamera vs. 2 Kamera | **5,6° vs. 5,2°** [Utah MOBL](https://utahmobl.github.io/OpenCap-monocular-project-page/) |
| Hüftflexion | Multi-View | RMSE 5–10°, CMC>0,94 [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0021929025001137); Hüft-Ab/Adduktion paradoxerweise oft valider als Sprunggelenk [MDPI](https://www.mdpi.com/2076-3417/16/4/1842) |
| Hüftflexion (Direct-Extraction-Ansatz 2026) | monokular | MAE 7,5–8,0°, r≈0,98 [arXiv 2607.17639](https://arxiv.org/html/2607.17639) |
| Sprunggelenk Dorsi-/Plantarflexion | Multi-View (OpenCap) | RMSE **4,6°–7,9°**, oft schlechteste Validität aller Gelenke [PMC12074354](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12074354/), [MDPI](https://www.mdpi.com/2076-3417/16/4/1842) |
| Frontalebene (Knievalgus, Beckenobliquität, Hüftadd/-abd) | Multi-View | RMSE **5–10°**, Limits of Agreement **35–46% des ROM**, tendenziell unterschätzt [PLOS One](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0293917), [Frontiers](https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2024.1352286/full) |
| Neueres 3D-Pose-Benchmark vs. IMU (2025) | verschiedene generische 3D-Pose-Modelle (MotionAGFormer, MotionBERT, MMPose) | Gesamt-RMSE **9,27°–12,28°** — deutlich schlechter als spezialisierte biomechanische Pipelines [arXiv 2510.02264](https://arxiv.org/pdf/2510.02264) |

**Fazit zur Fragestellung "±3°, ±5° oder ±10°?":** Realistisch für die **sagittale Ebene** (Knie-/Hüftflexion) mit Multi-View: **±5–7°**. Mit nur 1 Handy: **±5–11°** (im Mittel eher ~5–6° bei guten Bedingungen, Ausreißer bis ~12°). **±3°** ist mit aktueller Video-Technologie für klinische Einzelfallbeurteilung praktisch nicht erreichbar — das ist eher die Domäne von Marker-Multikamera-Systemen selbst untereinander. Die **Frontal-/Transversalebene** (Knievalgus, Beckenobliquität — gerade für Kreuzband-Reha klinisch hochrelevant!) liegt durchgehend bei **≥5–10°** mit sehr breiten Limits of Agreement und sollte im Projekt mit expliziten Unsicherheits-/Konfidenzangaben ausgegeben werden, nicht mit falscher Präzisionssuggestion.

---

## 3. Gangereignis-Erkennung (Heel Strike/Toe Off ohne Kraftmessplatte)

- **Zeni et al. 2008** (kinematisch, lokale Extrema der Fersen-/Zehen-Position relativ zum Becken): Original-Genauigkeit Heel-Strike-Fehler **0,18/0,30 Frames**, Toe-Off **−2,25/−2,61 Frames** [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0966636207001804). In neueren Vergleichsstudien weiterhin eine der genauesten kinematik-basierten Methoden, kleinster Zeitfehler Heel-Strike **4,78±9,56 ms** [arXiv 2503.00794](https://arxiv.org/pdf/2503.00794).
- **O'Connor et al. 2007** (Fußgeschwindigkeits-basiert, vertikale Geschwindigkeitsextrema): eine der genauesten Methoden für Heel-Strike neben Alton et al. 1998 [arXiv](https://arxiv.org/html/2503.00794v1).
- **ML/Deep-Learning (2023–2025):** LSTM-Modell (4363 Gangzyklen, 588 Probanden) vergleichbar mit klassischen kinematischen Methoden [arXiv 2503.00794](https://arxiv.org/pdf/2503.00794); zweistufiger Ansatz (OpenPose+CNN für Fersen-Keypoints) direkt aus Video [Springer](https://link.springer.com/article/10.1007/s11517-024-03189-7). Moderne DL-Ansätze: Initial-Contact im Mittel **5,4 ms**, Foot-Off **11,3 ms**, Detektionsraten ≥99%/≥95% [PMC11351211](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11351211/).
- **Direkt aus Video-Pose validiert:** PLOS Comp Biol [Link](https://journals.plos.org/ploscompbiol/article?id=10.1371%2Fjournal.pcbi.1008935) und PLOS Digital Health [Link](https://journals.plos.org/digitalhealth/article?id=10.1371%2Fjournal.pdig.0000467) bestätigen Machbarkeit ohne Marker.
- **Framerate-Effekt:** Keine direkte 30/60/120fps-Vergleichsstudie gefunden. Praktische Konsequenz: reiner Frame-Quantisierungsfehler ±33ms bei 30fps, ±16,7ms bei 60fps — die Framerate begrenzt direkt die erreichbare Timing-Auflösung, unabhängig vom Algorithmus. **Empfehlung: mindestens 60fps für Gangereigniserkennung**, 30fps ist ein harter Kompromiss.

---

## 4. Lizenzen — kritischer Teil

| Komponente | Lizenz | Kommerziell nutzbar? | Quelle |
|---|---|---|---|
| **SMPL** (Modell) | Eigene "non-commercial scientific research"-Lizenz (MPI) | **Nein** — explizit auch "incorporation in a commercial product/service" verboten | [smpl.is.tue.mpg.de](https://smpl.is.tue.mpg.de/modellicense.html) |
| **SMPL-X** (Modell) | gleiche Struktur | **Nein**, kommerziell nur via Meshcapade.com | [smpl-x.is.tue.mpg.de](https://smpl-x.is.tue.mpg.de/modellicense.html) |
| WHAM (Code) | MIT | Code ja, **Pipeline nein** (lädt SMPL) | [GitHub](https://github.com/yohanshin/WHAM/blob/main/LICENSE) |
| TRAM (Code) | MIT | Code ja, **Pipeline nein** (lädt SMPL) | [GitHub](https://github.com/yufu-wang/tram) |
| GVHMR | eigene NC-Lizenz | **Nein** | [LICENSE](https://github.com/zju3dv/GVHMR/blob/main/LICENSE) |
| 4D-Humans/HMR2 (Code) | MIT | Code ja, **Pipeline nein** (SMPL) | [LICENSE](https://github.com/shubham-goel/4D-Humans/blob/main/LICENSE.md) |
| RTMPose/MMPose | **Apache 2.0** | **Ja**, keine SMPL-Abhängigkeit | [GitHub](https://github.com/open-mmlab/mmpose/blob/main/LICENSE) |
| Sapiens (Meta) | **CC-BY-NC-SA 4.0** | **Nein** | [HuggingFace](https://huggingface.co/facebook/sapiens) |
| ViTPose/++ | **Apache 2.0** | **Ja** | [LICENSE](https://github.com/ViTAE-Transformer/ViTPose/blob/main/LICENSE) |
| MediaPipe | **Apache 2.0** | **Ja** | [Google AI Edge](https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker/python) |
| OpenPose | eigene NC-Lizenz, 25.000$/Jahr kommerziell, **Sport ausgeschlossen** | **Nein** | [LICENSE](https://github.com/CMU-Perceptual-Computing-Lab/openpose/blob/master/LICENSE) |
| OpenSim | **Apache 2.0** | **Ja** | [Wikipedia](https://en.wikipedia.org/wiki/OpenSim_(simulation_toolkit)) |
| OpenCap (Code) | **Apache 2.0** | Ja | [LICENSE](https://github.com/opencap-org/opencap-processing/blob/main/LICENSE.md) |
| OpenCap (Web-Service) | Nutzungsbedingungen: nur Bildung/Forschung | **Service nein**, Code ja | [Terms](https://www.opencap.ai/terms-conditions) |
| Pose2Sim | **BSD-3-Clause** | **Ja** | [GitHub](https://github.com/perfanalytics/pose2sim) |
| Sports2D | **BSD-3-Clause** | **Ja** | [LICENSE](https://github.com/davidpagnon/Sports2D/blob/main/LICENSE) |
| EasyMocap | eigene NC-Lizenz | **Nein** | [LICENSE](https://github.com/zju3dv/EasyMocap/blob/master/LICENSE) |
| FreeMocap | AGPL-3.0/GPL-3.0+ | eingeschränkt (Copyleft) | [freemocap.org](https://freemocap.org/) |
| SKEL | eigene NC-Lizenz + SMPL-Abhängigkeit | **Nein** | [skel.is.tue.mpg.de](https://skel.is.tue.mpg.de/) |
| AddBiomechanics | **CC-BY** | grundsätzlich ja | [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC10688959/) |
| Nimble Physics | **BSD** (Rajagopal-Modell MIT) | **Ja** | [GitHub](https://github.com/keenon/nimblephysics) |
| MyoSuite/MyoSkeleton | **Apache 2.0** | **Ja** | [GitHub](https://github.com/MyoHub/myosuite) |
| YOLO-Pose | AGPL-3.0 oder Enterprise | eingeschränkt | [Ultralytics](https://docs.ultralytics.com/models/yolo11) |
| SAM 3D Body/MHR (Meta) | explizit open-source (Details zu genauer Lizenzklausel noch verifizieren) | vermutlich ja | [arXiv](https://arxiv.org/abs/2602.15989) |

**Rechtliche Kerneinschätzung:** Die rote Linie ist **SMPL/SMPL-X**. Deren Modell-Lizenz verbietet jede kommerzielle Nutzung — unabhängig von der Code-Lizenz des umgebenden Frameworks. Das betrifft WHAM, TRAM, GVHMR (zusätzlich eigene NC-Klausel), 4D-Humans/HMR2, SKEL, SMPLer-X, Multi-HMR, TokenHMR, NLF sowie Sapiens (eigene NC-SA-Lizenz) — **alle für ein später kommerziell/klinisch nutzbares Produkt ungeeignet**, solange sie SMPL(-X) benötigen.

**Sichere, rein permissive Kombination** (Apache/MIT/BSD/CC-BY, keine SMPL-Abhängigkeit):
- 2D/3D-Keypoints: **RTMPose/RTMW (Apache 2.0)** oder **MediaPipe (Apache 2.0)** oder **ViTPose (Apache 2.0)**
- Multi-View + Biomechanik: **Pose2Sim (BSD-3)** → **OpenSim (Apache 2.0)**, optional **AddBiomechanics (CC-BY)** für automatisierte Skalierung
- 1-Kamera-Winkel: **Sports2D (BSD-3)**
- Kinetik-Erweiterung (falls gewünscht): **Nimble Physics (BSD)**, **MyoSuite (Apache 2.0)**
- Explizit ausgeschlossen aus der Produktionslinie: OpenPose, Sapiens, GVHMR, WHAM, TRAM, SKEL, SMPL/SMPL-X-basierte Pipelines generell, EasyMocap.

---

## 5. Compute/Deployment

- **CPU-fähig:** RTMPose (leichte Varianten), MediaPipe (explizit mobile/CPU-designed), Sports2D (Standard CPU, GPU optional via CUDA/MPS/ROCm) [GitHub](https://github.com/davidpagnon/Sports2D).
- **GPU nötig/sinnvoll:** ViTPose (Transformer, große Varianten), WHAM/GVHMR/TRAM (SLAM+Deep-Learning-Stack), Sapiens (1B-Parameter). Konkrete FPS-Zahlen auf RTX 3090/4090/T4/A100/L4 für WHAM/TRAM/GVHMR/RTMPose konnten in dieser Recherche nicht mehr im Detail belegt werden (Suchbudget erschöpft) — vor Architekturentscheidung eigene Benchmarks auf Ziel-Hardware empfohlen.
- **Google Cloud Run mit GPU:** unterstützt **NVIDIA L4** (24GB VRAM, min. 4 CPU/16GiB) und **NVIDIA RTX PRO 6000 Blackwell** (96GB VRAM) [Cloud Run Docs](https://docs.cloud.google.com/run/docs/configuring/services/gpu). Kaltstart mit vorinstallierten Treibern ~5s. Abrechnung instanzbasiert (nicht pro Request) — für sporadische Analyse-Jobs **Skalierung auf null** essenziell, um Leerlaufkosten zu vermeiden. Architektonisch für "kein 24/7-Betrieb, aber gelegentliche Video-Analyse" gut geeignet: Job kommt rein → Instanz startet (~5s) → verarbeitet → skaliert auf 0.
- **Android ML Kit Pose Detection:** im Kern **2D** — die Z-Koordinate ist laut Google-Doku "experimentell", **kein echter 3D-Wert**, für klinische Frontalebenen-Winkel ungeeignet. 33 Landmarks inkl. Hand/Fuß, ~30fps (Pixel 4) / ~45fps (iPhone X) [ML Kit Docs](https://developers.google.com/ml-kit/vision/pose-detection).
- **Apple Vision Framework 3D Body Pose / ARKit:** keine belastbaren publizierten Gelenkwinkel-Validierungsstudien in dieser Recherche gefunden — offene Lücke, vor Projektentscheidung gezielt nachprüfen.

---

## 6. Aufnahme-Best-Practices

- **Pose2Sim:** ≥2 Kameras, Front + 45°-Seitenwinkel auf Hüfthöhe, Kalibrierung via Schachbrett oder vermessene Szenenkoordinaten [GitHub](https://github.com/perfanalytics/pose2sim).
- **Sports2D:** Bewegung **so parallel wie möglich zur Bewegungsebene** (sagittal oder frontal) filmen — sonst Perspektivfehler; ≥60fps vorteilhaft; Standardauflösung 1280×720 [GitHub](https://github.com/davidpagnon/Sports2D).
- **OpenCap:** unterstützt Laufband und Overground; markerlose, checkerboard-freie Kalibrierung kombiniert mit gelerntem LSTM-Marker-Augmenter statt physischem Referenzobjekt [OpenCap-QA PDF](https://mobilize.stanford.edu/wp-content/uploads/2022/12/OpenCap-QA-Final.pdf).
- **Filterung:** Sports2D-Standard Butterworth 4. Ordnung, **6Hz Cutoff** (Alternativen: Kalman, One Euro, GCV-Spline, Gaussian, LOESS, Median) [GitHub](https://github.com/davidpagnon/Sports2D). Primärquelle der 6Hz-Konvention (klassisch Winter'sche Residual-Analyse-Methode) konnte in dieser Recherche nicht direkt verifiziert werden — nur indirekt als Community-Standard über die Sports2D-Doku bestätigt.

---

## 7. Bekannte Fallstricke

- **Perspektivfehler bei sagittaler 2D-Messung:** Abweichung von "senkrecht zur Bewegungsebene" führt zu systematischen Winkelfehlern (Rotation aus der Bildebene erscheint als Segmentverkürzung, nicht als Winkeländerung) [Sports2D-Doku](https://github.com/davidpagnon/Sports2D).
- **Kameraanzahl:** größter Sprung von 1→2 Kameras (RMSE 9,83°→4,92° bzw. 9,6°→4,1° je nach Studie); 2→3/5 Kameras bringt kaum noch etwas [PMC12942615](https://pmc.ncbi.nlm.nih.gov/articles/PMC12942615/), [PLOS Comp Biol](https://journals.plos.org/ploscompbiol/article?id=10.1371%2Fjournal.pcbi.1011462).
- **Frontalebene generell unzuverlässiger** als Sagittalebene (Limits of Agreement 35–46% des ROM) [PLOS One](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0293917) — für Knievalgus-Beurteilung in der Kreuzband-Reha eine zentrale Einschränkung.
- **Skalierung ohne Referenzobjekt:** OpenCaps Marker-Augmenter-Ansatz ersetzt physische Kalibrierobjekte teilweise durch einen gelernten anthropometrischen Prior — bleibt aber mit eigenem Fehlerbudget behaftet.
- **Okklusion des hinteren Beins, Tiefenambiguität, Jitter, Links/Rechts-Vertauschung:** in der Fachliteratur breit anerkannte Probleme monokularer Verfahren, in dieser Recherche aber wegen Suchbudget-Erschöpfung nicht mehr mit spezifischen Primärquellen belegbar — als bekannte Klasse von Fehlerquellen einzuplanen (z.B. Konsistenzchecks über Zeit gegen Links/Rechts-Sprünge, explizite Okklusions-Konfidenzwerte pro Frame).
- **Pathologische Bewegungsmuster:** mehrere Quellen merken an, dass Validierungsstudien überwiegend an gesunden Probanden durchgeführt wurden — die Übertragbarkeit auf Kreuzband-Reha-Patienten mit kompensatorischen Gangmustern ist noch unzureichend charakterisiert [arXiv 2402.13172](https://arxiv.org/html/2402.13172v4).

---

## Empfehlung: Zwei Pipeline-Varianten

**Variante A — "So schnell wie möglich etwas Brauchbares"**
- Aufnahme: 1 Handy, sagittal, 60fps, parallel zur Gehebene
- 2D-Pose: **MediaPipe Pose** (Apache 2.0, läuft on-device/CPU, hat Fuß-Keypoints)
- Winkelberechnung: **Sports2D** (BSD-3, direkt 2D-Sagittalwinkel, eingebauter Butterworth-Filter)
- Gangereignisse: kinematisch (Zeni-artig) aus Fersen-/Zehen-Trajektorien
- Deployment: läuft komplett clientseitig/CPU — praktisch keine Cloud-Kosten
- Erwartete Genauigkeit: Knieflexion sagittal ~±5–10°, Frontalebene unzuverlässig/nicht ausgeben
- Lizenzstatus: vollständig permissiv, kommerzialisierbar

**Variante B — "Bestmögliche Genauigkeit, forschungsnah"**
- Aufnahme: 2 Handys, Front + 45°, ≥60fps, kalibriert
- 2D-Pose: **RTMW/RTMPose-Wholebody** (Apache 2.0, GPU, präzise Fuß-Keypoints)
- Multi-View: **Pose2Sim** (BSD-3) für Triangulation
- Biomechanik: **OpenSim IK** (Apache 2.0), optional **AddBiomechanics** (CC-BY) für automatisierte Skalierung
- Optional Kinetik: **Nimble Physics** (BSD) oder **MyoSuite** (Apache 2.0)
- Deployment: **Google Cloud Run mit L4-GPU**, Skalierung auf null für sporadische Analysejobs
- Erwartete Genauigkeit: Knieflexion sagittal ~±5°, deutlich robuster gegen Okklusion
- Lizenzstatus: vollständig permissiv, kommerzialisierbar
- Forschungsnahe Alternative (nur für Prototyping, NICHT produktiv/kommerziell): OpenCap-Monocular/SMPL-basierte Methoden zum Vergleich/Benchmarking gegen die eigene Pipeline, aber nicht in ein verkauftes Produkt integrieren.

---

## Wichtiger Hinweis zu Recherchelücken

Das WebSearch-Kontingent der Session wurde während der Recherche vollständig erschöpft (200/200 über alle fünf parallelen Recherche-Threads und meine eigenen Nachrecherchen). Folgende Punkte konnten daher **nicht** mehr vertieft werden und sollten bei Bedarf gezielt nachrecherchiert werden:
- Konkrete FPS/Sekunden-Benchmarks für WHAM/TRAM/GVHMR/RTMPose auf spezifischen GPUs (RTX 3090/4090/T4/A100/L4)
- Apple ARKit/Vision-Framework-Genauigkeitsstudien für Gelenkwinkel
- Primärquelle der "6Hz-Butterworth"-Konvention (vermutlich Winter'sche Residual-Analyse, nicht direkt verifiziert)
- Exakte Frontalebenen-Zahlen aus OpenCap-Supplementary-Tabellen
- Detaillierte OpenCapBench-Tabelle (welches 2D-Pose-Modell konkret am besten auf Winkel übersetzt)
- Genaue Lizenzklausel von SAM 3D Body/Momentum Human Rig (vielversprechend als SMPL-Alternative, aber Details noch zu verifizieren)

---

## Vollständige Quellenliste (chronologisch nach Recherche-Block)

**2D-Pose/Multi-View:** [MMPose RTMPose](https://github.com/open-mmlab/mmpose/tree/main/projects/rtmpose) · [RTMW arXiv](https://arxiv.org/pdf/2407.08634) · [RTMPose arXiv](https://arxiv.org/html/2303.07399v2) · [RTMO Diskussion](https://github.com/open-mmlab/mmpose/discussions/3135) · [ViTPose GitHub](https://github.com/vitae-transformer/vitpose) · [ViTPose++ arXiv](https://arxiv.org/pdf/2212.04246) · [ViTPose arXiv](https://arxiv.org/pdf/2204.12484) · [ViTPose++ OpenReview](https://openreview.net/pdf?id=6H2pBoPtm0s) · [Sapiens HF](https://huggingface.co/facebook/sapiens-pose-0.6b) · [Sapiens arXiv](https://arxiv.org/html/2408.12569v1) · [MediaPipe Vergleich](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/openpose-mediapipe-rtmpose-pose-tracking) · [BlazePose Google Research](https://research.google/blog/on-device-real-time-body-pose-tracking-with-mediapipe-blazepose/) · [MediaPipe Genauigkeit](https://sigmoidal.ai/en/real-time-human-pose-estimation-using-mediapipe/) · [OpenPose LICENSE](https://github.com/CMU-Perceptual-Computing-Lab/openpose/blob/master/LICENSE) · [OpenPose viso.ai](https://viso.ai/deep-learning/openpose/) · [DWPose arXiv](https://arxiv.org/pdf/2307.15880) · [HRNet GitHub](https://github.com/microsoft/human-pose-estimation.pytorch/blob/master/README.md) · [HRNet CVPR-Paper](https://openaccess.thecvf.com/content_CVPR_2019/papers/Sun_Deep_High-Resolution_Representation_Learning_for_Human_Pose_Estimation_CVPR_2019_paper.pdf) · [YOLO11 Docs](https://docs.ultralytics.com/models/yolo11) · [YOLO11 Blog](https://www.ultralytics.com/blog/how-to-use-ultralytics-yolo11-for-pose-estimation) · [OpenCap Scoping Review](https://www.frontiersin.org/journals/digital-health/articles/10.3389/fdgth.2026.1882536/full) · [OpenCap Marker-Augmenter](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12198419/) · [Marker-Enhancer GitHub](https://github.com/stanfordnmbl/marker-enhancer) · [OpenCap-core LICENSE](https://github.com/stanfordnmbl/opencap-core/blob/main/LICENSE) · [Stanford Engineering News](https://engineering.stanford.edu/news/opencap-sophisticated-human-biomechanics-smartphone-video) · [OpenCap Monocular](https://utahmobl.github.io/OpenCap-monocular-project-page/) · [Pose2Sim/Sports2D LICENSE](https://github.com/davidpagnon/Sports2D/blob/main/LICENSE) · [Pose2Sim GitHub](https://github.com/perfanalytics/pose2sim) · [Sports2D JOSS](https://github.com/openjournals/joss-reviews/issues/6849) · [Sports2D Zenodo](https://zenodo.org/records/15290876) · [FreeMocap Libraries.io](https://libraries.io/pypi/freemocap) · [FreeMocap.org](https://freemocap.org/) · [EasyMocap LICENSE](https://github.com/zju3dv/EasyMocap/blob/master/LICENSE) · [Anipose PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8498918/) · [Multi-Kamera-Studie Medicina](https://pmc.ncbi.nlm.nih.gov/articles/PMC12942615/) · [Single-vs-Multi PubMed](https://pubmed.ncbi.nlm.nih.gov/38430608/)

**Monokulare 3D/Biomechanische Validierung:** [WHAM arXiv](https://arxiv.org/pdf/2312.07531) · [WHAM GitHub](https://github.com/yohanshin/WHAM) · [WHAM LICENSE](https://github.com/yohanshin/WHAM/blob/main/LICENSE) · [TRAM Projektseite](https://yufu-wang.github.io/tram4d/) · [TRAM arXiv](https://arxiv.org/pdf/2403.17346) · [TRAM GitHub](https://github.com/yufu-wang/tram) · [GVHMR GitHub](https://github.com/zju3dv/GVHMR) · [GVHMR LICENSE](https://github.com/zju3dv/GVHMR/blob/main/LICENSE) · [4D-Humans arXiv](https://arxiv.org/html/2305.20091v3) · [4D-Humans LICENSE](https://github.com/shubham-goel/4D-Humans/blob/main/LICENSE.md) · [MotionBERT arXiv](https://arxiv.org/abs/2210.06551) · [MotionBERT LICENSE](https://github.com/Walter0807/MotionBERT/blob/main/LICENSE) · [SMPLer-X arXiv](https://arxiv.org/abs/2309.17448) · [SMPLer-X GitHub](https://github.com/SMPLCap/SMPLer-X) · [Multi-HMR arXiv](https://arxiv.org/abs/2402.14654) · [Multi-HMR 2 arXiv](https://arxiv.org/pdf/2606.14841) · [Multi-HMR GitHub](https://github.com/naver/multi-hmr) · [TokenHMR arXiv](https://arxiv.org/pdf/2404.16752) · [TokenHMR GitHub](https://github.com/saidwivedi/TokenHMR) · [NLF GitHub](https://github.com/isarandi/nlf) · [PromptHMR arXiv](https://arxiv.org/abs/2504.06397) · [CoMotion Apple](https://machinelearning.apple.com/research/comotion-concurrent-3d-motion) · [CoMotion GitHub](https://github.com/apple/ml-comotion) · [SAM 3D Body arXiv](https://arxiv.org/abs/2602.15989) · [SAM 3D Body Meta AI](https://ai.meta.com/research/publications/sam-3d-body-robust-full-body-human-mesh-recovery/) · [SAM 3D Body HF](https://huggingface.co/facebook/sam-3d-body-dinov3) · [Klinische Winkelextraktion arXiv](https://arxiv.org/html/2607.17639) · [RAM arXiv](https://arxiv.org/pdf/2603.19929) · [DuoMo arXiv](https://arxiv.org/pdf/2603.03265) · [SAM-Body4D arXiv](https://arxiv.org/pdf/2512.08406) · [OnlineHMR arXiv](https://arxiv.org/pdf/2603.17355) · [Human3R arXiv](https://arxiv.org/pdf/2510.06219) · [SMPL-Lizenz](https://smpl.is.tue.mpg.de/modellicense.html) · [SMPL-X-Lizenz](https://smpl-x.is.tue.mpg.de/modellicense.html) · [OpenCapBench arXiv](https://arxiv.org/abs/2406.09788) · [OpenCapBench GitHub](https://github.com/StanfordMIMI/OpenCapBench) · [OpenCapBench Zusammenfassung](https://www.aimodels.fyi/papers/arxiv/opencapbench-benchmark-to-bridge-pose-estimation-biomechanics) · [OpenCapBench Trainingsdaten](https://arxiv.org/pdf/2409.03766v2) · [OpenCap Radfahren-Studie](https://www.sciencedirect.com/science/article/pii/S0010482525006468) · [Biomech. Framework arXiv](https://arxiv.org/html/2402.13172v4) · [VIDIMU arXiv](https://arxiv.org/pdf/2303.16150) · [Kinematik-Benchmark vs. IMU arXiv](https://arxiv.org/pdf/2510.02264)

**Biomechanische Nachverarbeitung:** [OpenSim Tutorial](https://opensimconfluence.atlassian.net/wiki/spaces/OpenSim/pages/53089741/Tutorial+3+-+Scaling+Inverse+Kinematics+and+Inverse+Dynamics) · [BOPS GitHub](https://github.com/RehabEngGroup/BOPS) · [AddBiomechanics PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC10688959/) · [AddBiomechanics PLOS ONE](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0295152) · [AddBiomechanics SimTK](https://simtk.org/projects/addbiomechanics) · [AddBiomechanics GitHub](https://github.com/keenon/AddBiomechanics) · [Nimble Physics GitHub](https://github.com/keenon/nimblephysics/blob/master/LICENSE) · [Nimble Physics arXiv](https://arxiv.org/abs/2103.16021) · [MyoSuite GitHub](https://github.com/MyoHub/myosuite) · [MyoSuite PyPI](https://pypi.org/project/MyoSuite/) · [MyoSuite Meta-Ankündigung](https://about.fb.com/news/2022/05/an-embodied-ai-platform-to-solve-biomechanical-problems/) · [SKEL Lizenz](https://skel.is.tue.mpg.de/license.html) · [SKEL GitHub](https://github.com/MarilynKeller/SKEL) · [OSSO GitHub](https://github.com/MarilynKeller/OSSO) · [OSSO arXiv](https://arxiv.org/abs/2204.10129) · [SMPL2AddBiomechanics GitHub](https://github.com/MarilynKeller/SMPL2AddBiomechanics) · [Pose2Sim Accuracy MDPI](https://www.mdpi.com/1424-8220/22/7/2712) · [Pose2Sim Accuracy PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9002957/) · [PhysCap arXiv](https://arxiv.org/abs/2008.08880) · [PhysCap Projektseite](https://vcai.mpi-inf.mpg.de/projects/PhysCap/) · [PhysPT arXiv](https://arxiv.org/abs/2404.04430) · [PhysPT CVPR](https://openaccess.thecvf.com/content/CVPR2024/html/Zhang_PhysPT_Physics-aware_Pretrained_Transformer_for_Estimating_Human_Dynamics_from_Monocular_CVPR_2024_paper.html) · [Pathologisches Gehen ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0966636225003583)

**Genauigkeit/Gangereignisse:** [OpenCap RMSE ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0021929024002781) · [OpenCap Range ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0021929025001137) · [Theia3D ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0021929021004346) · [Theia3D Review](https://www.sciencedirect.com/science/article/pii/S0933365725002672) · [Monokular ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0021929024001040) · [Smartphone-Studie PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10803458/) · [HGcnMLP Frontiers](https://www.frontiersin.org/journals/bioengineering-and-biotechnology/articles/10.3389/fbioe.2023.1335251/full) · [OpenCap Sprunggelenk PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12074354/) · [OpenCap Kamerakonfiguration MDPI](https://www.mdpi.com/2076-3417/16/4/1842) · [Frontalebene PLOS One](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0293917) · [Systematisches Review PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11175331/) · [Zeni 2008 ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0966636207001804) · [Gait-Event-Vergleich arXiv](https://arxiv.org/pdf/2503.00794) · [DL Gait Events Springer](https://link.springer.com/article/10.1007/s11517-024-03189-7) · [DL Gait Events PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11351211/) · [PLOS Comp Biol Gait Events](https://journals.plos.org/ploscompbiol/article?id=10.1371%2Fjournal.pcbi.1008935) · [PLOS Digital Health](https://journals.plos.org/digitalhealth/article?id=10.1371%2Fjournal.pdig.0000467) · [Framerate PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10420363/)

**Lizenzen/Compute/Best Practices:** [OpenCap Terms](https://www.opencap.ai/terms-conditions) · [Cloud Run GPU Docs](https://docs.cloud.google.com/run/docs/configuring/services/gpu) · [ML Kit Pose Detection](https://developers.google.com/ml-kit/vision/pose-detection) · [OpenSim Wikipedia](https://en.wikipedia.org/wiki/OpenSim_(simulation_toolkit)) · [MediaPipe kommerziell FAQ](https://quickpose.ai/faqs/can-mediapipe-be-used-commercially/) · [OpenCap-QA PDF](https://mobilize.stanford.edu/wp-content/uploads/2022/12/OpenCap-QA-Final.pdf) · [OpenCap Kamerakonfiguration PLOS](https://journals.plos.org/ploscompbiol/article?id=10.1371%2Fjournal.pcbi.1011462)
