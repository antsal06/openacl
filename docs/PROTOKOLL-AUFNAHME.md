# Aufnahmeprotokoll v0.1

Ziel: Aufnahmen, die zwischen Sessions vergleichbar sind. Gleicher Ort, gleiche Kamerapositionen, gleiche Schuhe, gleiche Uhrzeit. Vergleichbarkeit schlägt Perfektion.

## Ort

- Gerader, ebener Weg von mindestens 10 m, besser 12 m. Flur, Turnhalle, Tiefgarage, Gehweg.
- Die mittleren 4 bis 5 m sind der Messbereich. Davor und danach je 3 m zum Anlaufen und Auslaufen, damit du im Bild schon im normalen Gang bist.
- Ruhiger, einfarbiger Hintergrund ohne andere Personen. Gleichmäßiges Licht, kein Gegenlicht.
- Markiere Start, Ende und die Kamerapositionen mit Klebeband, damit jede Session gleich ist.

## Kameras

**Kamera A, sagittal (Pflicht).** Seitlich, exakt rechtwinklig zur Gehrichtung, 4 bis 5 m Abstand vom Gehweg, Stativ auf Hüfthöhe (etwa 0,9 bis 1,0 m). Querformat. Der ganze Körper inklusive Füße muss über den gesamten Messbereich im Bild sein. Kamera bewegt sich nicht, kein Zoom, kein Nachführen.

**Kamera B, frontal-schräg (empfohlen).** Zweites iPhone am Ende des Weges, etwa 45° zur Gehrichtung, gleiche Höhe, so dass der Messbereich im Bild ist. Für Pose2Sim und als Referenz. Beide Kameras nehmen gleichzeitig auf, ein lautes Klatschen am Anfang synchronisiert sie später.

**Kamera-Einstellungen (beide):** 1080p, **60 fps**, keine HDR-, Kino- oder Action-Modus-Effekte, Belichtung und Fokus per langem Tippen sperren. Objektiv 1x, nicht Ultraweitwinkel (Verzerrung).

## Kleidung

- Enge, einfarbige Kleidung, die sich vom Hintergrund abhebt. Kurze Hose oder enge Leggings, damit das Knie sichtbar ist. Keine weiten Hosen.
- Immer dieselben Schuhe. Barfuß ist eine Option, dann jede Session barfuß.

## Ablauf pro Session

1. Metadaten notieren (siehe unten).
2. 2 Minuten locker einlaufen.
3. **10 Durchgänge sagittal**, abwechselnd von links nach rechts und von rechts nach links, damit jedes Bein fünfmal kameranah ist. Selbstgewähltes, normales Tempo. Nicht auf den Gang konzentrieren, an etwas anderes denken.
4. Optional 4 Durchgänge bewusst schnell (für die Geschwindigkeitsabhängigkeit).
5. Optional 4 Durchgänge direkt auf Kamera B zu und von ihr weg (Frontalebene, nur qualitativ).
6. Für die Messfehler-Schätzung in Phase 0: nach 30 Minuten Pause Schritt 3 komplett wiederholen, Kameras nicht anfassen.

Ergebnis: rund 40 bis 50 Gangzyklen pro Bein pro Session. Das ist genug zum Mitteln.

## Metadaten je Session

Datei `data/sessions/YYYY-MM-DD_HHMM/meta.yaml`:

```yaml
date: 2026-09-05
time: "19:30"
post_op_weeks: 26
subject:                   # ADR-0009; nötig für Meter-Skalierung, Froude-Klasse und Seitenzuordnung
  height_m: 1.80
  mass_kg: 75
  operated_side: R         # L oder R
  surgery_date: 2026-03-01
  graft: "STG (Hamstring)"
location: "Flur Keller"
shoes: "Laufschuh X"
pain_now_0_10: 1          # aktueller Schmerz, operiertes Knie
pain_contra_0_10: 2       # aktueller Schmerz, Gegenseite
fatigue_0_10: 2
sleep_hours: 7
activity_yesterday: "Rad 40 min"
notes: ""
cameras:
  A: { device: "iPhone 15", position: "sagittal links vom Weg, 4.5 m, 0.95 m Höhe", fps: 60 }
  B: { device: "iPhone 13", position: "45° Wegende, 0.95 m Höhe", fps: 60 }
```

Videos daneben ablegen als `A_pass01.mov`, `B_pass01.mov` usw. Der Ordner `data/` bleibt lokal, nie ins Repo.

## Häufige Fehler

- Kamera nicht rechtwinklig: Winkel werden systematisch falsch. Mit einem Lot oder der Wasserwaage im Kamera-Raster prüfen.
- Zu nah: Füße oder Kopf verlassen das Bild, Perspektive verzerrt. Lieber 5 m als 3 m.
- 30 fps: Gangereignisse werden auf ±33 ms ungenau. Immer 60.
- Andere Personen im Bild: Pose-Modell springt zwischen Personen.
- Bewusst „schön“ gehen: misst dann den Vorsatz, nicht den Gang.

## Zweite Variante: OpenCap Web-App

Für die 3D-Referenz in Phase 0. Zwei iPhones auf Stativen, jeweils etwa 45° links und rechts vor dir, Abstand 3 bis 4 m, Schachbrett laut Anleitung auf opencap.ai ausdrucken und kalibrieren. Die App führt durch den Rest. Kostenlos für Forschung und private Nutzung, Daten liegen dann auf Stanford-Servern.
