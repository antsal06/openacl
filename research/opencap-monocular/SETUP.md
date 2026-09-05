<!-- Recherche-Stand: 2026-09-05. Primärquellen: GitHub-Repo utahmobl/opencap-monocular (README, LICENSE,
installation/, docker/, WHAM/README.md), arXiv:2603.24733, Lab-Blog mobl.mech.utah.edu, Google-Cloud-Doku.
Nur für research/ und lokale Nutzung, siehe ADR-0002 in docs/DECISIONS.md: SMPL-basierte Tools nie im
Produktionspfad. -->

# OpenCap Monocular – Setup (research/, nicht Produktionspfad)

Repo: https://github.com/utahmobl/opencap-monocular (Fork/Weiterentwicklung im Umfeld von
`stanfordnmbl/opencap-core`, Preprint arXiv:2603.24733, University of Utah MoBL-Lab). Stand der Recherche:
`pushed_at` 2026-08-02, 214 Stars (per `gh api`, 2026-09-05).

## Wichtige Korrektur gegenüber `docs/research/01-tool-landschaft.md`

Die dortige Aussage „Apache-2.0-Lizenz" für dieses Repo ist **falsch** und sollte dort korrigiert werden.
Verifiziert per direktem Fetch der `LICENSE`-Datei im Repo: Das Repo steht unter der
**PolyForm Noncommercial License 1.0.0** (https://polyformproject.org/licenses/noncommercial/1.0.0) –
ausdrücklich nicht-kommerziell. Passt zu ADR-0002 (SMPL-Tools nur `research/`, nie Produktionspfad), ändert
aber nichts an der Einordnung: Diese Lizenz allein würde schon jede kommerzielle Nutzung ausschließen, unabhängig
von der SMPL-Lizenz.

## 1. Was ist das Repo, und was macht es

Monokulare (Ein-Kamera) 3D-Ganganalyse: Pose-Schätzung (ViTPose) → Kamera-Trajektorie (DPVO, oder Fallback bei
statischer Kamera) → WHAM-Modell (SMPL-Körpermodell) → OpenSim-Skalierung/IK. Output ist auf ein bestehendes
OpenSim-Modell skaliert, ähnlich der Multi-Kamera-OpenCap-Pipeline, aber mit nur einem Video.

## 2. Installation

Quelle: `README.md` und `installation/INSTALL_SLIM.md` im Repo (per raw-GitHub-Fetch verifiziert).

- **OS:** Ubuntu 20.04 oder 22.04
- **Python:** 3.9
- **NVIDIA-Treiber:** ≥ 520, getestet mit CUDA 11.8 und 12.x
- **PyTorch:** 2.1.2+cu118
- **OpenSim:** 4.4, Installation über conda **vor** den pip-Abhängigkeiten (Reihenfolge wichtig laut README)
- **mmcv-full:** 1.7.2, installiert über `openmim`
- **ViTPose:** als editable install (`pip install -e`) aus einem Git-Submodul/separaten Repo
- SLAHMR-Utilities werden für den SMPL-Umgang mitinstalliert

**Docker wird für den produktiven Einsatz empfohlen** (`docker/README.md`): eigenes Dockerfile/Image im Repo,
`nvidia-container-toolkit` nötig, Container muss mit `--runtime=nvidia` gestartet werden (nicht `--gpus all`
oder CDI-Syntax – README ist hier laut Recherche explizit, das ältere `--runtime=nvidia`-Flag zu verwenden).

**VRAM-Anforderung: nicht verifiziert.** Weder README noch `INSTALL_SLIM.md` nennen für `opencap-monocular`
selbst eine konkrete VRAM-Zahl. Das verwandte, aber technisch andere Repo `stanfordnmbl/opencap-core`
(OpenPose-basierte Multi-Kamera-Pipeline, nicht WHAM-basiert) nennt in Suchtreffern 4 GB Minimum, 8 GB als
Cloud-Standard, 24 GB für hochauflösende Verarbeitung – das ist aber ein anderes Modell und nur ein grober
Anhaltspunkt, keine belastbare Aussage für dieses Repo.

## 3. Modelle zum Herunterladen, Registrierung, Lizenzen

Aus der „Third-Party Licenses"-Tabelle im README sowie `WHAM/README.md` (wörtlich zitiert bzw. paraphrasiert):

| Komponente | Lizenz | Kommerziell nutzbar | Registrierung nötig |
|---|---|---|---|
| WHAM (Checkpoints) | MIT | ja | nein |
| ViTPose (Checkpoints) | Apache 2.0 | ja | nein |
| DPVO | MIT | ja | nein – wird bei statischer Kamera ohnehin nicht verwendet (Fallback) |
| SMPL / SMPL-X (Körpermodell) | Custom (Max-Planck-Institut) | **nein** | **ja**, persönlich gebunden |

SMPL-Registrierung: https://smpl.is.tue.mpg.de (Account + Lizenz akzeptieren) und zusätzlich
https://smplify.is.tue.mpg.de. Lizenztext: https://smpl.is.tue.mpg.de/modellicense. Diese Lizenz ist
ausdrücklich nicht-kommerziell und an die registrierte Person gebunden – das deckt sich mit CLAUDE.md
(„SMPL-basierte Tools nur in research/ und lokal").

## 4. Eingabe

- Ein einzelnes Smartphone-Video.
- Kamera-Intrinsics werden **nicht manuell kalibriert**, sondern aus einer im Repo gepflegten
  Geräte-Datenbank bezogen (`make setup-intrinsics` bzw. `make update-intrinsics` unter `installation/`).
  Das setzt voraus, dass das jeweilige iPhone-Modell in dieser Datenbank enthalten ist. **Was bei einem
  unbekannten/neuen iPhone-Modell passiert (Fallback? Fehler? generische Intrinsics?), ist nicht verifiziert** –
  vor dem eigentlichen Lauf mit dem tatsächlichen iPhone-Modell prüfen.
- Unterstützte Videoformate/Auflösungen: README macht dazu keine Angabe. **Nicht verifiziert.** Sagittales
  1080p/60fps-Video nach `docs/PROTOKOLL-AUFNAHME.md` als Eingabe versuchen und Fehler beim Erstlauf
  protokollieren.

## 5. Ausgabe

Laut README (wörtlich referenziert):
- `mono.json` – zur Visualisierung im [OpenCap Visualizer](https://visualizer.opencap.ai)
- `*.trc` – Marker-Trajektorien (OpenSim-Format)
- `*.mot` – Kinematik (OpenSim-Format)
- `*_scaled.osim` – auf die Person skaliertes OpenSim-Modell

Damit ist die Ausgabe direkt mit dem in ADR-0007 geplanten Adapter-Schema kompatibel (ein Backend, das
`.mot`/`.trc` liefert, lässt sich in `KinematicsResult` überführen).

## 6. Laufzeit pro Sekunde Video

**Nicht verifiziert.** Weder das README noch der arXiv-Abstract (2603.24733) nennen eine konkrete
Verarbeitungszeit pro Sekunde Video oder ein Referenz-GPU-Modell für ein Benchmark. Die PDF-Volltextextraktion
des Preprints ist bei der Recherche technisch fehlgeschlagen (komprimierte PDF-Streams) – falls das für die
Planung wichtig wird, den PDF-Volltext separat (z. B. über den arXiv-HTML-Renderer) beschaffen und den
Methodenteil prüfen. Für die Benchmark-VM heißt das: Laufzeit beim ersten Testlauf selbst stoppen.

## 7. Gehostete Web-App – existiert bereits, einfacherer Weg

**Ja**, seit Beta-Release am 2026-04-06 laut Lab-Blog (https://mobl.mech.utah.edu/opencap-monocular-released/),
erreichbar über https://www.opencap.ai. Aus dem Paper (arXiv:2603.24733) sinngemäß zitiert: „OpenCap Monocular
is deployed via a smartphone app, web app, and secure cloud computing … enabling free, accessible single-
smartphone biomechanical assessments." Laut Lab-Blog: kein Laptop, keine Kalibrierung, kein Neutraltrial nötig,
Verarbeitung „in weniger als 2 Minuten", kostenlos auf der OpenCap-Cloud-Infrastruktur.

Bekannte Beta-Einschränkungen (Lab-Blog): funktioniert noch **nicht** für Sprünge, Laufband-Gehen oder kleine
Kinder – für normales Gehen (Antons Anwendungsfall) laut Ankündigung geeignet.

Die opencap.ai-Seite selbst ließ sich per automatisiertem Fetch nicht vollständig auslesen (JavaScript-
Single-Page-App). Für die konkrete Bedienung (Account, Upload-Flow, Export) empfiehlt sich ein kurzer manueller
Test im Browser, bevor die lokale GPU-VM-Route (Abschnitt 8) aufgesetzt wird.

**Empfehlung:** Zuerst die gehostete Web-App ausprobieren (kein SMPL-Account, keine VM-Kosten). Die
GPU-VM-Route unten ist der Fallback, falls die Web-App Limits hat (z. B. Rohdaten-Zugriff, Batch-Verarbeitung
mehrerer Sessions, Offline-Bedarf) oder falls Anton die Pipeline selbst inspizieren/verändern will.

## 8. GCP Compute-Engine-VM, `europe-west4`

### GPU-Wahl: T4 oder L4?

- **VRAM-Bedarf von opencap-monocular ist nicht verifiziert** (siehe Abschnitt 2). Der einzige Anhaltspunkt
  (verwandtes, aber anderes Repo `opencap-core`: 8 GB Cloud-Standard) spricht dafür, dass eine T4 (16 GB)
  ausreichen sollte – das ist aber eine Einschätzung, keine belegte Aussage für dieses konkrete Repo.
- **Verfügbarkeit laut Google-Cloud-Doku** (https://docs.cloud.google.com/compute/docs/gpus/gpu-regions-zones,
  Stand Recherche): `europe-west4-a/b/c` bieten sowohl G2-Maschinen mit **NVIDIA L4** als auch N1-Maschinen mit
  **NVIDIA T4** an. T4 ist global in deutlich mehr Zonen verfügbar (~30+) als L4 (~15–20) – falls die Region
  später wechselt (z. B. wegen Quote), ist T4 die robustere Wahl.
- **Empfehlung für den ersten Testlauf:** mit einer T4 starten (günstiger, breiter verfügbar). Bricht der Lauf
  mit Out-of-Memory ab, auf L4 wechseln. Das lässt sich beim ersten Benchmark in `europe-west4` direkt klären,
  ohne vorher zu raten.

### Aktuelle Deep-Learning-VM-Images (2026)

**Wichtig – Korrektur zu `infra/GCP-SETUP.md`:** Die dort verwendete Image-Familie
`common-cu124-ubuntu-2204` ist laut Google-Cloud-Doku (https://docs.cloud.google.com/deep-learning-vm/docs/images)
**deprecated**, Support-Ende zum 2026-04-01. Aktuell verfügbare Familien (`image-project=deeplearning-platform-release`):

- `common-cu129-ubuntu-2204-nvidia-580`
- `common-cu129-ubuntu-2404-nvidia-580`
- `common-cu128-ubuntu-2204-nvidia-570`

Da opencap-monocular laut README nur Treiber ≥ 520 verlangt, ist Treiber 580 (rückwärtskompatibel) unproblematisch.
`infra/GCP-SETUP.md` sollte auf eine dieser aktuellen Familien aktualisiert werden (ADR-Vorschlag, nicht Teil
dieses Dokuments).

### Konkrete Befehle

VM erstellen (T4, angepasst gegenüber `infra/GCP-SETUP.md` – GPU-Typ und Image-Familie aktualisiert):

```bash
gcloud compute instances create openacl-gpu-mono \
  --zone=europe-west4-a --machine-type=n1-standard-4 \
  --accelerator=type=nvidia-tesla-t4,count=1 \
  --image-family=common-cu129-ubuntu-2204-nvidia-580 --image-project=deeplearning-platform-release \
  --boot-disk-size=200GB --maintenance-policy=TERMINATE \
  --metadata=install-nvidia-driver=True
```

Video von lokal auf die VM kopieren (Syntax verifiziert:
https://docs.cloud.google.com/sdk/gcloud/reference/compute/scp):

```bash
gcloud compute scp data/sessions/2026-09-08_0830/A_pass01.mov \
  openacl-gpu-mono:~/videos/ --zone=europe-west4-a
```

VM nach dem Benchmark stoppen (Abrechnung endet, Platte bleibt bestehen):

```bash
gcloud compute instances stop openacl-gpu-mono --zone=europe-west4-a
```

## 9. Was Anton persönlich tun muss vs. was automatisierbar ist

**Persönlich, weil an die Person gebunden (nicht delegierbar):**
- SMPL-Account anlegen und Modelllizenz akzeptieren auf https://smpl.is.tue.mpg.de
- Zusätzlicher Account/Lizenzakzeptanz auf https://smplify.is.tue.mpg.de
- Die heruntergeladenen SMPL-Modell-Dateien anschließend manuell auf die VM legen (`gcloud compute scp`),
  da der Download-Link an den persönlichen Account gebunden ist

**Automatisierbar (kann ich mit `gcloud`/Skripten erledigen, sobald die SMPL-Dateien vorliegen):**
- VM anlegen, Treiber/Docker/Repo installieren
- WHAM-, ViTPose-, DPVO-Checkpoints herunterladen (keine Registrierung nötig, MIT/Apache-2.0)
- Video-Transfer, Pipeline-Lauf, Export-Dateien zurückkopieren
- VM stoppen/löschen

## 10. Offene Punkte (nicht verifiziert)

- VRAM-Anforderung von opencap-monocular selbst
- Verarbeitungszeit pro Sekunde Video / Referenz-GPU aus README oder Paper
- Verhalten bei unbekanntem iPhone-Modell in der Intrinsics-Datenbank
- Unterstützte Eingabe-Videoauflösungen/-formate
- Genauer Bedienablauf der opencap.ai-Web-App für die Monocular-Variante (Account, Upload, Export) – nicht per
  automatisiertem Fetch prüfbar, manueller Test im Browser empfohlen

## Quellen

- https://github.com/utahmobl/opencap-monocular
- https://raw.githubusercontent.com/utahmobl/opencap-monocular/main/README.md
- https://raw.githubusercontent.com/utahmobl/opencap-monocular/main/LICENSE
- https://raw.githubusercontent.com/utahmobl/opencap-monocular/main/installation/INSTALL_SLIM.md
- https://raw.githubusercontent.com/utahmobl/opencap-monocular/main/docker/README.md
- https://raw.githubusercontent.com/utahmobl/opencap-monocular/main/WHAM/README.md
- https://arxiv.org/abs/2603.24733
- https://arxiv.org/pdf/2603.24733
- https://mobl.mech.utah.edu/opencap-monocular-released/
- https://www.opencap.ai
- https://visualizer.opencap.ai
- https://smpl.is.tue.mpg.de
- https://smplify.is.tue.mpg.de
- https://smpl.is.tue.mpg.de/modellicense
- https://polyformproject.org/licenses/noncommercial/1.0.0
- https://docs.cloud.google.com/compute/docs/gpus/gpu-regions-zones
- https://docs.cloud.google.com/deep-learning-vm/docs/images
- https://docs.cloud.google.com/sdk/gcloud/reference/compute/scp
