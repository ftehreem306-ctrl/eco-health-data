# Eco-Health Action Hub: Air, DNA and the Next Generation

A public-awareness initiative founded by Tehreem Fatima (final-year BS Medical Laboratory Technology, NUMS; interests: cancer genetics, epigenetics, translational medicine).

It explains, in plain language and with references, what research shows about PM2.5 air pollution and:

- DNA damage
- epigenetics
- cancer
- pregnancy and the next generation

**Website:** https://ftehreem306-ctrl.github.io/eco-health-data/

## What this repository contains

| Part | File(s) |
|---|---|
| Referenced white paper (64 references), with every finding labelled known, suspected or unknown | `whitepaper.md` |
| Nine-page website: home dashboard, three learning modules (air and cancer, your DNA, mothers and babies), what you can do, air data, vision, about, references | `index.html`, `cancer.html`, `dna.html`, `mothers.html`, `action.html`, `air.html`, `vision.html`, `about.html`, `references.html` |
| Shared design, the script that reads the air data, and the page-section navigation | `assets/css/style.css`, `assets/js/air.js`, `assets/js/nav.js` |
| Python script that downloads PM2.5 data from the OpenAQ API (v3) | `scripts/fetch_pm25.py` |
| Daily GitHub Actions workflow that runs the script and commits the result | `.github/workflows/update-pm25.yml` |
| Manually run workflow that lists all OpenAQ PM2.5 locations in Pakistan | `.github/workflows/discover-locations.yml` |
| Chosen locations and the AQI scale used for categories | `config/locations.json`, `config/aqi_scale.json` |
| Data the website reads, and the list of candidate locations | `data/pm25.json`, `data/candidates.json` |
| Setup guide and audit report | `DATA_SETUP.md`, `AUDIT.md` |

## What this project does not do

- It does not collect biological samples or genetic data.
- It does not measure health outcomes at any location.
- It does not offer diagnostic tests or medical advice.

Genomic and translational research is described only as a future roadmap. That work would happen through ethics-approved partnerships.

## How the air data are produced

For each location, the script averages the hourly PM2.5 values from the previous 24 hours. It then assigns a category using the US EPA Air Quality Index breakpoints for 24-hour PM2.5, as revised in 2024.

The project applies three rules of its own:

- a value is shown only if at least 18 of the 24 hourly values exist
- the average is truncated to one decimal place
- data more than 24 hours old are shown as "no recent data"

All 15 locations are AirGradient sensors listed on OpenAQ. Their accuracy has not been checked against reference instruments.

## Licences

- **Code:** MIT License (see `LICENSE`).
- **Text:** CC BY 4.0.
- **Air-quality data:** these belong to their providers and are used under each provider's licence, which the website shows.

## Use of AI

AI tools assisted with the literature search, drafting and code. The author approved every evidence row and checked every reference.

## Corrections

Please open an issue in this repository.
