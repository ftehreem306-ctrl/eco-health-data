# Eco-Health Action Hub

An educational website about fine particulate air pollution (PM2.5) and health in Pakistan, by Tehreem Fatima (BS Medical Laboratory Technology, final year, NUMS).

**Website:** https://ftehreem306-ctrl.github.io/eco-health-data/

## What this repository contains

| Part | File(s) |
|---|---|
| A referenced white paper on PM2.5 and health, with a focus on Pakistan | `whitepaper.md` |
| A single-page website: recent PM2.5 readings for 15 locations, a household "daily defence playbook", and the references | `index.html` |
| A Python script that downloads PM2.5 data from the OpenAQ API (v3) | `scripts/fetch_pm25.py` |
| A GitHub Actions workflow that runs the script once a day and commits the result | `.github/workflows/update-pm25.yml` |
| A workflow, run by hand, that lists all OpenAQ PM2.5 locations in Pakistan | `.github/workflows/discover-locations.yml` |
| The chosen locations and the AQI scale used for categories | `config/locations.json`, `config/aqi_scale.json` |
| The data the website reads, and the list of candidate locations | `data/pm25.json`, `data/candidates.json` |
| Setup instructions | `DATA_SETUP.md` |

## How the data are produced

For each location, the script averages the hourly PM2.5 values from the previous 24 hours. It then assigns a category using the US EPA Air Quality Index breakpoints for 24-hour PM2.5, as revised in 2024.

The project applies three rules of its own:

- a value is shown only if at least 18 of the 24 hourly values exist
- the average is truncated to one decimal place
- data more than 24 hours old are shown as "no recent data"

All 15 locations are AirGradient sensors listed on OpenAQ. Their accuracy has not been checked against reference instruments.

## What this project does not do

- It does not measure health outcomes at any location.
- It does not forecast air quality.
- It does not give medical advice.

## Licences

- **Code:** MIT License (see `LICENSE`).
- **Text** (white paper and website wording): CC BY 4.0.
- **Air quality data:** these belong to their providers and are used under each provider's licence, which is shown on the website. They are accessed through OpenAQ.

## Use of AI

AI tools helped with the literature search, drafting and code. The author checked every reference.

## Corrections

Please open an issue in this repository.
