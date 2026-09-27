"""Fotoaufräumer – findet doppelte, unscharfe und Dokument-Fotos und zeigt sie groß im Browser.

Grundsatz: Es wird nie etwas gelöscht. Aussortiertes wandert in den Ordner
"_Aussortiert" innerhalb des Fotoordners und kann jederzeit zurückgeholt werden.

Aufruf:  python fotoaufraeumer.py [FOTOORDNER] [--neu]
Ohne FOTOORDNER öffnet sich ein Auswahlfenster.
"""

import argparse
import csv
import gzip
import hashlib
import io
import json
import os
import re
import shutil
import sqlite3
import struct
import sys
import threading
import time
import webbrowser
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import imagehash
import numpy as np
from PIL import Image, ImageOps

try:
    import pillow_heif

    pillow_heif.register_heif_opener()
except ImportError:  # HEIC-Fotos werden dann übersprungen
    pillow_heif = None

BILD_ENDUNGEN = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp"}
DATEN_ORDNER = "_Fotoaufraeumer-Daten"
AUSSORTIERT = "_Aussortiert"
DOKUMENTE = "_Dokumente"
EIGENE_ORDNER = {DATEN_ORDNER, AUSSORTIERT, DOKUMENTE}

# Wie ähnlich zwei Fotos sein müssen (0 = identisch, 64 = völlig verschieden)
AEHNLICH_GRENZE = 8
# Fotos, die weiter als so viele Sekunden auseinanderliegen, gelten nie als Serie
SERIEN_FENSTER_SEK = 120
PORT = 8765

OBERFLAECHE = Path(__file__).with_name("oberflaeche.html")
ORTE = Path(__file__).with_name("orte.csv.gz")        # Orte ab 1000 Einwohnern, Daten: GeoNames (CC BY 4.0)
LAENDER = Path(__file__).with_name("laender.json")   # Ländercode -> deutscher Name


# ---------------------------------------------------------------- Analyse


def aufnahmezeit(bild, pfad):
    """Aufnahmedatum aus den Kameradaten, sonst Änderungsdatum der Datei."""
    try:
        exif = bild.getexif()
        roh = exif.get_ifd(0x8769).get(36867) or exif.get(306)
        if roh:
            return datetime.strptime(str(roh).strip()[:19], "%Y:%m:%d %H:%M:%S").timestamp(), True
    except Exception:
        pass
    return os.path.getmtime(pfad), False


def kamera(bild):
    try:
        exif = bild.getexif()
        return f"{exif.get(271, '')} {exif.get(272, '')}".strip()
    except Exception:
        return ""


def schaerfe(grau):
    """Schärfe als Varianz des Laplace-Filters, pro Kachel berechnet.

    Genommen wird die schärfste Kachel: Ein Porträt mit unscharfem Hintergrund
    zählt so trotzdem als scharf, solange das Gesicht scharf ist.
    """
    a = np.asarray(grau, dtype=np.float32)
    lap = a[1:-1, 1:-1] * -4 + a[:-2, 1:-1] + a[2:, 1:-1] + a[1:-1, :-2] + a[1:-1, 2:]
    h, w = lap.shape
    werte = []
    for y in range(4):
        for x in range(4):
            kachel = lap[y * h // 4:(y + 1) * h // 4, x * w // 4:(x + 1) * w // 4]
            if kachel.size:
                werte.append(float(kachel.var()))
    werte.sort()
    # zweitschärfste Kachel, damit ein einzelner Glanzpunkt nicht alles rettet
    return werte[-2] if len(werte) > 1 else (werte[0] if werte else 0.0)


def dokument_wert(bild_klein):
    """0..1 – wie sehr das Foto nach Papier mit Schrift aussieht (hell, farblos, viele feine Kanten)."""
    hsv = np.asarray(bild_klein.convert("HSV"), dtype=np.float32) / 255.0
    saettigung = hsv[..., 1].mean()
    hell = (hsv[..., 2] > 0.6).mean()
    grau = np.asarray(bild_klein.convert("L"), dtype=np.float32)
    kanten = (np.abs(np.diff(grau, axis=1)) > 40).mean()
    wert = 0.0
    wert += max(0.0, 1 - saettigung / 0.18) * 0.4
    wert += min(1.0, hell / 0.55) * 0.35
    wert += min(1.0, kanten / 0.06) * 0.25
    return round(float(wert), 3)


def art_nach_name(pfad):
    name = pfad.name.lower()
    teile = [t.lower() for t in pfad.parts]
    if "screenshot" in name or any("screenshot" in t for t in teile):
        return "screenshot"
    if re.match(r"(img|vid)-\d{8}-wa\d+", name) or any("whatsapp" in t for t in teile):
        return "whatsapp"
    return ""


def analysiere_datei(pfad_str):
    pfad = Path(pfad_str)
    try:
        daten = pfad.read_bytes()
        sha = hashlib.sha1(daten).hexdigest()
        bild = Image.open(io.BytesIO(daten))
        zeit, zeit_aus_kamera = aufnahmezeit(bild, pfad)
        modell = kamera(bild)
        if bild.format == "JPEG":
            bild.draft("RGB", (1024, 1024))  # schnelles verkleinertes Laden
        bild = ImageOps.exif_transpose(bild).convert("RGB")
        breite, hoehe = Image.open(io.BytesIO(daten)).size
        bild.thumbnail((800, 800))
        grau = bild.convert("L")
        klein = bild.copy()
        klein.thumbnail((256, 256))
        return {
            "pfad": pfad_str,
            "groesse": len(daten),
            "mtime": os.path.getmtime(pfad),
            "sha": sha,
            "phash": str(imagehash.phash(bild)),
            "zeit": zeit,
            "zeit_kamera": int(zeit_aus_kamera),
            "breite": breite,
            "hoehe": hoehe,
            "kamera": modell,
            "schaerfe": round(float(schaerfe(grau)), 1),
            "dokument": dokument_wert(klein),
            "art": art_nach_name(pfad),
            "fehler": "",
            "gps_geprueft": 0,
        }
    except Exception as e:
        return {"pfad": pfad_str, "fehler": f"{type(e).__name__}: {e}"}


def db_oeffnen(wurzel):
    ordner = wurzel / DATEN_ORDNER
    ordner.mkdir(exist_ok=True)
    (ordner / "vorschau").mkdir(exist_ok=True)
    db = sqlite3.connect(ordner / "analyse.sqlite", check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS foto (
            id INTEGER PRIMARY KEY, pfad TEXT UNIQUE, groesse INT, mtime REAL, sha TEXT,
            phash TEXT, zeit REAL, zeit_kamera INT, breite INT, hoehe INT, kamera TEXT,
            schaerfe REAL, dokument REAL, art TEXT, fehler TEXT,
            gruppe INT, empfohlen INT DEFAULT 0,
            ort TEXT DEFAULT ''   -- '' = an Ort und Stelle, sonst 'aussortiert' / 'dokumente'
        );
        """
    )
    vorhandene = {z[1] for z in db.execute("PRAGMA table_info(foto)")}
    for spalte, typ in (("lat", "REAL"), ("lon", "REAL"), ("stadt", "TEXT"), ("region", "TEXT"),
                        ("land", "TEXT"), ("gps_geprueft", "INT DEFAULT 0")):
        if spalte not in vorhandene:
            db.execute(f"ALTER TABLE foto ADD COLUMN {spalte} {typ}")
    zahlen_reparieren(db)
    return db


def zahlen_reparieren(db):
    """Frühere Versionen konnten Zahlen als rohe Bytes speichern (numpy-float32 unter Windows).

    Die werden hier zurückverwandelt, damit eine vorhandene Analyse weiterverwendbar bleibt.
    """
    for spalte in ("schaerfe", "dokument"):
        for zeile in db.execute(f"SELECT id, {spalte} FROM foto WHERE typeof({spalte}) = 'blob'").fetchall():
            roh = bytes(zeile[1])
            format_ = {4: "<f", 8: "<d"}.get(len(roh))
            wert = round(struct.unpack(format_, roh)[0], 3) if format_ else 0.0
            db.execute(f"UPDATE foto SET {spalte} = ? WHERE id = ?", (wert, zeile[0]))
    db.commit()


def fotos_finden(wurzel):
    for ordner, unterordner, dateien in os.walk(wurzel):
        unterordner[:] = [u for u in unterordner if u not in EIGENE_ORDNER]
        for d in dateien:
            if Path(d).suffix.lower() in BILD_ENDUNGEN:
                yield Path(ordner) / d


def analysieren(wurzel, db, neu=False):
    if neu:
        db.execute("DELETE FROM foto WHERE ort = ''")
    bekannt = {r["pfad"]: (r["groesse"], r["mtime"]) for r in db.execute("SELECT pfad, groesse, mtime FROM foto")}
    offen = []
    alle = []
    for p in fotos_finden(wurzel):
        rel = str(p.relative_to(wurzel))
        alle.append(rel)
        st = p.stat()
        if bekannt.get(rel) != (st.st_size, st.st_mtime):
            offen.append(rel)

    # Fotos, die es nicht mehr gibt (und die wir nicht selbst verschoben haben), vergessen
    vorhanden = set(alle)
    for pfad in bekannt:
        if pfad not in vorhanden:
            db.execute("DELETE FROM foto WHERE pfad = ? AND ort = ''", (pfad,))

    print(f"{len(alle)} Fotos gefunden, davon {len(offen)} neu zu analysieren.")
    if offen:
        start = time.time()
        felder = ["pfad", "groesse", "mtime", "sha", "phash", "zeit", "zeit_kamera", "breite", "hoehe",
                  "kamera", "schaerfe", "dokument", "art", "fehler", "gps_geprueft"]
        fehler = 0
        with ProcessPoolExecutor() as pool:
            for i, erg in enumerate(pool.map(analysiere_datei, [str(wurzel / r) for r in offen], chunksize=16), 1):
                erg["pfad"] = str(Path(erg["pfad"]).relative_to(wurzel))
                if erg["fehler"]:
                    fehler += 1
                    st = (wurzel / erg["pfad"]).stat()
                    erg.update(groesse=st.st_size, mtime=st.st_mtime)
                werte = [erg.get(f) for f in felder]
                db.execute(
                    f"INSERT INTO foto ({','.join(felder)}) VALUES ({','.join('?' * len(felder))}) "
                    f"ON CONFLICT(pfad) DO UPDATE SET {','.join(f'{f}=excluded.{f}' for f in felder[1:])}",
                    werte,
                )
                if i % 100 == 0 or i == len(offen):
                    db.commit()
                    dauer = time.time() - start
                    rest = dauer / i * (len(offen) - i)
                    print(f"\r  {i}/{len(offen)} analysiert – noch etwa {rest / 60:.0f} Min.   ", end="", flush=True)
        print()
        if fehler:
            print(f"  {fehler} Dateien ließen sich nicht öffnen (stehen im Reiter 'Probleme').")
    gruppieren(db)
    db.commit()
    orte_bestimmen(wurzel, db)


# ---------------------------------------------------------------- Orte


def gps_lesen(pfad_str):
    """Breiten- und Längengrad aus den Kameradaten, ohne das Bild selbst zu laden."""
    try:
        gps = Image.open(pfad_str).getexif().get_ifd(0x8825)

        def grad(werte, richtung):
            g, m, s = (float(w) for w in werte)
            wert = g + m / 60 + s / 3600
            return -wert if richtung in ("S", "W") else wert

        lat, lon = grad(gps[2], gps.get(1, "N")), grad(gps[4], gps.get(3, "E"))
        if abs(lat) < 0.001 and abs(lon) < 0.001:  # 0/0 heißt bei manchen Handys "kein Empfang"
            return None
        return lat, lon
    except Exception:
        return None


class Ortsverzeichnis:
    def __init__(self):
        with gzip.open(ORTE, "rt", encoding="utf-8") as f:
            zeilen = list(csv.reader(f))[1:]
        self.lat = np.array([float(z[0]) for z in zeilen])
        self.lon = np.array([float(z[1]) for z in zeilen])
        self.namen = [(z[2], z[3], z[4]) for z in zeilen]
        self.laender = json.loads(LAENDER.read_text(encoding="utf-8"))

    def naechster(self, lat, lon):
        dx = (self.lon - lon) * np.cos(np.radians(lat))
        dx = np.minimum(np.abs(dx), 360 * np.cos(np.radians(lat)) - np.abs(dx))  # über die Datumsgrenze
        stadt, region, code = self.namen[int(np.argmin(dx * dx + (self.lat - lat) ** 2))]
        return stadt, region, self.laender.get(code, code)


def orte_bestimmen(wurzel, db):
    offen = db.execute("SELECT id, pfad, ort FROM foto WHERE fehler = '' AND gps_geprueft = 0").fetchall()
    if not offen:
        return
    print(f"Aufnahmeorte werden gelesen ({len(offen)} Fotos) ...")
    verzeichnis = Ortsverzeichnis()
    with ProcessPoolExecutor() as pool:
        ergebnisse = pool.map(gps_lesen, [str(aktueller_pfad(wurzel, z)) for z in offen], chunksize=32)
        for zeile, gps in zip(offen, ergebnisse):
            if gps:
                stadt, region, land = verzeichnis.naechster(*gps)
                db.execute("UPDATE foto SET lat = ?, lon = ?, stadt = ?, region = ?, land = ?, gps_geprueft = 1 "
                           "WHERE id = ?", (gps[0], gps[1], stadt, region, land, zeile["id"]))
            else:
                db.execute("UPDATE foto SET lat = NULL, lon = NULL, stadt = NULL, region = NULL, land = NULL, "
                           "gps_geprueft = 1 WHERE id = ?", (zeile["id"],))
    db.commit()
    mit_ort = db.execute("SELECT COUNT(*) FROM foto WHERE land IS NOT NULL").fetchone()[0]
    print(f"  {mit_ort} Fotos haben einen Aufnahmeort.")


class Gruppen:
    """Union-Find: fasst Fotos zu Gruppen von Doppelten zusammen."""

    def __init__(self):
        self.eltern = {}

    def finde(self, a):
        self.eltern.setdefault(a, a)
        while self.eltern[a] != a:
            self.eltern[a] = self.eltern[self.eltern[a]]
            a = self.eltern[a]
        return a

    def verbinde(self, a, b):
        self.eltern[self.finde(a)] = self.finde(b)


def gruppieren(db):
    fotos = db.execute(
        "SELECT id, sha, phash, zeit, schaerfe, dokument, art, breite, hoehe, pfad FROM foto WHERE fehler = '' AND ort = ''"
    ).fetchall()

    def nur_exakt(f):
        # Textseiten und Bildschirmfotos sehen für den Ähnlichkeitsvergleich alle gleich aus.
        # Damit nicht Seite 1 und Seite 2 eines Briefs als "doppelt" gelten, zählt bei ihnen
        # nur die exakt gleiche Datei.
        return f["art"] == "screenshot" or f["dokument"] >= 0.6

    g = Gruppen()
    nach_sha, nach_phash = {}, {}
    for f in fotos:
        # 1. exakt gleiche Dateien und 2. gleiches Bild (z. B. per WhatsApp neu gespeichert)
        paare = [(nach_sha, f["sha"])] + ([] if nur_exakt(f) else [(nach_phash, f["phash"])])
        for tabelle, schluessel in paare:
            if schluessel in tabelle:
                g.verbinde(f["id"], tabelle[schluessel])
            else:
                tabelle[schluessel] = f["id"]
    # 3. Serienbilder: sehr ähnlich und kurz nacheinander aufgenommen
    nach_zeit = sorted((f for f in fotos if not nur_exakt(f)), key=lambda f: f["zeit"])
    hashes = {f["id"]: imagehash.hex_to_hash(f["phash"]) for f in nach_zeit}
    for i, f in enumerate(nach_zeit):
        for j in range(i + 1, len(nach_zeit)):
            anderes = nach_zeit[j]
            if anderes["zeit"] - f["zeit"] > SERIEN_FENSTER_SEK:
                break
            if hashes[f["id"]] - hashes[anderes["id"]] <= AEHNLICH_GRENZE:
                g.verbinde(f["id"], anderes["id"])

    mitglieder = {}
    for f in fotos:
        mitglieder.setdefault(g.finde(f["id"]), []).append(f)
    db.execute("UPDATE foto SET gruppe = NULL, empfohlen = 0")
    for liste in mitglieder.values():
        if len(liste) < 2:
            continue
        # Empfehlung: das schärfste in der höchsten Auflösung, bei Gleichstand der kürzeste Pfad
        bestes = max(liste, key=lambda f: (f["breite"] * f["hoehe"] >= 0.8 * max(x["breite"] * x["hoehe"] for x in liste),
                                           f["schaerfe"], -len(f["pfad"])))
        for f in liste:
            db.execute("UPDATE foto SET gruppe = ?, empfohlen = ? WHERE id = ?",
                       (bestes["id"], int(f["id"] == bestes["id"]), f["id"]))


# ---------------------------------------------------------------- Browser-Oberfläche


def vorschau_pfad(wurzel, foto_id, groesse):
    return wurzel / DATEN_ORDNER / "vorschau" / f"{foto_id}_{groesse}.jpg"


def vorschau_erzeugen(quelle, ziel, groesse):
    """Verkleinerte Kopie speichern. Läuft auch in eigenen Prozessen, daher nur Pfade als Argumente."""
    try:
        bild = Image.open(quelle)
        if bild.format == "JPEG":
            bild.draft("RGB", (groesse, groesse))
        bild = ImageOps.exif_transpose(bild).convert("RGB")
        bild.thumbnail((groesse, groesse))
        zwischen = Path(f"{ziel}.{os.getpid()}.{threading.get_ident()}.tmp")
        bild.save(zwischen, "JPEG", quality=82)
        os.replace(zwischen, ziel)
        return True
    except Exception:
        return False


def vorschau(wurzel, db, sperre, foto_id, groesse):
    groesse = 1600 if groesse > 600 else 600
    ziel = vorschau_pfad(wurzel, foto_id, groesse)
    if not ziel.exists():
        with sperre:
            zeile = db.execute("SELECT pfad, ort FROM foto WHERE id = ?", (foto_id,)).fetchone()
        if not zeile:
            return None
        # Das Verkleinern (bei großen HEIC-Fotos eine Sekunde und mehr) läuft ohne Sperre,
        # damit die Oberfläche währenddessen weiter antwortet.
        if not vorschau_erzeugen(str(aktueller_pfad(wurzel, zeile)), str(ziel), groesse):
            return None
    return ziel.read_bytes()


def vorschauen_vorbereiten(wurzel, db, sperre):
    """Im Hintergrund alle kleinen Vorschaubilder erzeugen – die Doppelten zuerst."""
    with sperre:
        zeilen = db.execute(
            "SELECT id, pfad, ort FROM foto WHERE fehler = '' "
            "ORDER BY gruppe IS NULL, art = '', schaerfe"
        ).fetchall()
    auftraege = [(str(aktueller_pfad(wurzel, z)), str(vorschau_pfad(wurzel, z["id"], 600)))
                 for z in zeilen if not vorschau_pfad(wurzel, z["id"], 600).exists()]
    if not auftraege:
        return
    print(f"Vorschaubilder werden im Hintergrund vorbereitet ({len(auftraege)} Stück) – "
          "du kannst trotzdem schon loslegen.")
    with ProcessPoolExecutor() as pool:
        for i, _ in enumerate(pool.map(vorschau_erzeugen, *zip(*auftraege), [600] * len(auftraege), chunksize=4), 1):
            if i % 50 == 0 or i == len(auftraege):
                print(f"\r  {i}/{len(auftraege)} Vorschaubilder fertig   ", end="", flush=True)
    print()


def aktueller_pfad(wurzel, zeile):
    ordner = {"": wurzel, "aussortiert": wurzel / AUSSORTIERT, "dokumente": wurzel / DOKUMENTE}[zeile["ort"]]
    return ordner / zeile["pfad"]


def verschieben(wurzel, db, ids, nach):
    """nach: 'aussortiert', 'dokumente' oder '' (zurück an den Ursprungsort)."""
    erledigt, probleme = 0, []
    for foto_id in ids:
        zeile = db.execute("SELECT id, pfad, ort FROM foto WHERE id = ?", (foto_id,)).fetchone()
        if not zeile or zeile["ort"] == nach:
            continue
        von = aktueller_pfad(wurzel, zeile)
        zu = aktueller_pfad(wurzel, {"pfad": zeile["pfad"], "ort": nach})
        if zu.exists():
            probleme.append(f"{zeile['pfad']}: am Ziel liegt schon eine Datei mit diesem Namen")
            continue
        try:
            zu.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(von), str(zu))
        except OSError as e:
            probleme.append(f"{zeile['pfad']}: {e}")
            continue
        db.execute("UPDATE foto SET ort = ? WHERE id = ?", (nach, foto_id))
        erledigt += 1
    db.commit()
    return {"erledigt": erledigt, "probleme": probleme}


JAHR = "strftime('%Y', zeit, 'unixepoch', 'localtime')"
MONAT = "CAST(strftime('%m', zeit, 'unixepoch', 'localtime') AS INT)"


def stoebern_filter(q):
    bedingungen, args = ["fehler = ''", "ort = ''"], []
    if q.get("jahr"):
        bedingungen.append(f"{JAHR} = ?")
        args.append(q["jahr"])
    if q.get("monat"):
        bedingungen.append(f"{MONAT} = ?")
        args.append(int(q["monat"]))
    if q.get("land") == "-":
        bedingungen.append("land IS NULL")
    elif q.get("land"):
        bedingungen.append("land = ?")
        args.append(q["land"])
    return " AND ".join(bedingungen), args


def uebersicht(db, q):
    """Wie viele Fotos es pro Jahr, Monat und Land gibt – jeweils passend zu den anderen Filtern."""
    def zaehle(ausdruck, ohne):
        filter_, args = stoebern_filter({k: v for k, v in q.items() if k != ohne})
        return [list(z) for z in db.execute(
            f"SELECT {ausdruck} AS k, COUNT(*) FROM foto WHERE {filter_} GROUP BY k ORDER BY k", args)]
    return {
        "jahre": zaehle(JAHR, "jahr"),
        "monate": zaehle(MONAT, "monat") if q.get("jahr") else [],
        "laender": sorted(zaehle("land", "land"), key=lambda z: (z[0] is None, -z[1])),
    }


def liste(db, reiter, schwelle, q=None):
    basis = ("SELECT id, pfad, groesse, zeit, breite, hoehe, schaerfe, dokument, art, gruppe, empfohlen, ort, fehler, "
             "stadt, region, land FROM foto ")
    if reiter == "stoebern":
        filter_, args = stoebern_filter(q or {})
        sql = basis + f"WHERE {filter_} ORDER BY zeit"
    elif reiter == "doppelt":
        sql = basis + "WHERE gruppe IS NOT NULL AND ort = '' ORDER BY (SELECT MIN(zeit) FROM foto g WHERE g.gruppe = foto.gruppe), gruppe, empfohlen DESC, zeit"
        args = ()
    elif reiter == "unscharf":
        sql = basis + "WHERE fehler = '' AND ort = '' AND art = '' AND schaerfe < ? ORDER BY schaerfe"
        args = (schwelle,)
    elif reiter == "dokumente":
        sql = basis + "WHERE fehler = '' AND ort = '' AND art = '' AND dokument >= ? ORDER BY dokument DESC"
        args = (schwelle,)
    elif reiter in ("screenshot", "whatsapp"):
        sql = basis + "WHERE ort = '' AND art = ? ORDER BY zeit DESC"
        args = (reiter,)
    elif reiter == "aussortiert":
        sql = basis + "WHERE ort != '' ORDER BY ort, zeit DESC"
        args = ()
    elif reiter == "probleme":
        sql = basis + "WHERE fehler != '' ORDER BY pfad"
        args = ()
    else:
        return []
    return [dict(r) for r in db.execute(sql, args)]


def zaehlen(db):
    z = lambda sql: db.execute(sql).fetchone()[0]
    return {
        "gesamt": z("SELECT COUNT(*) FROM foto WHERE ort = ''"),
        "doppelt": z("SELECT COUNT(*) FROM foto WHERE gruppe IS NOT NULL AND ort = '' AND empfohlen = 0"),
        "screenshot": z("SELECT COUNT(*) FROM foto WHERE ort = '' AND art = 'screenshot'"),
        "whatsapp": z("SELECT COUNT(*) FROM foto WHERE ort = '' AND art = 'whatsapp'"),
        "aussortiert": z("SELECT COUNT(*) FROM foto WHERE ort != ''"),
        "probleme": z("SELECT COUNT(*) FROM foto WHERE fehler != ''"),
    }


def server_starten(wurzel, db):
    sperre = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def senden(self, code, inhalt, typ="application/json; charset=utf-8"):
            if isinstance(inhalt, (dict, list)):
                inhalt = json.dumps(inhalt, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", typ)
            self.send_header("Content-Length", str(len(inhalt)))
            self.end_headers()
            self.wfile.write(inhalt)

        def do_GET(self):
            url = urlparse(self.path)
            q = {k: v[0] for k, v in parse_qs(url.query).items()}
            try:
                if url.path == "/":
                    self.senden(200, OBERFLAECHE.read_bytes(), "text/html; charset=utf-8")
                elif url.path == "/api/liste":
                    with sperre:
                        self.senden(200, liste(db, q.get("reiter", ""), float(q.get("schwelle", 0)), q))
                elif url.path == "/api/uebersicht":
                    with sperre:
                        self.senden(200, uebersicht(db, q))
                elif url.path == "/api/zahlen":
                    with sperre:
                        self.senden(200, {**zaehlen(db), "ordner": str(wurzel)})
                elif url.path == "/api/bild":
                    inhalt = vorschau(wurzel, db, sperre, int(q["id"]), int(q.get("g", 600)))
                    if inhalt is None:
                        self.senden(404, {"fehler": "unbekannt"})
                    else:
                        self.send_response(200)
                        self.send_header("Content-Type", "image/jpeg")
                        self.send_header("Cache-Control", "max-age=86400")
                        self.send_header("Content-Length", str(len(inhalt)))
                        self.end_headers()
                        self.wfile.write(inhalt)
                else:
                    self.senden(404, {"fehler": "unbekannt"})
            except Exception as e:
                self.senden(500, {"fehler": str(e)})

        def do_POST(self):
            laenge = int(self.headers.get("Content-Length", 0))
            daten = json.loads(self.rfile.read(laenge) or b"{}")
            if self.path == "/api/verschieben" and daten.get("nach") in ("aussortiert", "dokumente", ""):
                with sperre:
                    self.senden(200, verschieben(wurzel, db, [int(i) for i in daten.get("ids", [])], daten["nach"]))
            else:
                self.senden(404, {"fehler": "unbekannt"})

    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    adresse = f"http://127.0.0.1:{PORT}/"
    print(f"\nDie Oberfläche läuft unter {adresse}")
    print("Zum Beenden dieses Fenster schließen (oder Strg+C drücken).")
    webbrowser.open(adresse)
    threading.Thread(target=vorschauen_vorbereiten, args=(wurzel, db, sperre), daemon=True).start()
    server.serve_forever()


def ordner_waehlen():
    try:
        import tkinter
        from tkinter import filedialog

        fenster = tkinter.Tk()
        fenster.withdraw()
        fenster.attributes("-topmost", True)
        ordner = filedialog.askdirectory(title="Welcher Ordner enthält die Fotos?")
        fenster.destroy()
        return ordner
    except Exception:
        return input("Pfad zum Fotoordner: ").strip().strip('"')


def main():
    parser = argparse.ArgumentParser(description="Fotos aufräumen – ohne etwas zu löschen.")
    parser.add_argument("ordner", nargs="?", help="der Fotoordner")
    parser.add_argument("--neu", action="store_true", help="alles noch einmal von vorn analysieren")
    parser.add_argument("--nur-analyse", action="store_true", help="nur analysieren, keine Oberfläche öffnen")
    args = parser.parse_args()

    ordner = args.ordner or ordner_waehlen()
    if not ordner:
        print("Kein Ordner gewählt.")
        return 1
    wurzel = Path(ordner).resolve()
    if not wurzel.is_dir():
        print(f"Den Ordner {wurzel} gibt es nicht.")
        return 1
    if pillow_heif is None:
        print("Hinweis: pillow-heif fehlt, HEIC-Fotos können nicht gelesen werden.")

    print(f"Fotoordner: {wurzel}")
    db = db_oeffnen(wurzel)
    analysieren(wurzel, db, neu=args.neu)
    z = zaehlen(db)
    print(f"Fertig: {z['doppelt']} überzählige Doppelte, {z['screenshot']} Screenshots, {z['whatsapp']} WhatsApp-Bilder.")
    if not args.nur_analyse:
        server_starten(wurzel, db)
    return 0


if __name__ == "__main__":
    sys.exit(main())
