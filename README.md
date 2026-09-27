# Fotoaufräumer

**Everyday photo cleanup tool — AI-built, human-led.**

A small Windows tool for people who have thousands of phone photos and never delete any, because on
the phone everything is too small to tell what you are about to throw away. It finds duplicates,
blurry shots, photos of documents, screenshots and WhatsApp images, and shows them **large, side by
side, in the browser**. Nothing is ever deleted: sorted-out photos move to a folder `_Aussortiert`
and can be restored with one click.

The user interface and the guide are in German. The guide is here: **[ANLEITUNG.md](ANLEITUNG.md)**.

## How it was made

The code was written by Claude (Anthropic's model, working in Claude Code) over one night of
conversation. Uta Kähler set the goal, gave the requirements in her own words, tested every version
on her real photo library and decided what counted as done. The
[Werkstattbericht](WERKSTATTBERICHT.md) (German, with an English summary) documents that process:
the original requirement sentences, the problems her tests uncovered, and how each one changed the tool.

## What it does

| Tab | What you see |
| --- | --- |
| Stöbern | all photos by year, month and country (country from the camera's GPS data, resolved offline) |
| Doppelte | exact and near duplicates including burst shots, the best one marked ★ |
| Unscharf | blurry photos, blurriest first, with an adjustable threshold |
| Dokumente? | photos that look like paper, receipts or printed text |
| Screenshots, WhatsApp | their own piles, recognised by file name and folder |
| Aussortiert | everything sorted out, restorable |

- Runs entirely on the laptop: no photo leaves the machine, no account, no cloud.
- Reads HEIC files as well as JPEG and PNG.
- Remembers its analysis, so later runs only look at new photos.

## Under the hood

Python with Pillow, pillow-heif, ImageHash and NumPy; everything else is standard library.
`fotoaufraeumer.py` analyses the folder in a process pool and stores the results in SQLite:

- **Duplicates:** identical files by SHA-1, the same picture re-saved by perceptual hash, burst shots
  by perceptual hash within a short time window. Screenshots and document photos only count as
  duplicates when the file is identical, so page 1 and page 2 of a letter are not merged.
- **Sharpness:** variance of the Laplacian, computed per tile. The second-sharpest tile decides, so a
  portrait with a soft background still counts as sharp.
- **Documents:** a small heuristic from low saturation, brightness and fine edges.

It then serves `oberflaeche.html` on a local port and opens the browser. Large previews are
prepared in the background so the interface stays responsive. `Starten.bat` sets up a virtual
environment on first start.

## Data and licences

- Code: MIT licence, see [LICENSE](LICENSE).
- `orte.csv.gz` and `laender.json`: places with more than 1,000 inhabitants from
  [GeoNames](https://www.geonames.org/), licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
