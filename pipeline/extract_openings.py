import argparse, hashlib, json, re, time, requests
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "data" / "cache" / "wiki"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
HEADERS = {"User-Agent": "PredictionModel-research/0.1 (personal research)"}

def parse_years(arg):
    if not arg:
        return []
    parts = arg.split(',')
    years = []
    for p in parts:
        if '-' in p:
            a,b = p.split('-')
            years.extend(range(int(a), int(b)+1))
        else:
            years.append(int(p))
    return sorted(set(years))

def read_tsv(year):
    path = ROOT / f"data/raw/boxoffice/{year}.tsv"
    if not path.exists():
        return None
    lines = [l.rstrip('\n') for l in path.read_text(encoding='utf-8').splitlines() if l.strip()!='']
    header_idx = None
    for i,line in enumerate(lines):
        if 'Rank' in line:
            header_idx = i
            break
    if header_idx is None:
        return None
    header = [h.strip() for h in lines[header_idx].split('\t')]
    data = []
    for line in lines[header_idx+1:]:
        cells = [c.strip() for c in line.split('\t')]
        if len(cells) != len(header):
            continue
        try:
            rank = int(cells[0])
        except:
            continue
        row = dict(zip(header, cells))
        row['_rank'] = rank
        data.append(row)
    return data, header

def money_to_int(text):
    text = text.strip()
    if not text:
        return None
    # Remove surrounding $ or US$
    text = re.sub(r'^(US\$|\$)\s*', '', text, flags=re.I)
    # Detect million/billion
    mult = 1
    if re.search(r'\billion\b', text, re.I):
        mult = 1_000_000_000
        text = re.sub(r'\s*\billion\b', '', text, flags=re.I)
    elif re.search(r'\bmillion\b', text, re.I):
        mult = 1_000_000
        text = re.sub(r'\s*\bmillion\b', '', text, flags=re.I)
    # Remove commas and spaces
    text = re.sub(r'[,\s]', '', text)
    if not text:
        return None
    try:
        val = float(text)
    except:
        return None
    return int(round(val * mult))

def parse_films(raw_data, year):
    films = []
    for r in raw_data:
        try:
            rank = int(r['_rank'])
        except:
            continue
        title = r.get('Release', '').strip()
        if not title:
            continue
        # theaters
        theaters_raw = r.get('Theaters', '')
        try:
            theaters = int(re.sub(r'[^\d]', '', theaters_raw)) if theaters_raw != '-' else 0
        except:
            theaters = 0
        # total gross
        gross_raw = r.get('Total Gross', '')
        try:
            gross = money_to_int(gross_raw) if gross_raw != '-' else 0
        except:
            gross = 0
        # release date
        date_raw = r.get('Release Date', '')
        date_iso = ''
        if date_raw:
            parts = [p.strip() for p in date_raw.split(',')]
            month_day = parts[0]
            if len(parts) > 1:
                year_part = re.search(r'\d{4}', parts[1])
                year_val = year_part.group() if year_part else str(year)
            else:
                year_val = str(year)
            try:
                # parse month_day like "Jan 8"
                dt = pd.to_datetime(f"{month_day} {year_val}", errors='coerce')
                if not pd.isna(dt):
                    date_iso = dt.date().isoformat()
            except:
                date_iso = f"{year_val}-01-01"
        else:
            date_iso = f"{year}-01-01"
        distributor = r.get('Distributor', '').strip()
        genre = r.get('Genre', '')
        films.append({
            'year': year,
            'rank': rank,
            'title': title,
            'theaters_max': theaters,
            'total_gross': gross,
            'release_date': date_iso,
            'distributor': distributor,
            'genre': genre
        })
    return films

def normalize(s):
    s = s.lower()
    s = re.sub(r'\([^)]*\)', '', s)  # remove parentheses and contents
    s = re.sub(r'[^\w\s]', '', s)    # remove punctuation
    s = re.sub(r'\s+', ' ', s).strip()
    if s.startswith('the '):
        s = s[4:]
    return s

def wiki_request(params):
    key = hashlib.sha1(json.dumps(params, sort_keys=True).encode()).hexdigest()
    cache_path = CACHE_DIR / f"{key}.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text())
    url = "https://en.wikipedia.org/w/api.php"
    for attempt in range(1,7):
        time.sleep(1.0)  # be polite: at most ~1 live request per second
        resp = requests.get(url, params=params, headers=HEADERS, timeout=20)
        if resp.status_code == 429 or 500 <= resp.status_code < 600:
            if attempt == 6:
                resp.raise_for_status()
            time.sleep(int(resp.headers.get("Retry-After", 0) or 0) or 10 * attempt)
            continue
        resp.raise_for_status()
        data = resp.json()
        cache_path.write_text(json.dumps(data))
        return data
    return None

def search_wiki(title, year):
    params = {
        'action':'query',
        'list':'search',
        'srsearch':f'{title} {year} film',
        'srlimit':5,
        'format':'json'
    }
    data = wiki_request(params)
    if not data:
        return None, 'no_article', ''
    norm_title = normalize(title)
    # Prefer "Title (2024 film)" / "Title (film)" over a bare "Title", which may be a person, book or disambiguation page
    exact_film = exact = starts_film = None
    for item in data.get('query',{}).get('search',[]):
        rt = item.get('title','')
        if normalize(rt) == norm_title:
            if 'film' in rt.lower() and exact_film is None:
                exact_film = rt
            elif exact is None:
                exact = rt
        elif normalize(rt).startswith(norm_title) and 'film' in rt.lower() and starts_film is None:
            starts_film = rt
    chosen = exact_film or exact or starts_film
    if not chosen:
        return None, 'no_article', ''
    # fetch extract
    params2 = {
        'action':'query',
        'prop':'extracts',
        'explaintext':1,
        'redirects':1,
        'titles':chosen,
        'format':'json'
    }
    data2 = wiki_request(params2)
    pages = data2.get('query',{}).get('pages',{})
    extract = ''
    for v in pages.values():
        extract = v.get('extract','')
        break
    # verify
    if (re.search(rf'\b({year-1}|{year})\b', extract) and re.search(r'\bfilm\b', extract, re.I)
            and re.search(r'box office|grossed|opening weekend', extract, re.I)):
        status = 'matched'
    else:
        status = 'unverified'
    return chosen, status, extract

def extract_opening(text, total_gross):
    if not text:
        return None, None, False, '', ''
    # find box office section
    lines = text.split('\n')
    start_idx = -1
    for i,line in enumerate(lines):
        if re.match(r'^==+\s*Box office\s*==+$', line, re.I):
            start_idx = i
            break
    if start_idx != -1:
        # find next heading of same or higher level
        # determine level by count of '=' at start
        first = lines[start_idx]
        m = re.match(r'^(=+)', first)
        if m:
            level = len(m.group(1))
        else:
            level = 2
        end_idx = len(lines)
        for i in range(start_idx+1, len(lines)):
            m2 = re.match(r'^(=+)', lines[i])
            if m2:
                lvl2 = len(m2.group(1))
                if lvl2 <= level:
                    end_idx = i
                    break
        section = '\n'.join(lines[start_idx:end_idx])
    else:
        section = text
    # split sentences
    sentences = re.split(r'\.\s+(?=[A-Z])', section)
    evidence = ''
    opening = None
    opening_theaters = None
    estimate_flag = False
    money_pattern = re.compile(r'(?:US\$|\$)\s*\d{1,3}(?:,\d{3})*(?:\.\d+)?(?:\s*(?:million|billion)\b)?', re.I)
    reject_terms = re.compile(r'\b(?:worldwide|global|international|overseas|china|chinese|uk|united kingdom|japan|korea|india|france|germany|australia|mexico)\b', re.I)
    accept_terms = re.compile(r'united states and canada|domestic|north america|us box office|u\.s\. box office|in the united states', re.I)
    weekend_terms = re.compile(r'opening weekend|opened|opening|debuted|debut|first weekend', re.I)
    theater_pattern = re.compile(r'(\d{1,3}(?:,\d{3})*\d*)\s*(?:theaters|theatres|locations|cinemas)', re.I)
    for sent in sentences:
        sent_strip = sent.strip()
        if not sent_strip:
            continue
        low = sent_strip.lower()
        if not weekend_terms.search(low):
            continue
        money_matches = list(money_pattern.finditer(sent_strip))
        if not money_matches:
            continue
        # reject check
        if reject_terms.search(low) and not accept_terms.search(low):
            continue
        # Pick the amount tied to the weekend phrase; sentences often also give previews / first-day figures.
        amts = [(m, money_to_int(m.group())) for m in money_matches]
        amts = [(m, v) for m, v in amts if v and v >= 100_000]
        # Drop partial-weekend figures: previews, advance/fan screenings, single days
        partial = re.compile(r'^[^$]{0,45}(preview|advance|early screening|fan screening|first day|opening day|thursday|friday|saturday|sunday alone)', re.I)
        amts = [(m, v) for m, v in amts
                if not partial.search(sent_strip[m.end():]) and 'including' not in sent_strip[max(0, m.start() - 15):m.start()].lower()]
        if not amts:
            continue
        cue_before = re.compile(r'(debut(?:ed)? (?:to|with)|open(?:ed|s)? (?:to|with)|weekend (?:gross|total) of|opening weekend of|went on to (?:debut|gross|make|earn)[^$]{0,25})\s*(?:an estimated\s*|about\s*|around\s*)?$', re.I)
        cue_after = re.compile(r'^[^.$]{0,40}(opening weekend|first weekend|over the weekend|its debut weekend)', re.I)
        cued = [(m, v) for m, v in amts
                if cue_before.search(sent_strip[max(0, m.start() - 60):m.start()]) or cue_after.search(sent_strip[m.end():])]
        amt = (cued[0] if cued else max(amts, key=lambda t: t[1]))[1]
        opening = amt
        evidence = sent_strip[:300]
        # estimate flag
        if 'estimated' in low or 'projected' in low:
            estimate_flag = True
        # theater count
        tmatch = theater_pattern.search(sent_strip)
        if tmatch:
            opening_theaters = int(re.sub(r'[,\s]', '', tmatch.group(1)))
        break
    if opening is None:
        return None, None, False, '', ''
    return opening, opening_theaters, estimate_flag, evidence, ''

def sanity_flag(opening, total_gross):
    if opening is None or total_gross == 0:
        return ''
    lower = total_gross * 0.06  # wide releases rarely open below 6% or above 90% of their total
    upper = total_gross * 0.90
    if opening < lower or opening > upper:
        return 'suspect'
    return 'ok'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--years', type=str, default='2010-2025')
    parser.add_argument('--limit', type=int, default=None)
    parser.add_argument('--film-list-only', action='store_true')
    args = parser.parse_args()
    years_list = parse_years(args.years)
    if not years_list:
        print("No years specified.")
        return
    all_films = []
    for y in years_list:
        res = read_tsv(y)
        if res is None:
            continue
        raw_data, _ = res
        films = parse_films(raw_data, y)
        if args.limit:
            films = films[:args.limit]
        all_films.extend(films)
    if not all_films:
        print("No TSV files found or no data.")
        return
    film_df = pd.DataFrame(all_films)
    interim_dir = ROOT / "data" / "interim"
    interim_dir.mkdir(parents=True, exist_ok=True)
    film_path = interim_dir / "film_list.csv"
    film_df[['year','rank','title','theaters_max','total_gross','release_date','distributor','genre']].to_csv(film_path, index=False)
    print(f"Saved film list to {film_path} ({len(film_df)} rows)")
    if args.film_list_only:
        return
    # Step 2+3
    results = []
    yearly_stats = {}
    for y in years_list:
        yearly_stats[y] = {'total':0,'matched':0,'with_open':0,'suspect':0}
    for idx,row in film_df.iterrows():
        y = row['year']
        title = row['title']
        yearly_stats[y]['total'] += 1
        wiki_title, status, extract = search_wiki(title, y)
        opening_wiki = None
        opening_theaters_wiki = None
        estimate_flag = False
        evidence = ''
        if status in ('matched','unverified') and extract:
            opening_wiki, opening_theaters_wiki, estimate_flag, evidence, _ = extract_opening(extract, row['total_gross'])
        sanity = sanity_flag(opening_wiki, row['total_gross'])
        results.append({
            'year': y,
            'title': title,
            'theaters_max': row['theaters_max'],
            'total_gross': row['total_gross'],
            'release_date': row['release_date'],
            'distributor': row['distributor'],
            'wiki_title': wiki_title if wiki_title else '',
            'match_status': status,
            'opening_wiki': opening_wiki if opening_wiki is not None else '',
            'opening_theaters_wiki': opening_theaters_wiki if opening_theaters_wiki is not None else '',
            'estimate_flag': estimate_flag,
            'sanity': sanity,
            'evidence': evidence
        })
        if status == 'matched':
            yearly_stats[y]['matched'] += 1
        if opening_wiki is not None:
            yearly_stats[y]['with_open'] += 1
            if sanity == 'suspect':
                yearly_stats[y]['suspect'] += 1
    out_df = pd.DataFrame(results)
    out_path = interim_dir / "openings_wiki.csv"
    out_df.to_csv(out_path, index=False)
    print(f"Saved openings to {out_path}")
    total_films = sum(v['total'] for v in yearly_stats.values())
    total_matched = sum(v['matched'] for v in yearly_stats.values())
    total_with = sum(v['with_open'] for v in yearly_stats.values())
    total_suspect = sum(v['suspect'] for v in yearly_stats.values())
    print("\nYearly summary:")
    for y in years_list:
        ys = yearly_stats[y]
        print(f"{y}: films={ys['total']}, matched={ys['matched']}, with opening={ys['with_open']}, suspect={ys['suspect']}")
    print(f"\nOverall: films={total_films}, matched={total_matched}, with opening={total_with}, suspect={total_suspect}")
    if total_matched > 0:
        coverage = total_with / total_matched * 100
        print(f"Coverage of matched films with opening: {coverage:.1f}%")
    else:
        print("No matched films.")

if __name__ == "__main__":
    main()