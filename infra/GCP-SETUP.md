# GCP-Setup für OpenACL

Du legst das Projekt an, weil dafür dein Billing-Konto nötig ist. Danach kann ich mit `gcloud` arbeiten.

## 1. Projekt anlegen (du, einmalig)

```bash
gcloud projects create openacl-<suffix> --name="OpenACL"
gcloud billing accounts list
gcloud billing projects link openacl-<suffix> --billing-account=<ACCOUNT_ID>
```

Danach in dieser Session als Default setzen, ohne das andere Projekt anzufassen:

```bash
gcloud config configurations create openacl
gcloud config set project openacl-<suffix>
gcloud config set compute/region europe-west4
gcloud config set compute/zone europe-west4-a
gcloud auth application-default login
```

Mit `gcloud config configurations activate default` kommst du zu `pace-mcp` zurück.

## 2. APIs (Phase 0 und 3)

```bash
gcloud services enable compute.googleapis.com storage.googleapis.com \
  run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com
```

## 3. Phase 0: GPU-VM für OpenCap Monocular

Eine VM mit L4-GPU, nur für den Benchmark, danach löschen oder stoppen. Grobe Kosten: unter 1 Euro pro Stunde, Rechnung läuft nur solange die VM an ist.

```bash
gcloud compute instances create openacl-gpu \
  --zone=europe-west4-a --machine-type=g2-standard-4 \
  --accelerator=type=nvidia-l4,count=1 \
  --image-family=common-cu124-ubuntu-2204 --image-project=deeplearning-platform-release \
  --boot-disk-size=200GB --maintenance-policy=TERMINATE \
  --metadata=install-nvidia-driver=True
gcloud compute instances stop openacl-gpu   # nach dem Benchmark
```

Falls die GPU-Quote in der Region 0 ist, unter IAM → Kontingente „GPUs (all regions)“ und „NVIDIA L4“ auf 1 anheben.

## 4. Phase 3: Cloud Run mit GPU

Kommt später. Kurzfassung: Container in Artifact Registry, `gcloud run deploy --gpu 1 --gpu-type nvidia-l4 --no-cpu-throttling --min-instances 0`, Videos in einem Cloud-Storage-Bucket in `europe-west4`, Sessions in Cloud SQL Postgres oder Firestore.

## Regeln

- Keine Service-Account-Keys herunterladen. Lokal `application-default login`, in Cloud Run die angehängte Service-Identität.
- Buckets nicht öffentlich. Videos sind Gesundheitsdaten.
- Alles, was Geld kostet und nicht auf null skaliert, nach Gebrauch stoppen.
