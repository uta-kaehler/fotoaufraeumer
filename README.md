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

This project was developed through a human-led, AI-assisted workflow across multiple environments.

The project lead defined the user problem, set the safety constraints and acceptance criteria, assigned tasks according to the provisional strengths of different AI systems, tested successive versions in real use, and directed further iteration through concrete feedback.

AI systems supported different parts of the process: orientation in unfamiliar technical environments, implementation, debugging, documentation and refinement. The work was coordinated through a shared project goal rather than treated as a sequence of isolated prompts.

Coordination did not mean delegating a finished specification. It meant keeping the project coherent across systems and platforms: deciding what needed clarification, which system was best placed to support a particular step, testing whether the implementation matched the intended use, and translating observations from use into the next development decision.

| Participant | Contribution |
| --- | --- |
| **Project lead** | Defined the problem, requirements, safety constraints and acceptance criteria; tested releases with a personal photo library of approximately 5,000 images; evaluated behaviour in context and directed iteration |
| **Gemini** (Google) | Supported orientation in unfamiliar platform workflows |
| **Claude Code** (Anthropic) | Supported implementation, debugging, documentation and iterative refinement |

The project lead writes no code. This project demonstrates a different competence: directing multiple AI systems toward a coherent goal — specifying what a tool should and should not do, evaluating its behaviour in context, and making informed decisions about each next iteration. This is process responsibility in AI-assisted development, not software development, and the two are not the same.

## From requirements to use

There were no formal specification documents or user stories. Requirements emerged in ordinary language from the practical problem, including sentences such as:

> *“Whenever I want to delete something, it's just too small — you can't even tell what you're deleting. So I always end up leaving it, frustrated.”*  
> (“…das ist einfach zu klein, man erkennt gar nicht, was man löscht. Deswegen lasse ich es dann immer gefrustet.”)

That sentence determined two central design decisions: show images large, and never delete them directly—only move them.

Acceptance meant real use. Test observations from the first evening—for example, “it says 197 duplicates, but they don't show up,” a screenshot of a crash, and “the WhatsApp stuff isn't shown at all”—each led to concrete fixes. A further observation, that sorting by year, month and place would be useful, became a feature in the next iteration.

This repository therefore documents both a working tool and a practical development process: a real-world problem translated into requirements, implemented with AI assistance, and improved through human-led testing and iteration.

The [Werkstattbericht](WERKSTATTBERICHT.md) (workshop report, in German with an English summary) records the process: original requirement statements, issues surfaced in testing, and the changes they prompted.

## Under the hood

Python with Pillow, pillow-heif, ImageHash and NumPy; everything else uses the standard library. `fotoaufraeumer.py` analyses the selected folder in a process pool and stores results in SQLite.

- **Duplicates:** Identical files are detected using SHA-1; visually similar re-saved images and burst shots are detected using perceptual hashes. Screenshots and document photos count as duplicates only when files are identical, so different pages of a letter are not merged.
- **Sharpness:** Blur is estimated through the variance of the Laplacian, calculated per tile. The second-sharpest tile is used, so a portrait with a soft background can still count as sharp.
- **Documents:** A small heuristic uses low saturation, brightness and fine edges.

The tool serves `oberflaeche.html` locally and opens it in the browser. Large previews are generated in the background so the interface remains responsive. `Starten.bat` sets up a virtual environment on the first run.

## Data and licences

- Code: MIT licence; see [LICENSE](LICENSE).
- `orte.csv.gz` and `laender.json`: places with more than 1,000 inhabitants from [GeoNames](https://www.geonames.org/), licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
