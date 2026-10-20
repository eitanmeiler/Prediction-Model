# Live forecasting playbook (Oct–Dec 2026)

The rule that makes this credible: **a forecast counts only if it was committed to git before the film opened.**

## Every Monday (10 min)
1. Refresh this year's box office: open
   https://www.boxofficemojo.com/year/2026/?grossesOption=totalGrosses&sort=maxNumTheaters with
   `python3 tracker/collect_years.py` running, click **Copy BOM table** (it replaces last week's copy).
2. Rebuild: `./refresh.sh --quick`
3. Look at the dashboard (`.venv/bin/streamlit run app/dashboard.py`): new actuals appear in "Forecast vs. actual".

## Wednesday before each opening (theater counts come out)
1. Find each film's opening theater count (Box Office Mojo or trade reports usually post it Wednesday/Thursday).
2. Add it to `tracker/upcoming.json` as `"open_theaters": 3500` for that film.
3. `./refresh.sh --quick`, check the forecast looks sane (drivers, comparables), then freeze:
   `.venv/bin/python models/forecast_live.py --freeze`
4. Commit immediately: `git add forecasts/forecast_log.csv && git commit -m "Freeze forecasts for <date> openings" && git push`

## Monday after the opening
Refresh (step 1 above). The tracker page grades the forecast automatically: actual, % miss, inside the 80% range?

## Calendar
| Opens | Films | Freeze by |
|---|---|---|
| Oct 23 | Clayface, Klara and the Sun | Wed Oct 21 |
| Nov 6 | **The Cat in the Hat** (headline), I Play Rocky, Wild Horse Nine (limited — side case) | Wed Nov 4 |
| Nov 11–13 | Ghost Soldier, Ebenezer, How to Rob a Bank | Mon Nov 9 / Wed Nov 11 |
| Nov 20 | The Hunger Games: Sunrise on the Reaping | Wed Nov 18 |
| Nov 25 | Focker-in-Law, Hexed | Mon Nov 23 |

Before freezing, check dates and distributors in `tracker/upcoming.json` against Box Office Mojo — release dates move.
Forecasts can't be frozen until the 2026 box office has been loaded (the forecaster refuses, by design).
