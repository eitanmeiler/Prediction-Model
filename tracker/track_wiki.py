#!/usr/bin/env python3
import sys, json, csv, datetime, pathlib, argparse, time, urllib.request, urllib.error, urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
WATCHLIST = ROOT / "tracker" / "watchlist.json"
CSV_PATH = ROOT / "data" / "live" / "wiki_pageviews.csv"
LOG_PATH = ROOT / "data" / "live" / "tracker.log"
UA = "PredictionModel-research/0.1 (personal research; contact via GitHub)"
DEFAULT_START = datetime.date(2026, 6, 1)
MAX_RETRIES = 3
BACKOFF = 10
SLEEP_BETWEEN = 1.0

def fetch_views(article: str, start: datetime.date, end: datetime.date):
    enc = urllib.parse.quote(article, safe='')
    url = (f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
           f"en.wikipedia/all-access/user/{enc}/daily/"
           f"{start:%Y%m%d}/{end:%Y%m%d}")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    data = json.load(resp)
                    return data.get("items", [])
                elif resp.status == 404:
                    return None  # treat as no data
                else:
                    raise urllib.error.HTTPError(url, resp.status, resp.reason,
                                                 resp.headers, None)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                body = e.read().decode("utf-8", "ignore")
                # Wikimedia publishes daily data with a lag of 1-3 days; that also comes back as 404
                return "LAG" if "do not have data for those date" in body else None
            if attempt < MAX_RETRIES:
                time.sleep(BACKOFF * (attempt + 1))
                continue
            return e
        except (urllib.error.URLError, OSError) as e:  # DNS/network down (e.g. just after wake), timeouts
            if attempt < MAX_RETRIES:
                time.sleep(30 * (attempt + 1))
                continue
            return e
        except Exception:
            if attempt < MAX_RETRIES:
                time.sleep(BACKOFF)
                continue
            raise
    return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=str, help="Backfill start date (YYYY-MM-DD)")
    parser.add_argument("--dry-run", action="store_true", help="Only show what would be fetched")
    args = parser.parse_args()

    if not WATCHLIST.is_file():
        print(f"Watchlist not found: {WATCHLIST}", file=sys.stderr)
        return 1

    try:
        watchlist = json.loads(WATCHLIST.read_text())
    except Exception as e:
        print(f"Failed to read watchlist: {e}", file=sys.stderr)
        return 1

    today = datetime.datetime.utcnow().date()
    yesterday = today - datetime.timedelta(days=1)

    # Load existing CSV to know latest dates per (film_id, role)
    latest = {}
    if CSV_PATH.is_file():
        with CSV_PATH.open(newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                fid = row["film_id"]
                role = row["role"]
                d = datetime.datetime.strptime(row["date"], "%Y-%m-%d").date()
                key = (fid, role)
                if key not in latest or d > latest[key]:
                    latest[key] = d

    start_arg = datetime.date.fromisoformat(args.start) if args.start else DEFAULT_START
    rows_added = 0
    errors = 0
    problems = []
    lagged = 0
    films_processed = 0

    for film in watchlist.get("films", []):
        fid = film.get("id")
        title = film.get("title")
        release_str = film.get("release_date")
        try:
            release = datetime.datetime.strptime(release_str, "%Y-%m-%d").date()
        except Exception:
            continue
        if (today - release).days > 60:
            continue
        films_processed += 1
        articles = film.get("wiki_articles", {})
        for role, article in articles.items():
            key = (fid, role)
            last = latest.get(key)
            start_date = (last + datetime.timedelta(days=1)) if last else start_arg
            if start_date > yesterday:
                continue
            time.sleep(SLEEP_BETWEEN)
            result = fetch_views(article, start_date, yesterday)
            if isinstance(result, Exception):
                errors += 1
                problems.append(f"{fid}/{role}: HTTP {getattr(result, 'code', '?')}")
                continue
            if result == "LAG":
                lagged += 1
                continue
            if result is None:  # 404: article missing or no views in range
                problems.append(f"{fid}/{role}: 404 {article}")
                continue
            to_write = []
            for item in result:
                ts = item.get("timestamp", "")
                if len(ts) < 8:
                    continue
                try:
                    dt = datetime.datetime.strptime(ts[:8], "%Y%m%d").date()
                except ValueError:
                    continue
                if last and dt <= last:
                    continue
                views = item.get("views", 0)
                to_write.append((fid, role, article, dt.isoformat(), views,
                                 datetime.datetime.utcnow().isoformat() + "Z"))
            if args.dry_run:
                print(f"Would add {len(to_write)} rows for {fid}/{role}")
                continue
            if to_write:
                CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
                write_header = not CSV_PATH.is_file()
                with CSV_PATH.open("a", newline='') as f:
                    writer = csv.writer(f)
                    if write_header:
                        writer.writerow(["film_id", "role", "article", "date", "views", "fetched_at"])
                    writer.writerows(to_write)
                rows_added += len(to_write)
                # update latest to avoid re-fetching same dates in same run
                latest[key] = max((datetime.datetime.strptime(r[3], "%Y-%m-%d").date() for r in to_write),
                                  default=latest.get(key))
            time.sleep(SLEEP_BETWEEN)

    if lagged:
        problems.append(f"{lagged} articles: Wikimedia has not published data after the last stored date yet (normal lag, retried next run)")
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not args.dry_run:
        with LOG_PATH.open("a") as logf:
            logf.write(f"{datetime.datetime.utcnow().isoformat()}Z, rows_added={rows_added}, errors={errors}, notes={problems}\n")
    print(f"Processed {films_processed} films, added {rows_added} rows, {errors} errors.")
    for msg in problems:
        print("  " + msg)
    return 0

if __name__ == "__main__":
    sys.exit(main())
