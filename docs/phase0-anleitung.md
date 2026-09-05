<!-- Recherche-Stand: 2026-09-05, per WebSearch/WebFetch gegen Primärquellen geprüft (Apple-Support-Doku,
Apple-Developer-Doku, opencap.ai/App-Store/Papers). Wo nichts verifiziert werden konnte, steht das explizit
dabei statt einer Vermutung. Quellen am Ende jedes Abschnitts. -->

# Phase 0 – Anleitung für Anton

Schritt-für-Schritt-Checkliste für Session 1 (siehe `docs/ROADMAP.md` Phase 0 und `docs/PROTOKOLL-AUFNAHME.md`
für Ort/Ablauf). Aktuelle iOS-Version zum Zeitpunkt der Recherche: iOS 26 (Patch 26.6.1, 27.08.2026); iOS 27
wird für Herbst 2026 erwartet und könnte während Phase 0 schon aufspielbar sein – die unten genannten
Menüpfade sind laut Apple-Support-Doku über die letzten iOS-Versionen stabil geblieben, für iOS-Versionen vor
17 nicht verifiziert.
([MacRumors](https://www.macrumors.com/2026/07/27/apple-releases-ios-26-6/), [Wikipedia iOS 26](https://en.wikipedia.org/wiki/IOS_26))

## 1. iPhone-Kameraeinstellungen

Auf **beiden** iPhones vor Session 1 einmal einstellen (danach bleibt es gespeichert, bis du es änderst):

- [ ] **Auflösung/fps:** `Einstellungen → Kamera → Video aufnehmen` → **1080p HD bei 60 fps** wählen.
  In iOS 26 kannst du das auch direkt in der Kamera-App per Wisch-Geste nach oben während der Aufnahme sehen/
  ändern, ohne die App zu verlassen – ersetzt aber nicht die Grundeinstellung.
  ([Apple Support](https://support.apple.com/guide/iphone/change-video-recording-settings-iphc1827d32f/ios), [AppleInsider](https://appleinsider.com/inside/ios-26/tips/inside-camera-in-ios-26----the-essentials-of-iphone-photography))
- [ ] **Codec – Maximale Kompatibilität:** `Einstellungen → Kamera → Formate` → **„Maximale Kompatibilität“**
  wählen (H.264/JPEG), nicht „Hohe Effizienz“ (HEVC/HEIF). Damit liest OpenCV das Video später ohne
  Umwandlung. ([Apple Support 109041](https://support.apple.com/en-us/109041))
- [ ] **HDR-Video aus:** gleicher Bildschirm wie oben, `Einstellungen → Kamera → Video aufnehmen` →
  Schalter „HDR-Video“ ausschalten. ([Apple Support](https://support.apple.com/guide/iphone/change-video-recording-settings-iphc1827d32f/ios))
- [ ] **Kinomodus aus:** Kinomodus ist kein Schalter, sondern ein eigener Modus im Moduskarussell der
  Kamera-App (neben Foto/Video/Zeitlupe). Einfach beim Aufnehmen auf „Video“ bleiben, nicht auf „Kino“ wischen.
  ([Apple Support HT212778](https://support.apple.com/en-us/HT212778))
- [ ] **Aktionsmodus aus:** Im Video-Modus oben links auf das Aktionsmodus-Symbol (durchgestrichene laufende
  Figur) tippen – gelb = aktiv, nochmal tippen deaktiviert. Vor jeder Aufnahme kurz prüfen.
  ([BGR](https://www.bgr.com/1964079/how-to-use-action-mode-on-iphone/))
- [ ] **Belichtung/Fokus sperren (AE/AF-Lock):** In der Kamera-App auf die Person im Sucher tippen und
  gedrückt halten, bis oben gelb „AE/AF-Sperre“ erscheint, dann loslassen. Bei iPhone 16 und neuer geht das
  alternativ über die Kamerasteuerungs-Taste (leicht drücken und halten), muss aber vorher unter
  `Einstellungen → Kamera → Kamerasteuerung` aktiviert werden. Zum Lösen an anderer Stelle tippen.
  ([iPhonePhotographySchool](https://iphonephotographyschool.com/ae-af-lock/), [idownloadblog](https://www.idownloadblog.com/2024/11/13/apple-ios-18-2-iphone-camera-control-lock-focus-exposure/))
- [ ] Objektiv auf 1x lassen (kein Ultraweitwinkel, siehe `docs/PROTOKOLL-AUFNAHME.md`).

## 2. Videos auf den Mac bringen (ohne Transkodierung)

**Empfehlung: Kabel + Image Capture**, nicht AirDrop.

- AirDrop transkodiert HEVC unter Umständen zu H.264 (erneute Kompression, Qualitätsverlust) – da du ohnehin
  schon auf H.264 aufnimmst (Schritt 1), ist das Risiko geringer, aber wiederkehrende Nutzerberichte zeigen
  reale Probleme. Die relevante Einstellung dagegen ist nicht AirDrop-spezifisch, sondern
  `Einstellungen → Fotos → Auf Mac oder PC übertragen` → **„Originale behalten“** statt „Automatisch“.
  ([Apple Support 120267](https://support.apple.com/en-us/120267), [totalmedia.ai](https://www.totalmedia.ai/en/resources/blog/why-videos-look-worse-after-airdrop))
- [ ] **Weg der Wahl – Image Capture:** iPhone per Kabel an den Mac, App „Digitale Bilder“ (Image Capture)
  öffnen, iPhone in der Seitenleiste wählen. Unten links auf „Nach Import löschen“ klicken und auf
  **„Originale behalten“** stellen. Zielordner direkt auf einen Zwischenordner setzen (z. B. Schreibtisch),
  von dort in `data/sessions/...` einsortieren. Umgeht die Fotomediathek komplett, erhält Metadaten wie fps
  am zuverlässigsten. ([Apple Support Image Capture](https://support.apple.com/guide/image-capture/image-capture-user-guide-imgcp1003/mac), [AppleInsider](https://appleinsider.com/inside/macos/tips/how-to-import-photos-using-the-image-capture-app-on-mac))
- Alternative: Fotos-App-Import (`Datei → Importieren`, nach Kabelverbindung). Landet aber erst in der
  Fotomediathek und muss von dort separat exportiert werden – ein Umweg mehr.
  ([Apple Support](https://support.apple.com/guide/photos/import-from-a-camera-or-phone-pht6c803201/mac))
- Ein Menüpunkt „Finder-Import Originale“ wie ursprünglich angenommen ließ sich **nicht verifizieren** –
  der direkte Kamerarollen-Zugriff über den Finder-Gerätefinder existiert für Videos so nicht mehr, der
  offizielle Weg läuft über Fotos-App oder Image Capture.

## 3. Ablage

Ordnerstruktur laut `docs/PROTOKOLL-AUFNAHME.md`:

```
data/sessions/YYYY-MM-DD_HHMM/
  meta.yaml
  A_pass01.mov, A_pass02.mov, ...
  B_pass01.mov, B_pass02.mov, ...
```

`meta.yaml` mit den Feldern aus dem Protokoll ausfüllen (Datum, Zeit, post-op Wochen, Ort, Schuhe, Schmerz,
Müdigkeit, Schlaf, Aktivität gestern, Kamera-Setup). `data/` ist gitignored, bleibt lokal.

**Checkliste für die Session (Kurzfassung, Details in `docs/PROTOKOLL-AUFNAHME.md`):**

- [ ] Ort mit geradem, ebenem 10–12-m-Weg, ruhiger einfarbiger Hintergrund
- [ ] Start, Ende und Kamerapositionen mit **Klebeband** markieren
- [ ] Kamera A sagittal, rechtwinklig zum Weg, 4–5 m Abstand, **Stativhöhe** ca. 0,9–1,0 m (Hüfthöhe)
- [ ] Kamera B (falls genutzt) frontal-schräg 45°, gleiche Höhe
- [ ] Beide Kameras: Einstellungen aus Schritt 1 geprüft, Objektiv 1x
- [ ] Enge, einfarbige Kleidung, immer dieselben Schuhe
- [ ] Metadaten in `meta.yaml` notieren
- [ ] 2 Minuten einlaufen
- [ ] Lautes **Klatschen** am Anfang zur späteren Synchronisation beider Kameras
- [ ] **10 Durchgänge** sagittal, abwechselnd links↔rechts, normales Tempo
- [ ] Optional: 4 Durchgänge bewusst schnell, 4 Durchgänge frontal auf Kamera B zu/weg
- [ ] **30 Minuten Pause**, Kameras nicht anfassen
- [ ] **Wiederholung:** Schritt „10 Durchgänge“ komplett erneut (Grundlage für den eigenen Messfehler/MDC)

## 4. OpenCap Web-App mit zwei iPhones

- [ ] App **„OpenCap“** aus dem App Store laden (Entwickler Model Health, Inc., benötigt iOS 15.6+), auf
  beiden iPhones. ([App Store](https://apps.apple.com/us/app/opencap/id1630513242))
- [ ] Account auf der Web-App (vermutlich unter `app.opencap.ai`, Session per QR-Code mit dem iPhone
  verbinden) anlegen. **Ob ein Account zwingend nötig ist, war per automatisiertem Abruf nicht abschließend
  zu verifizieren** – die Terms-Seite ist eine JavaScript-Anwendung ohne extrahierbaren Text, im Zweifel beim
  Durchklicken der App selbst prüfen.
- [ ] Kalibrierungsmuster ausdrucken: **Schachbrett 210 × 175 mm, 5×6 Felder, 35 mm Kantenlänge**, auf A4.
  Beim Drucken „Originalgröße/100 %“ einstellen, nicht „an Seite anpassen“, sonst stimmen die Maße nicht.
  Größeres Präzisionsbrett (720 × 540 mm, 9×12 Felder, 60 mm) ist eine Alternative mit ähnlicher Genauigkeit,
  für den Hausgebrauch reicht das A4-Muster. ([MDPI Review](https://www.mdpi.com/2673-7078/5/4/88))
- [ ] Ablauf laut App: (1) **Kalibrierung** – Schachbrett kurz in beide Kamerabilder halten, OpenCap berechnet
  die Kameraposition daraus; (2) **Neutralpose** – ruhig stehen, App führt durch die Pose; (3) **Aufnahme**
  der Aktivität (Trial-Typ „walking“ wählen). ([PLOS Comp Biology](https://journals.plos.org/ploscompbiol/article?id=10.1371%2Fjournal.pcbi.1011462))
- [ ] **Export:** Der herunterladbare Session-Ordner enthält `CalibrationImages/`, `MarkerData/` (**.trc**),
  `OpenSimData/` (**.mot**) und `Videos/`. Für Massen-/Batch-Download gibt es zusätzlich das Repo
  `opencap-processing`. ([DeepWiki](https://deepwiki.com/opencap-org/opencap-core/2-getting-started), [GitHub opencap-processing](https://github.com/stanfordnmbl/opencap-processing))
- [ ] **Nutzungsbedingungen (verifiziert 2026-09-05 aus dem Quelltext der Terms-Seite):** Stanford stellt
  OpenCap „free of charge for academic or non-profit organization non-commercial research or educational use
  only“ bereit; Nutzung durch „any commercial entity for any purpose“ ist untersagt, ebenso Nutzung „on
  behalf of any organization that is not a non-profit organization“. Ein Account mit Passwort ist Pflicht
  (Punkt 12 der Terms). Alle Daten sind laut Terms „visible to and may be used by the development team“.
  Einordnung: Private Einzelnutzung ohne Organisation und ohne Gewinnabsicht ist weder ausdrücklich erlaubt
  noch ausdrücklich verboten. Das ist eine Grauzone und deine Entscheidung. Falls du sie nutzt, dann nur
  als persönliche Referenzmessung, nie als Teil des OpenACL-Produktionspfads. Bei Unsicherheit kurz an
  info@opencap.ai schreiben. ([Terms-Seite](https://www.opencap.ai/terms-conditions), [Data Privacy & IRB](https://docs.google.com/document/d/1DBw9LVAuUwgz713037VQjsaD8sj2-AN_hzga_7kXtXI))
- [ ] **OpenCap Monocular Beta (seit März 2026):** gleiche Web-App, ein Handy, Menüpunkt „Get Started → OpenCap
  Monocular“ auf opencap.ai. Gleiche Nutzungsbedingungen wie oben. Für dich der einfachste Weg zu einer
  3D-Referenz ohne GPU-VM, siehe `research/opencap-monocular/SETUP.md`.
- [ ] **Datenspeicherung:** Laut Paper auf Stanford-eigener Cloud-Infrastruktur, Ende-zu-Ende-verschlüsselt.
  Genauer Cloud-Anbieter dahinter nicht genannt – nicht verifiziert. Explizite Datenlimits für Privatnutzer
  2026 wurden nicht gefunden – nicht verifiziert.

## 5. Apple-Health-Export

- [ ] Health-App öffnen → **Profilbild oben rechts** antippen → ganz unten **„Alle Gesundheitsdaten
  exportieren“** antippen → erzeugt `export.zip`. Entpackt liegt darin **`export.xml`** (und zusätzlich
  `export_cda.xml`, klinisches CDA-Format, kannst du ignorieren).
  ([applehealthdata.com](https://applehealthdata.com/export-apple-health-data/))
- [ ] Datei ablegen unter **`data/health/export.xml`** (gitignored, bleibt lokal).
- **Relevante Record-Typen** (Identifier laut Apple-Developer-Doku bestätigt; in der `export.xml` mit dem
  Präfix `HKQuantityTypeIdentifier` versehen):
  - `WalkingAsymmetryPercentage` – Anteil Schritte mit L/R-Geschwindigkeitsunterschied
    ([Doku](https://developer.apple.com/documentation/healthkit/hkquantitytypeidentifier/walkingasymmetrypercentage))
  - `WalkingSpeed` – durchschnittliche Ganggeschwindigkeit auf ebenem Untergrund
    ([Doku](https://developer.apple.com/documentation/healthkit/hkquantitytypeidentifier/walkingspeed))
  - `WalkingDoubleSupportPercentage` ([Doku](https://developer.apple.com/documentation/healthkit/hkquantitytypeidentifier/walkingdoublesupportpercentage))
  - `WalkingStepLength` ([Doku](https://developer.apple.com/documentation/healthkit/hkquantitytypeidentifier/walkingsteplength))
  - `AppleWalkingSteadiness` ([Doku](https://developer.apple.com/documentation/healthkit/hkquantitytypeidentifier/applewalkingsteadiness))
- [ ] **Ohne Apple Watch, nur iPhone:** bestätigt möglich, Bedingung ist iPhone ab Modell 8 mit iOS 15+,
  **nah am Körper getragen** (Hosentasche, Gürteltasche, Handtasche) – nicht in der Hand oder im Rucksack.
  ([Apple Support 102504](https://support.apple.com/en-us/102504), [Superage](https://www.superage.app/en/blog/apple-watch-gait-metrics-walking-asymmetry-steadiness/))

## 6. Beim Physio erfragen

Kurze Liste zum Mitnehmen:

- [ ] **Quadrizeps-Kraft-LSI** (Limb Symmetry Index) – isokinetisch oder per Handdynamometer, in %
- [ ] **Hop-Test-Batterie als LSI:** Single Hop, Triple Hop, Crossover Hop, 6-m-Timed-Hop, jeweils in %
- [ ] **Kniestreckdefizit** in Grad (aktiv/passiv angeben lassen)
- [ ] **Datum der Messung** (für den Abgleich mit dem eigenen Session-Datum)

## Offene Punkte (nicht verifiziert)

- Ob für die OpenCap-Web-App zwingend ein Account nötig ist
- Genauer Wortlaut der OpenCap-Nutzungsbedingungen für private Einzelnutzer (Terms-Seite technisch nicht
  auslesbar, im Browser selbst prüfen)
- Cloud-Anbieter hinter der Stanford-OpenCap-Infrastruktur
- Menüpfade für iOS-Versionen älter als 17

## Quellen (gesamt)

- https://www.macrumors.com/2026/07/27/apple-releases-ios-26-6/
- https://en.wikipedia.org/wiki/IOS_26
- https://support.apple.com/guide/iphone/change-video-recording-settings-iphc1827d32f/ios
- https://appleinsider.com/inside/ios-26/tips/inside-camera-in-ios-26----the-essentials-of-iphone-photography
- https://support.apple.com/en-us/109041
- https://support.apple.com/en-us/HT212778
- https://www.bgr.com/1964079/how-to-use-action-mode-on-iphone/
- https://iphonephotographyschool.com/ae-af-lock/
- https://www.idownloadblog.com/2024/11/13/apple-ios-18-2-iphone-camera-control-lock-focus-exposure/
- https://support.apple.com/en-us/120267
- https://www.totalmedia.ai/en/resources/blog/why-videos-look-worse-after-airdrop
- https://support.apple.com/guide/image-capture/image-capture-user-guide-imgcp1003/mac
- https://appleinsider.com/inside/macos/tips/how-to-import-photos-using-the-image-capture-app-on-mac
- https://support.apple.com/guide/photos/import-from-a-camera-or-phone-pht6c803201/mac
- https://apps.apple.com/us/app/opencap/id1630513242
- https://www.mdpi.com/2673-7078/5/4/88
- https://journals.plos.org/ploscompbiol/article?id=10.1371%2Fjournal.pcbi.1011462
- https://deepwiki.com/opencap-org/opencap-core/2-getting-started
- https://github.com/stanfordnmbl/opencap-processing
- https://www.opencap.ai/terms-conditions
- https://applehealthdata.com/export-apple-health-data/
- https://developer.apple.com/documentation/healthkit/hkquantitytypeidentifier/walkingasymmetrypercentage
- https://developer.apple.com/documentation/healthkit/hkquantitytypeidentifier/walkingspeed
- https://developer.apple.com/documentation/healthkit/hkquantitytypeidentifier/walkingdoublesupportpercentage
- https://developer.apple.com/documentation/healthkit/hkquantitytypeidentifier/walkingsteplength
- https://developer.apple.com/documentation/healthkit/hkquantitytypeidentifier/applewalkingsteadiness
- https://support.apple.com/en-us/102504
- https://www.superage.app/en/blog/apple-watch-gait-metrics-walking-asymmetry-steadiness/
