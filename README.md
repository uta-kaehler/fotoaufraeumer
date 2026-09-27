# Fotoaufräumer

*German for “photo tidier”.* **An everyday photo-cleanup tool, developed through a human-led, AI-assisted workflow.**

A small Windows tool for people who have thousands of photos on their phone and never delete any, because on a phone screen it is too hard to see what they might throw away by mistake. It finds duplicates, blurry shots, photos of documents, screenshots and WhatsApp images, and shows them **large, side by side, in the browser**.

Nothing is ever deleted: sorted-out photos move to a folder called `_Aussortiert` and can be restored with one click.

The interface and manual are in German ([ANLEITUNG.md](ANLEITUNG.md)). It was built for real use in a real household, not as a demo.

## What it does

| Tab | What you see |
| --- | --- |
| Stöbern (Browse) | All photos by year, month and country; country is derived offline from the camera’s GPS data |
| Doppelte (Duplicates) | Exact and near duplicates, including burst shots, with the best candidate marked ★ |
| Unscharf (Blurry) | Blurry photos, blurriest first, with an adjustable threshold |
| Dokumente? (Documents?) | Photos that appear to show paper, receipts or printed text |
| Screenshots, WhatsApp | Separate groups, recognised by file name and folder |
| Aussortiert (Sorted out) | Everything moved aside for review, restorable at any time |

- Runs entirely on the laptop: no photo leaves the device, no account and no cloud required.
- Reads HEIC, JPEG and PNG.
- Remembers previous analysis, so later runs look only at newly added photos.

## How it was developed

This project was developed collaboratively: by one person who writes no code, working with several AI systems across different environments.

The way of working was a conversation, not a hand-off. Uta Kähler described what she needed and what the tool must never do. Claude proposed how it could work and contributed ideas of its own. She listened, asked back, chose what to adopt, and tested each version in real use. What she observed in use became the next step.

Final responsibility stayed with her. That includes the questions nobody raises automatically: what a tool may do with private photos, what data protection requires, what happens if something goes wrong. AI systems often think along on such points, and she asks them to. Keeping these questions in view, and answering for the result, remains the responsibility of the person whose name is on the project.

| Participant | Contribution |
| --- | --- |
| **Uta Kähler** (final responsibility) | Described the problem and what the tool must never do; weighed the proposals and decided what to adopt; kept overarching questions such as data protection in view; tested each version with about 5,000 of her own photos; decided what counted as done |
| **Gemini** (Google) | Supported orientation in unfamiliar platform workflows (setting up GitHub) |
| **Claude Code** (Anthropic) | Proposed solutions and ideas; implementation, debugging, documentation and iterative refinement |

Uta Kähler writes no code. What this project shows is a different competence: describing clearly what is needed, engaging with what AI systems propose, deciding what to take on, noticing in use what needs adjusting, and carrying final responsibility for the result. This is responsibility for the process in AI-assisted development, not software development, and the two are not the same.

## From requirements to use

There were no formal specification documents or user stories. Requirements emerged in ordinary language from the practical problem, including sentences such as:

> *“Whenever I want to delete something, it's just too small — you can't even tell what you're deleting. So I always end up leaving it, frustrated.”*  
> (“…das ist einfach zu klein, man erkennt gar nicht, was man löscht. Deswegen lasse ich es dann immer gefrustet.”)

From that sentence came the two central design decisions, proposed by Claude and adopted by her: show images large, and never delete them directly—only move them.

Acceptance meant real use. Observations from the first evening—for example, “it says 197 duplicates, but they don't show up,” a screenshot of a crash, and “the WhatsApp stuff isn't shown at all”—each led to a concrete adjustment. A further remark, that sorting by year, month and place would be useful, became a feature in the next iteration. The whole session took about one hour.

This repository therefore documents both a working tool and a practical way of working: a real-world problem put into words, developed in conversation with AI systems, and adjusted step by step through real use.

The [Werkstattbericht](WERKSTATTBERICHT.md) (workshop report, in German with an English summary) records the process: the original requirement statements, what testing brought to light, and the adjustments that followed.

## Under the hood

Python with Pillow, pillow-heif, ImageHash and NumPy; everything else uses the standard library. `fotoaufraeumer.py` analyses the selected folder in a process pool and stores results in SQLite.

- **Duplicates:** Identical files are detected using SHA-1; visually similar re-saved images and burst shots are detected using perceptual hashes. Screenshots and document photos count as duplicates only when files are identical, so different pages of a letter are not merged.
- **Sharpness:** Blur is estimated through the variance of the Laplacian, calculated per tile. The second-sharpest tile is used, so a portrait with a soft background can still count as sharp.
- **Documents:** A small heuristic uses low saturation, brightness and fine edges.

The tool serves `oberflaeche.html` locally and opens it in the browser. Large previews are generated in the background so the interface remains responsive. `Starten.bat` sets up a virtual environment on the first run.

## Data and licences

- Code: MIT licence; see [LICENSE](LICENSE).
- `orte.csv.gz` and `laender.json`: places with more than 1,000 inhabitants from [GeoNames](https://www.geonames.org/), licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
