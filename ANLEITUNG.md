# Fotoaufräumer – Anleitung

Der Fotoaufräumer schaut sich alle Fotos in einem Ordner an und zeigt dir im Browser, **groß und nebeneinander**:

- **Stöbern**: alle Fotos nach Jahr, Monat und Land (z. B. „2024 · Aug · Spanien“).
- **Doppelte**: gleiche oder fast gleiche Fotos, auch Serienbilder. Das beste ist mit ★ markiert.
- **Unscharf**: die verwackelten Fotos, die unschärfsten zuerst.
- **Dokumente?**: Fotos, die nach Zetteln, Rechnungen oder Schrift aussehen.
- **Screenshots** und **WhatsApp**-Bilder, jeweils auf einem eigenen Stapel.

**Es wird nie etwas gelöscht.** Was du aussortierst, wandert in den Ordner `_Aussortiert`
(brauchbare Dokumente in `_Dokumente`), beide liegen direkt im Fotoordner. Über den Reiter
„Aussortiert“ holst du alles mit einem Klick zurück. Den Ordner `_Aussortiert` leerst du
erst selbst, wenn du dir sicher bist.

---

## Einmalig: Einrichten

### Schritt 1 – Python installieren
Python ist ein kostenloses Programm, das der Fotoaufräumer zum Laufen braucht.

1. Unten in der Taskleiste auf **Start** klicken und **Microsoft Store** öffnen.
2. Nach **Python 3.12** suchen (Herausgeber: Python Software Foundation) und auf **Herunterladen** klicken.
3. Fertig. Danach musst du nichts weiter tun.

### Schritt 2 – Den Fotoaufräumer herunterladen
1. Auf GitHub dieses Repository öffnen.
2. Auf den grünen Knopf **Code** klicken und dann auf **Download ZIP**.
3. Die ZIP-Datei im Download-Ordner mit der rechten Maustaste anklicken → **Alle extrahieren…** → **Extrahieren**.
   Der entstandene Ordner ist dein Fotoaufräumer. Du kannst ihn verschieben, wohin du magst.

---

## Aufräumen

1. Im Fotoaufräumer-Ordner doppelt auf **Starten.bat** klicken.
   - Falls Windows „Der Computer wurde durch Windows geschützt“ meldet: auf **Weitere Informationen** und dann **Trotzdem ausführen** klicken.
   - Beim allerersten Start richtet er sich ein paar Minuten lang ein.
2. Es öffnet sich ein Fenster: **den Ordner mit deinen Fotos auswählen**.
3. Jetzt wird analysiert. Das schwarze Fenster zeigt, wie lange es noch dauert. Bei vielen tausend Fotos
   kann das eine Stunde oder länger brauchen – Tee kochen ist erlaubt.
   Beim nächsten Mal geht es schnell, weil nur neue Fotos angeschaut werden.
4. Danach öffnet sich der Browser mit der Übersicht.

### In der Übersicht
- **Klick auf ein Foto** markiert es rot („weg“) oder hebt die Markierung auf.
- **Lupe** (⤢, unten rechts am Foto) zeigt es bildschirmgroß. Klick irgendwohin schließt es wieder.
- **Bildgröße**: Regler oben – so groß, wie du es brauchst, um zu erkennen, was du vor dir hast.
- **Aussortieren** verschiebt die markierten Fotos *dieser Seite* nach `_Aussortiert`.
- **Nach „_Dokumente“** verschiebt sie in den Dokumente-Ordner (für Brauchbares).
- Bei **Unscharf** und **Dokumente?** gibt es einen Regler **Grenze**: Damit stellst du ein, wie streng gesucht wird.

Zum Beenden einfach das schwarze Fenster schließen. Du kannst jederzeit weitermachen, wo du aufgehört hast.

---

## Welche Ordner vom Handy?
Der Kamera-Ordner (`DCIM › Camera`) enthält nur, was die Kamera selbst aufgenommen hat. Auf einem
Samsung-Handy liegen die anderen Bilder woanders:
- WhatsApp: `Android › media › com.whatsapp › WhatsApp › Media › WhatsApp Images`
- Screenshots: `DCIM › Screenshots` oder `Pictures › Screenshots`
- Heruntergeladenes: `Download`

Einfach alle in denselben Fotoordner auf dem Laptop kopieren und den Fotoaufräumer neu starten.
Bereits angeschaute Fotos werden nicht noch einmal analysiert.

## Gut zu wissen
- Das Land kommt aus den Standortdaten, die die Kamera ins Foto schreibt. Fotos ohne diese Daten
  (z. B. WhatsApp-Bilder, bei denen WhatsApp sie entfernt) stehen unter „ohne Ort“.
  Ortsdaten: [GeoNames](https://www.geonames.org/), Lizenz CC BY 4.0.
- Der Fotoaufräumer arbeitet nur auf deinem Laptop. Die Fotos gehen nirgendwo hin, auch nicht ins Internet.
- Was du auf dem Laptop aufräumst, ändert nichts am Handy und nichts an Google Fotos.
- Im Fotoordner entsteht ein Ordner `_Fotoaufraeumer-Daten` mit Vorschaubildern und den Analyse-Ergebnissen.
  Den kannst du löschen, wenn du fertig bist. Beim nächsten Start wird dann neu analysiert.
- Wenn alles noch einmal ganz von vorn analysiert werden soll: in der Eingabeaufforderung
  `Starten.bat --neu` aufrufen.
