# Phase 0 – Ergebnis der ersten Session (2026-09-07, ausgewertet 2026-09-11)

Was wir aus der ersten echten Aufnahme über die *Methode* gelernt haben. Die Beobachtungen zur
Person stehen im privaten Bericht (`data/sessions/2026-09-07/gangbericht.html`, nicht im Repo).
Alles hier ist [ausgeführt], sofern nicht anders markiert.

## Aufbau

Turnhalle, Holzboden, ruhige Holzwand. Kamera A (iPhone 11) sagittal 5 m neben dem Weg, 0,96 m
hoch, 1080p/60 fps. Weg: 3 m Anlaufen, 5 m Messbereich, 3 m Auslaufen, umdrehen, zurück. Vier
Bedingungen als je ein durchlaufendes Video (96 bis 265 s): Socken normal, Socken normal als
Wiederholung nach 30 min, Schuhe, Socken schnell. Zusätzlich zwei OpenCap-Trials (zwei iPhones,
45°, Schachbrett-Kalibrierung, LaiUhlrich2022-Modell, HRNet + LSTM-Augmenter).

## Ausbeute

| Bedingung | Durchgänge | Zyklen im Pool (kameranah) L / R |
| --- | --- | --- |
| Socken 1 | 10 | 10 / 10 |
| Socken 2 | 18 | 18 / 21 |
| Schuhe | 8 | 5 / 9 |
| schnell | 6 | 6 / 5 |
| OpenCap Socken | 1 Trial, 4,6 s verwertbar | 3 / 3 |
| OpenCap Schuhe | 1 Trial, 3,9 s verwertbar | 2 / 2 |

Faustregel: 5 m Messbereich liefern **2 Zyklen je Seite und Durchgang**. Für die 20 bis 40
Zyklen aus `docs/00-SYNTHESE.md` braucht es also 20 bis 40 Durchgänge je Bedingung oder einen
längeren Messbereich.

## Durchsatz

Sports2D `balanced` auf Apple M2 (8 GB, CPU, ONNX Runtime, kein CoreML für die Detektoren mit
ONNX Runtime > 1.26): ca. 4 Bilder/s, also rund 60 s je 4-s-Durchgang. Zwei Sessions parallel
sind möglich, drei sprengen den Arbeitsspeicher. Eine Session mit 18 Durchgängen dauert etwa
20 min. Die Segmentierung (`openacl segment`) braucht 20 s je 3-Minuten-Video.

## Backend-Vergleich Sports2D (1 Kamera, 2D) gegen OpenCap (2 Kameras, 3D)

Nicht dieselben Durchgänge, aber dieselbe Person am selben Nachmittag.

| Größe | Sports2D (Socken, 20 Zyklen) | OpenCap (Socken, 6 Zyklen) | Lesart |
| --- | --- | --- | --- |
| Peak Knieflexion Schwung | 61 bis 62° | 61 bis 63° | einig |
| Minimum Knieflexion mittlere Standphase | 9 bis 12° | 3 bis 6° | Sports2D liest die Standphase gebeugter; Normband (Marker) liegt bei ~3° |
| Peak Hüftextension | −8 bis −10° | −19° | Sports2D-Hüftwinkel nutzt den Rumpfvektor, OpenCap das Becken; nicht vergleichbar |
| Peak Plantarflexion | siehe Artefakte | −11 bis −13° | Seitenkamera unbrauchbar für das Sprunggelenk |
| Gehgeschwindigkeit | 1,13 m/s | 1,29 m/s | verschiedene Durchgänge, OpenCap-Weg länger |
| GPS gegen Normband | 5,2 bis 6,1° | 6,7 bis 7,8° | beide im Bereich gesunder Erwachsener (5 bis 6°) |

Schlussfolgerung: Für Knie-Schwungpeak, Zeitmaß und Symmetrie stimmen die Backends überein.
Für absolute Standphasen-Winkel und Hüftextension hat die 2D-Messung einen Methoden-Offset gegen
das markerbasierte Normband; der **Seitenvergleich** bleibt davon unberührt, der **Normvergleich**
in der Standphase nicht.

## Wiederholungsstreuung (eigener MDC, Socken 1 gegen Socken 2)

Innerhalb-Tag, Kamera unberührt, 10 Paare je Kennzahl (Durchgang × kameranahe Seite), Werte in
`data/subject/mdc.yaml` (privat). Größenordnung:

| Kennzahl | MDC95 eigen | ICC(2,1) | Literatur-MDC |
| --- | --- | --- | --- |
| Peak Knieflexion Schwung | 3,1° | 0,34 | 9,2° |
| Min. Knieflexion Standphase | 2,1° | 0,60 | 7,5° (generisch) |
| Knieflexion bei Fersenkontakt | 3,3° | 0,75 | 7,5° |
| Standphase | 3,2 pp | −0,30 | 5 pp (Platzhalter) |
| Stride-Zeit | 0,03 s | 0,73 | 0,05 s (Platzhalter) |
| Gehgeschwindigkeit | 0,12 m/s | 0,40 | 0,10 m/s (Platzhalter) |

Zwei Dinge daran sind wichtig. Erstens: Die ICC-Werte sind niedrig bis negativ, obwohl die
Messung reproduziert. Grund ist die geringe Streuung *zwischen* den Durchgängen bei einem sehr
regelmäßigen Gang; der ICC teilt Zwischen-Target-Varianz durch Gesamtvarianz und wird bei
homogenen Targets klein. Der MDC95 kommt aus dem SEM und bleibt davon unberührt. Zweitens: Der
eigene MDC ist ein Innerhalb-Tag-Wert unter identischen Bedingungen, also die *Untergrenze* dessen,
was das Verfahren auflösen kann. Zwischen Tagen, Kamerapositionen oder Kleidung liegt er höher;
die Literaturwerte (7,5 bis 9,2°) sind Zwischen-Tag-Werte. Beide Referenzen gehören in jeden
Report, und ein Unterschied zwischen ihnen ist nicht „belastbar“, sondern „wiederholbar an
diesem Tag“.

## Artefakte, die man kennen muss

1. **Sichtseiten-Flip von Sports2D.** Sports2D entscheidet je Frame aus der Fersen-Zehen-Orientierung,
   welche Seite sichtbar ist, und spiegelt davor die x-Koordinaten. Bei kleinen Füßen (weiße
   Socken auf hellem Holz, 5 m Abstand) werden Ferse und Zehen vertauscht erkannt, die Entscheidung
   kippt, und Knie- (−180°) und Sprunggelenkwinkel (+180°) kommen verschoben heraus. Der
   Bewegungsumfang bleibt exakt erhalten, deshalb ist das ein reiner Offset und wird in
   `openacl.backends.sports2d.unwrap_angles` zurückgerechnet. In einem Durchgang betraf es den
   ganzen Kniekanal der *kameranahen* Seite. Der eigentliche Fix ist, `visible_side` aus der
   Richtung in `passes.yaml` zu setzen (ADR-0010), was seit a8bf1d1 passiert.
2. **Richtungs-Konfundierung.** Bei einer Seitenkamera ist die kameranahe Seite vollständig an die
   Gehrichtung gekoppelt: rechts immer beim Weg nach rechts im Bild, links immer beim Weg nach
   links. Jede richtungsabhängige Verzerrung (Kamera nicht exakt rechtwinklig, Keypoint-Bias)
   erscheint als Seitenunterschied, und die Wiederholung reproduziert ihn. Konkret: Peak
   Plantarflexion −5° auf der einen, −25° auf der anderen Seite, in allen Durchgängen, mit
   Sports2D-MDC von 2,5°; OpenCap misst −11° gegen −13°. **Sprunggelenkwinkel aus einer
   Seitenkamera sind in diesem Aufbau nicht interpretierbar.** Für das Knie liegt derselbe
   Vorbehalt vor; dort stimmten 2D und 3D aber in der Richtung des Seitenunterschieds überein.
   Gegenmittel: Kamera mit Wasserwaage und Lot rechtwinklig stellen, und ein Zwei-Kamera-Backend.
3. **Sports2D-Perspektivkorrektur** nimmt 10 m Kameraabstand an, wenn nichts anderes gesetzt ist.
   Seit a8bf1d1 kommt der Wert aus `meta.yaml` `cameras.A.distance_m`. Betroffen sind nur
   Meterwerte (Schrittlänge, Geschwindigkeit), nicht Winkel.
4. **Ereignis-Ausreißer.** Ein Durchgang von 42 hatte einen falschen Fersenkontakt (Stride 0,99 s
   statt 1,18 s, Kadenz 131 statt 101). Die Zyklus-Ausreißerregel (2 SD der Stride-Dauer) greift
   innerhalb eines Durchgangs mit nur 2 bis 3 Zyklen nicht. Offener Punkt: Ausreißerregel auf
   Session-Ebene über den gepoolten Stride-Dauern.
5. **OpenCap-IK-Sättigung.** Außerhalb des kalibrierten Bereichs sitzen 9 bis 12 % der Frames
   exakt auf den OpenSim-Koordinatengrenzen (Knie 0,00°, Hüfte −30,00°, Sprunggelenk −50,00°).
   Das sind keine Messwerte; `openacl.backends.opencap` setzt sie auf NaN (ADR-0011).
6. **Normband-Klasse an der Terzilgrenze.** Zwei Sessions derselben Person mit 1,13 und 1,10 m/s
   fielen einmal in „comfortable“ und einmal in „slow“ (Froude 0,133 gegen 0,128 bei Grenze
   0,130). Für Vergleiche innerhalb einer Person sollte die Klasse fixiert werden
   (`--speed-class`), sonst vergleicht man gegen zwei verschiedene Bänder.

## Apple Health als Verlaufsquelle

Der iPhone-Export enthält Gehgeschwindigkeit, Schrittlänge, Doppelstützzeit und Asymmetrie ab
Juli 2024. Die OP-Woche und die Erholung in acht Wochen sind darin ohne jede Kamera sichtbar
(Geschwindigkeit 1,36 → 0,67 → 1,30 m/s, Asymmetrie 0 → 100 → 0 %). Als Trend über Monate ist
das brauchbar; als Absolutwert nicht (Doppelstütz-ICC 0,4 bis 0,6, ADR-0005).

## Was in Phase 0 nicht gemacht wurde

- OpenCap Monocular (gehostete Beta oder GPU-VM) lief nicht; die Zwei-Kamera-Variante hat die
  Referenzfrage ausreichend beantwortet.
- Die 45°-Videos von Kamera B liegen unausgewertet für ein späteres Pose2Sim-Backend.
- Hop-Tests fehlen; ein isometrischer Krafttest vom Mai liegt vor (privat).

## Konsequenzen für das Protokoll

Schuhe statt Socken (stabilere Fuß-Keypoints), 20 Durchgänge je Bedingung, Kamera rechtwinklig
mit Wasserwaage prüfen, `distance_m` und `near_side_when_walking_plus_x` ins `meta.yaml`,
Normband-Klasse je Person fixieren. Eingearbeitet in `docs/PROTOKOLL-AUFNAHME.md`.
