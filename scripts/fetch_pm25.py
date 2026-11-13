#!/usr/bin/env python3
"""Fetch PM2.5 data for the Eco-Health Action Hub from the OpenAQ API (v3).

Two modes:

  python scripts/fetch_pm25.py --discover
      Lists every OpenAQ location in Pakistan that reports PM2.5 and writes
      data/candidates.json, newest data first, so you can choose locations.

  python scripts/fetch_pm25.py
      Reads config/locations.json and config/aqi_scale.json, and writes
      data/pm25.json for the website.

What the script does for each OpenAQ location:
  1. Reads the location's details (provider, owner, licence, sensors).
  2. Finds its PM2.5 sensor (OpenAQ parameter ID 2).
  3. Downloads the hourly averages for the 24 hours before the run.
  4. If at least MIN_HOURS hourly values exist, averages them and assigns a
     category from the published scale in config/aqi_scale.json.
  5. Otherwise it records "no_recent_data" or "insufficient_data". It never
     copies an older value forward as if it were current.

The API key is read from the environment variable OPENAQ_API_KEY.
It is never written to any file.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

API_BASE = "https://api.openaq.org/v3"
EXPLORER_URL = "https://explore.openaq.org/locations/{id}"
PM25_PARAMETER_ID = 2          # OpenAQ parameter ID for PM2.5
WINDOW_HOURS = 24              # averaging window used by the AQI scale
MIN_HOURS = 18                 # project rule: need 18 of 24 hourly values (75%)
STALE_AFTER_HOURS = 24         # older data are shown as "no recent data"
REQUEST_PAUSE_SECONDS = 1.1    # keeps us well under 60 requests per minute
MAX_LOCATIONS = 15

ROOT = Path(__file__).resolve().parent.parent
LOCATIONS_FILE = ROOT / "config" / "locations.json"
SCALE_FILE = ROOT / "config" / "aqi_scale.json"
OUTPUT_FILE = ROOT / "data" / "pm25.json"
CANDIDATES_FILE = ROOT / "data" / "candidates.json"


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------

def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(dt: datetime | None) -> str | None:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if dt else None


def parse_time(value) -> datetime | None:
    """Accepts '2026-11-13T10:00:00Z', {'utc': '...'} or None."""
    if isinstance(value, dict):
        value = value.get("utc")
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def truncate_1dp(x: float) -> float:
    """Truncate (not round) to one decimal place, matching the precision of
    the breakpoint table. This is a project rule, stated on the website."""
    return math.floor(x * 10) / 10


def categorise(value: float | None, scale: dict) -> str | None:
    if value is None:
        return None
    for cat in scale["categories"]:
        lo, hi = cat["min"], cat["max"]
        if value >= lo and (hi is None or value <= hi):
            return cat["key"]
    return None


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    tmp.replace(path)


# --------------------------------------------------------------------------
# OpenAQ client
# --------------------------------------------------------------------------

class OpenAQ:
    def __init__(self, api_key: str, session: requests.Session | None = None):
        self.session = session or requests.Session()
        self.session.headers.update({"X-API-Key": api_key, "Accept": "application/json"})

    def get(self, path: str, params: dict | None = None) -> dict:
        url = f"{API_BASE}{path}"
        for attempt in range(3):
            resp = self.session.get(url, params=params, timeout=30)
            time.sleep(REQUEST_PAUSE_SECONDS)
            if resp.status_code == 429:
                wait = int(resp.headers.get("x-ratelimit-reset", "60") or 60)
                print(f"  rate limit reached; waiting {wait}s", file=sys.stderr)
                time.sleep(min(max(wait, 1), 120))
                continue
            if resp.status_code == 401:
                raise SystemExit("OpenAQ rejected the API key (401). Check the OPENAQ_API_KEY secret.")
            if 500 <= resp.status_code < 600 and attempt < 2:
                time.sleep(5)
                continue
            resp.raise_for_status()
            return resp.json()
        resp.raise_for_status()
        return resp.json()

    def location(self, location_id: int) -> dict | None:
        results = self.get(f"/locations/{location_id}").get("results") or []
        return results[0] if results else None

    def hours(self, sensor_id: int, start: datetime, end: datetime) -> list[dict]:
        params = {"datetime_from": iso(start), "datetime_to": iso(end), "limit": 100, "page": 1}
        return self.get(f"/sensors/{sensor_id}/hours", params).get("results") or []

    def pakistan_pm25_locations(self) -> list[dict]:
        out, page = [], 1
        while True:
            data = self.get("/locations", {"iso": "PK", "parameters_id": PM25_PARAMETER_ID,
                                           "limit": 1000, "page": page})
            batch = data.get("results") or []
            out.extend(batch)
            if len(batch) < 1000:
                return out
            page += 1


# --------------------------------------------------------------------------
# Building one row of the table
# --------------------------------------------------------------------------

def location_metadata(loc: dict) -> dict:
    licenses = []
    for lic in loc.get("licenses") or []:
        attribution = lic.get("attribution") or {}
        licenses.append({
            "name": lic.get("name"),
            "attribution_name": attribution.get("name"),
            "attribution_url": attribution.get("url"),
        })
    return {
        "openaq_name": loc.get("name"),
        "locality": loc.get("locality"),
        "provider": (loc.get("provider") or {}).get("name"),
        "owner": (loc.get("owner") or {}).get("name"),
        "openaq_is_monitor_flag": loc.get("isMonitor"),
        "latitude": (loc.get("coordinates") or {}).get("latitude"),
        "longitude": (loc.get("coordinates") or {}).get("longitude"),
        "licenses": licenses,
    }


def find_pm25_sensors(loc: dict) -> list[dict]:
    """A location can have more than one PM2.5 sensor; return all of them."""
    out = []
    for sensor in loc.get("sensors") or []:
        param = sensor.get("parameter") or {}
        if param.get("id") == PM25_PARAMETER_ID or param.get("name") == "pm25":
            out.append(sensor)
    return out


def find_pm25_sensor(loc: dict) -> dict | None:
    sensors = find_pm25_sensors(loc)
    return sensors[0] if sensors else None


def summarise_hours(hours: list[dict], window_start: datetime, now: datetime) -> dict:
    """Average the valid hourly values that end inside the 24-hour window."""
    values, ends = [], []
    for h in hours:
        value = h.get("value")
        period = h.get("period") or {}
        end = parse_time(period.get("datetimeTo"))
        if value is None or end is None:
            continue
        if not (window_start < end <= now):
            continue
        if not isinstance(value, (int, float)) or value < 0:
            continue  # negative or non-numeric readings are excluded
        values.append(float(value))
        ends.append(end)
    return {
        "n": len(values),
        "mean": sum(values) / len(values) if values else None,
        "last_end": max(ends) if ends else None,
    }


def build_openaq_row(client: OpenAQ, entry: dict, scale: dict, now: datetime) -> dict:
    row = {
        "type": "openaq",
        "openaq_sensor_id": None,
        "display_name": entry.get("display_name"),
        "city": entry.get("city"),
        "openaq_location_id": entry.get("openaq_location_id"),
        "openaq_url": EXPLORER_URL.format(id=entry.get("openaq_location_id")),
        "status": None,
        "pm25_24h_mean": None,
        "hours_used": 0,
        "window_start_utc": None,
        "window_end_utc": None,
        "latest_hour_end_utc": None,
        "category": None,
        "units": "µg/m³",
        "message": None,
    }
    try:
        loc = client.location(int(entry["openaq_location_id"]))
    except (requests.RequestException, KeyError, ValueError) as exc:
        row.update(status="error", message=f"Could not read location: {exc}")
        return row
    if not loc:
        row.update(status="error", message="Location not found on OpenAQ.")
        return row
    row.update(location_metadata(loc))

    sensors = [x for x in find_pm25_sensors(loc)
               if (x.get("parameter") or {}).get("units") in (None, "µg/m³", "ug/m3", "μg/m³")]
    if not sensors:
        row.update(status="no_recent_data", message="This location has no PM2.5 sensor reporting in µg/m³.")
        return row

    window_start = now - timedelta(hours=WINDOW_HOURS)
    row["window_start_utc"], row["window_end_utc"] = iso(window_start), iso(now)
    # Try every PM2.5 sensor at the location and keep the one with the most hourly values.
    s, errors = {"n": 0, "mean": None, "last_end": None}, []
    for sensor in sensors:
        try:
            hours = client.hours(int(sensor["id"]), window_start, now)
        except requests.RequestException as exc:
            errors.append(str(exc))
            continue
        candidate = summarise_hours(hours, window_start, now)
        if candidate["n"] > s["n"]:
            s = candidate
            row["openaq_sensor_id"] = sensor.get("id")
    if s["n"] == 0 and errors and len(errors) == len(sensors):
        row.update(status="error", message=f"Could not read hourly data: {errors[0]}")
        return row
    row["hours_used"] = s["n"]
    row["latest_hour_end_utc"] = iso(s["last_end"])

    if s["n"] == 0:
        row.update(status="no_recent_data", message="No PM2.5 data in the last 24 hours.")
    elif s["n"] < MIN_HOURS:
        row.update(status="insufficient_data",
                   message=f"Only {s['n']} of {WINDOW_HOURS} hourly values in the last 24 hours "
                           f"(at least {MIN_HOURS} needed).")
    else:
        mean = truncate_1dp(s["mean"])
        row.update(status="ok", pm25_24h_mean=mean, category=categorise(mean, scale))
    return row


def build_manual_row(entry: dict, scale: dict) -> dict:
    value = entry.get("pm25_24h_mean")
    period_end = parse_time(entry.get("period_end_utc"))
    usable = isinstance(value, (int, float)) and value >= 0 and period_end is not None \
        and bool(entry.get("source_url"))
    mean = truncate_1dp(float(value)) if usable else None
    return {
        "type": "manual",
        "display_name": entry.get("display_name"),
        "city": entry.get("city"),
        "status": "manual_snapshot" if usable else "no_recent_data",
        "pm25_24h_mean": mean,
        "snapshot_period_end_utc": iso(period_end),
        "category": categorise(mean, scale),
        "units": "µg/m³",
        "source_name": entry.get("source_name"),
        "source_url": entry.get("source_url"),
        "recorded_by": entry.get("recorded_by"),
        "message": ("Manual snapshot. This is not current data."
                    if usable else "No checked value available."),
    }


# --------------------------------------------------------------------------
# Main modes
# --------------------------------------------------------------------------

def run_update(client: OpenAQ) -> None:
    config = load_json(LOCATIONS_FILE)
    scale = load_json(SCALE_FILE)
    entries = config.get("locations") or []
    if len(entries) > MAX_LOCATIONS:
        raise SystemExit(f"config/locations.json lists {len(entries)} locations; the maximum is {MAX_LOCATIONS}.")

    now = utc_now()
    rows = []
    for entry in entries:
        name = entry.get("display_name")
        if entry.get("type") == "manual":
            rows.append(build_manual_row(entry, scale))
        elif entry.get("type") == "openaq" and entry.get("openaq_location_id"):
            print(f"Fetching {name} (OpenAQ {entry['openaq_location_id']})")
            rows.append(build_openaq_row(client, entry, scale, now))
        else:
            print(f"Skipping {name}: no valid type or OpenAQ ID", file=sys.stderr)

    output = {
        "generated_utc": iso(now),
        "data_source": {
            "name": "OpenAQ",
            "url": "https://openaq.org",
            "api": "OpenAQ API v3",
            "note": "Data belong to the providers named for each location; see each location's licence.",
        },
        "method": {
            "value": "Mean of hourly PM2.5 averages over the 24 hours before generated_utc",
            "units": "µg/m³",
            "window_hours": WINDOW_HOURS,
            "min_hours_required": MIN_HOURS,
            "stale_after_hours": STALE_AFTER_HOURS,
            "rounding": "Truncated to one decimal place before categorising",
            "project_rules_note": "The 18-hour minimum, the truncation and the 24-hour staleness limit are this project's own rules.",
        },
        "scale": scale,
        "locations": rows,
    }
    write_json(OUTPUT_FILE, output)
    ok = sum(1 for r in rows if r["status"] == "ok")
    print(f"Wrote {OUTPUT_FILE.relative_to(ROOT)}: {ok} of {len(rows)} locations have a current 24-hour average.")


def run_discover(client: OpenAQ) -> None:
    now = utc_now()
    found = []
    for loc in client.pakistan_pm25_locations():
        sensor = find_pm25_sensor(loc)
        last = parse_time(loc.get("datetimeLast"))
        meta = location_metadata(loc)
        found.append({
            "openaq_location_id": loc.get("id"),
            "openaq_url": EXPLORER_URL.format(id=loc.get("id")),
            **meta,
            "pm25_sensor_id": sensor.get("id") if sensor else None,
            "datetime_last_utc": iso(last),
            "hours_since_last": round((now - last).total_seconds() / 3600, 1) if last else None,
        })
    found.sort(key=lambda r: (r["hours_since_last"] is None, r["hours_since_last"] or 0))
    write_json(CANDIDATES_FILE, {"generated_utc": iso(now), "country": "PK", "locations": found})
    print(f"{len(found)} PM2.5 locations found in Pakistan. Saved to {CANDIDATES_FILE.relative_to(ROOT)}.")
    print(f"{'ID':>9}  {'hrs ago':>8}  {'monitor':>7}  {'provider':<22} name / locality")
    for r in found[:60]:
        print(f"{r['openaq_location_id']:>9}  {str(r['hours_since_last']):>8}  "
              f"{str(r['openaq_is_monitor_flag']):>7}  {str(r['provider'])[:22]:<22} "
              f"{r['openaq_name']} / {r['locality']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--discover", action="store_true",
                        help="list PM2.5 locations in Pakistan instead of updating data/pm25.json")
    args = parser.parse_args()

    api_key = os.environ.get("OPENAQ_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("OPENAQ_API_KEY is not set. See README for how to add it.")
    client = OpenAQ(api_key)
    run_discover(client) if args.discover else run_update(client)


if __name__ == "__main__":
    main()
