# Data setup: step-by-step guide

This guide sets up the daily PM2.5 update. It needs no software on your computer: everything is done on github.com and openaq.org. It takes about 30 minutes.

## How the data pipeline works

1. Once a day, GitHub Actions (GitHub's free automation service) runs `scripts/fetch_pm25.py`.
2. For each location in `config/locations.json`, the script downloads the last 24 hours of hourly PM2.5 averages from the OpenAQ API (version 3).
3. If at least 18 of the 24 hourly values exist, it averages them. It then gives the average a category from the published US EPA AQI scale stored in `config/aqi_scale.json`.
4. If there is too little data, or none at all, the location is marked **no recent data** or **not enough data**. An old value is never shown as current.
5. The results are saved to `data/pm25.json`, and the website reads that file.

**Project rules.** These are our own choices, not part of the AQI scale, and the website states them:

- at least 18 of 24 hours of data are needed
- the average is truncated to one decimal place
- data older than 24 hours are hidden

## Files

| File | What it does |
|---|---|
| `scripts/fetch_pm25.py` | Downloads data and writes `data/pm25.json` |
| `config/locations.json` | The locations you choose (up to 15) |
| `config/aqi_scale.json` | AQI breakpoints and actions, with sources |
| `requirements.txt` | The one Python package the script needs (`requests`) |
| `.github/workflows/update-pm25.yml` | Runs the update every day |
| `.github/workflows/discover-locations.yml` | Lists all PM2.5 locations in Pakistan, run by hand |
| `data/pm25.json` | The output that the website reads |
| `data/candidates.json` | Created by the discovery workflow |

---

## Step 1: Get an OpenAQ API key

1. Go to https://explore.openaq.org/register and create a free account.
2. Confirm your email address.
3. Open https://explore.openaq.org/account and copy your **API key**.
4. Treat the key like a password. Never paste it into a file, an email or a chat.

The free key allows 60 requests per minute and 2,000 per hour. One daily run uses about 30 requests.

## Step 2: Store the key as a GitHub secret

A *secret* is stored encrypted by GitHub. Workflows can use it, but nobody can read it back, including you.

1. Open https://github.com/ftehreem306-ctrl/eco-health-data
2. Click **Settings**, the tab with a gear icon. If you don't see it, you are not signed in as the owner.
3. In the left menu, click **Secrets and variables**, then **Actions**.
4. Click **New repository secret**.
5. Fill in two boxes:
   - **Name:** `OPENAQ_API_KEY`. Spell it exactly like this, in capitals.
   - **Secret:** paste your key.
6. Click **Add secret**.

## Step 3: Allow workflows to save files

1. Go to **Settings**, then **Actions**, then **General**.
2. Scroll to **Workflow permissions**.
3. Choose **Read and write permissions** and click **Save**.

## Step 4: Upload the files

On the repository's main page, click **Add file**, then **Upload files**. Drag in these files and folders:

- `scripts/`
- `config/`
- `data/`
- `requirements.txt`
- `DATA_SETUP.md`

Then click **Commit changes**.

The `.github` folder starts with a dot, so it is often hidden and may not upload. Create each workflow file by hand instead:

1. Click **Add file**, then **Create new file**.
2. In the name box, type `.github/workflows/update-pm25.yml`. GitHub creates the folders as you type each `/`.
3. Paste the contents of `update-pm25.yml`, then click **Commit changes**.
4. Repeat for `.github/workflows/discover-locations.yml`.

## Step 5: Find which locations have data

1. Click the **Actions** tab.
2. If GitHub asks, click **I understand my workflows, go ahead and enable them**.
3. In the left list, click **Discover PM2.5 locations in Pakistan**, then **Run workflow**, then the green **Run workflow** button.
4. Wait 1–2 minutes until a green tick appears. A red cross means it failed; see Troubleshooting below.
5. Open `data/candidates.json` in the repository.

Each entry in `candidates.json` describes one location:

| Field | Meaning |
|---|---|
| `openaq_location_id` | The number to copy into `config/locations.json` |
| `hours_since_last` | How long ago the location last reported. Smaller is better; choose locations under 24. |
| `provider`, `owner` | Who supplies the data |
| `openaq_is_monitor_flag` | OpenAQ's own label for the station type. Its exact meaning is still to be confirmed in OpenAQ's documentation, so don't describe a station as "reference-grade" from this flag alone. |
| `licenses` | The data licence, which the website must show |

## Step 6: Choose your locations

1. Open `config/locations.json` and click the pencil icon to edit it.
2. Delete the two example entries.
3. Add up to 15 entries. Each one looks like this:

   ```json
   {
     "type": "openaq",
     "openaq_location_id": 123456,
     "display_name": "Lahore – name of the station",
     "city": "Lahore"
   }
   ```

   Separate entries with commas, and put no comma after the last one.
4. Click **Commit changes**.

If a city has no live location, you can add a **manual snapshot**. This is a value you copy yourself from a published 24-hour average:

```json
{
  "type": "manual",
  "display_name": "Quetta – manual snapshot",
  "city": "Quetta",
  "pm25_24h_mean": 41.2,
  "period_end_utc": "2026-11-10T19:00:00Z",
  "source_name": "Name of the agency or page",
  "source_url": "https://link-to-the-exact-page",
  "recorded_by": "Tehreem Fatima",
  "notes": "24-hour average for 10 Nov 2026"
}
```

The numbers above are only an example of the format, not real data. A manual snapshot always appears on the website as *"Manual snapshot dated …, not current data"*. If `pm25_24h_mean` or `source_url` is empty, the location is shown as **no recent data**.

## Step 7: Run the first update

1. Click **Actions**, then **Update PM2.5 data**, then **Run workflow**.
2. After the green tick appears, open `data/pm25.json` and check it:
   - each location has a `status`: `ok`, `insufficient_data`, `no_recent_data`, `manual_snapshot` or `error`
   - `pm25_24h_mean` is filled in only when `status` is `ok` or `manual_snapshot`

From now on, the update runs by itself every day at 08:17 Pakistan time.

## Troubleshooting

| What you see | What to do |
|---|---|
| `OPENAQ_API_KEY is not set` | The secret is missing or misspelled. Repeat Step 2. |
| `OpenAQ rejected the API key (401)` | The key is wrong or was changed. Copy it again from your OpenAQ account and update the secret. |
| `Permission denied` or `403` when pushing | Repeat Step 3. |
| A location always shows `error` | Check that its ID exists at `https://explore.openaq.org/locations/<ID>`. |
| The workflow stops running | GitHub can pause scheduled workflows in repositories that have had no activity for a long time. Go to **Actions**, open the workflow and click **Enable workflow**. |

## Rules from OpenAQ that this project follows

- **API key:** every request must carry it in the `X-API-Key` header.
- **Rate limits:** do not exceed 60 requests per minute or 2,000 per hour.
- **Unused jobs:** do not leave requests running when the data are no longer needed. If the project ends, disable the workflow.
- **No browser requests:** OpenAQ does not allow web browsers to request data directly. That is why the website reads a saved file instead of calling the API.
- **Licences and credit:** follow each data provider's licence and credit the source. The website shows the provider and licence for every location.
