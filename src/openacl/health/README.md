# `openacl.health` – Apple-Health-Export als zweite Gangmetrik-Quelle

Diese Schicht setzt den Apple-Health-Teil von **ADR-0005** um: das iPhone misst beim Tragen in
der Hosentasche ohnehin täglich ein paar Gangmetriken (Gehgeschwindigkeit, Schrittlänge,
Doppelstützzeit, Gehasymmetrie, „Walking Steadiness“). Diese Schicht liest sie aus dem
Health-Export, rechnet sie in SI-Einheiten um und aggregiert sie zu Tages-/Wochenwerten und
einem Periodenvergleich rund um das OP-Datum. Sie ist **kein Ersatz** für die videobasierte
Kinematik-Engine (Schicht 2/3) und liefert **keine Gelenkwinkel** – siehe „Was das nicht ist“
unten.

Noch nicht in `openacl.cli` verdrahtet; Aufruf über `python -m openacl.health`.

## Export holen

iPhone: Health-App → Profilbild oben rechts → „Gesundheitsdaten exportieren“ → `export.zip`
per AirDrop/Mail/Dateien aufs Notebook holen. Das Zip enthält `apple_health_export/export.xml`
(alle Records) und `export_cda.xml` (klinische Dokumente, wird hier ignoriert).

**Nichts davon gehört ins Repo.** `data/` ist per `.gitignore` komplett ausgeschlossen; dieses
Modul liest `export.zip`/`export.xml` nur lokal von der Platte, kopiert nichts, und die Tests
verwenden ausschließlich eine synthetische, frei erfundene XML-Fixture
(`tests/health/synthetic.py`) – kein Zugriff auf `data/` in Tests.

## Benutzung

```bash
python -m openacl.health data/health/export.zip \
    --out data/health/derived \
    --surgery-date 2026-03-01   # Platzhalter, bis das echte OP-Datum feststeht
```

Schreibt in `--out`:

- `health_daily.parquet` – Tageswerte je Metrik (Mittelwert, Median, SD, n) plus gleitender
  7-Tage-Median (`daily.py: rolling_median_7d`)
- `health_summary.json` – Periodenvergleich (vor OP / 0–6 / 6–12 / 12–26 / >26 Wochen post-OP)
  je Metrik, inklusive der Doppelstütz-Messgüte-Notiz (siehe unten)
- `health_trends.png` – vier Panels (Geschwindigkeit, Schrittlänge, Doppelstütz, Asymmetrie)
  über die Zeit, Tagesmedian als Punkte, 7-Tage-Median als Linie, OP-Datum als gestrichelte
  Linie, Reha-Perioden schattiert

Als Bibliothek:

```python
from openacl.health import load_gait_export, rolling_median_7d, period_summary_json

df = load_gait_export("data/health/export.zip")  # oder export.xml direkt
daily = rolling_median_7d(df)
summary = period_summary_json(df, surgery_date=date(2026, 3, 1))
```

## Gelesene Record-Typen und Einheiten

| Apple-Typ (`HKQuantityTypeIdentifier...`) | `metric`-Spalte | Rohquelle → gespeicherte Einheit |
|---|---|---|
| `WalkingSpeed` | `walking_speed_m_s` | `km/hr` → `m/s` (÷3,6); `m/s` unverändert |
| `WalkingStepLength` | `step_length_m` | `cm` → `m` (÷100); `m` unverändert |
| `WalkingDoubleSupportPercentage` | `double_support_pct` | HealthKit-Bruch (0–1, `unit="%"`) → ×100 |
| `WalkingAsymmetryPercentage` | `walking_asymmetry_pct` | HealthKit-Bruch → ×100 |
| `AppleWalkingSteadiness` | `walking_steadiness_pct` | HealthKit-Bruch → ×100 |
| `StepCount` | `step_count` | `count`, nur als Aktivitätskontext |

**HealthKit-Falle:** Die drei Prozent-Metriken tragen `unit="%"`, HealthKit speichert darunter
aber den **Bruch** (0–1), nicht die Prozentzahl – z. B. bedeutet ein Doppelstütz-Rohwert von
`0.28` 28 %, nicht 0,28 %. Dieses Modul rechnet mit ×100 um, damit die Zahl zur `_pct`-Endung
im Namen passt (Konvention: jede Zahl trägt ihre Einheit im Namen). Empirisch gegen den
eigenen Export geprüft (Werte plausibel im Bereich 15–35 % für Doppelstütz, 0–100 % für
Asymmetrie und Steadiness); ein Export mit einer anderen Einheit als den hier gelisteten löst
einen `ValueError` aus, statt die Zahl still falsch zu skalieren.

Der Parser (`export.py`) ist `iterparse`-basiert (kein `ET.parse`), liest wahlweise direkt aus
`export.zip` oder aus `export.xml`, und hält beim echten ~90-MB/~120k-Record-Export den
Speicherbedarf niedrig, weil bereits verarbeitete Elemente laufend aus dem Baum entfernt
werden. `startDate`/`endDate` werden mit ihrem eigenen UTC-Offset geparst und sofort nach UTC
konvertiert (`start`/`end`-Spalten sind tz-aware UTC); lokale Kalendertage/-wochen für die
Aggregation entstehen erst in `daily.py` (`local_tz`, Default `Europe/Vienna`).

## Aggregation und Periodenvergleich (`daily.py`)

- `daily_stats` / `weekly_stats`: Mittelwert, Median, SD, n je Metrik und Tag/ISO-Woche
  (lokale Zeitzone).
- `rolling_median_7d`: gleitender 7-Tage-Median der Tagesmediane, Lücken (Tage ohne Records)
  werden übersprungen statt als 0 gewertet.
- `period_summary` / `period_summary_json`: derselbe Aufbau, aber gruppiert nach Reha-Periode
  relativ zu `surgery_date` (vor OP; 0–6, 6–12, 12–26, >26 Wochen post-OP).

**Messgüte, nicht nur Doku, sondern im Code (`DOUBLE_SUPPORT_ICC_NOTE`) und in
`health_summary.json`:** Apples Doppelstützzeit hat gegenüber einem Laborreferenzsystem nur
eine Intraclass-Correlation von 0,42–0,58 (Sci Rep 2023;13, doi:10.1038/s41598-023-32550-3).
Konsequenz: Diese Werte sind als **Trend über Tage/Wochen** brauchbar, ein einzelner
Tageswert ist **kein verlässlicher Messwert**. Das gilt der Sache nach für alle Health-Export-
Gangmetriken hier – sie stammen aus proprietären Apple-Algorithmen ohne veröffentlichte
Validierung gegen ein Ganglabor, mit Ausnahme des zitierten Doppelstütz-ICCs.

## Plot (`plot.py`)

Vier Panels, deutsche Beschriftung, neutrale Sprache (ADR-0004: „Beobachtung, keine Diagnose
oder Therapieempfehlung“ steht als Fußzeile auf jedem Plot). Punkte = Tagesmedian, Linie =
gleitender 7-Tage-Median, gestrichelte Linie = OP-Datum, graue Flächen = Reha-Perioden
(Beschriftung nur bei ausreichend breiten Perioden, sonst nur Schattierung, um Textüberlappung
bei sehr ungleich langen Prä-/Post-OP-Zeiträumen zu vermeiden).

## Was diese Zahlen NICHT sind

- **Keine Gelenkwinkel.** Kein Kniewinkel, keine Standphasenanteile aus Kinematik – das ist
  Schicht 2/3 (`openacl.backends`, `openacl.core`), aus Video. Diese Schicht liefert nur die
  vier iPhone-Gangmetriken plus Schrittzahl als Aktivitätskontext.
- **Keine Diagnose, keine Therapieempfehlung** (ADR-0004, MDR Regel 11). Auffälligkeiten hier
  sind Beobachtungen zur Besprechung mit Fachpersonal, nicht mehr.
- **Kein validiertes Messinstrument.** Die zugrunde liegenden Apple-Algorithmen sind nicht
  offen dokumentiert; nur für die Doppelstützzeit existiert eine veröffentlichte
  Validierungsstudie (s. o.), und die zeigt mäßige Übereinstimmung mit einem Laborsystem.
- **Kein Ersatz für den Seitenvergleich.** Der Health-Export unterscheidet nicht zwischen
  operiertem und nicht-operiertem Bein; er ist ein globaler, geräteseitig gemittelter Wert pro
  Gehepisode.

## Bekannte Einschränkungen

- Nur die sechs oben gelisteten Record-Typen werden gelesen; alles andere im Export (Workouts,
  Herzfrequenz, Schlaf, …) wird beim Streaming ignoriert und nie in den Speicher geladen.
- `local_tz` (Default `Europe/Vienna`) bestimmt, welchem Kalendertag ein Record kurz vor/nach
  Mitternacht zugeordnet wird; bei Reisen in andere Zeitzonen kann das für einzelne Tage an der
  Grenze leicht verschieben.
- Der Periodenvergleich ist ein einfacher Gruppenvergleich (Mittelwert/Median/SD/n je Periode),
  kein Signifikanztest und kein MDC-Gate wie in `openacl.core.mdc` – dafür fehlen hier
  Wiederholungsmessungen im engeren Sinn (ADR-0009). Wer die Zahlen im Verlauf über Wochen
  bewerten will, sollte trotzdem eher `rolling_median_7d` als `health_summary.json` ansehen,
  weil Wochen-/Periodengrenzen sonst leicht wie harte Schwellen wirken, wo keine sind.
