**Walkthrough 1 — How the dataset was built**  

### 1 What we're predicting  
We are forecasting the domestic (United States and Canada) opening‑weekend gross for each film. The target variable is placed on a logarithmic scale, which turns prediction errors into percentage‑based measures that are easier to interpret.  

Interview soundbite: **“I predict the log‑scaled domestic opening‑weekend gross so that model errors can be read directly as percent deviations.”**  

### 2 Where the box office numbers come from  
The opening‑weekend figures come from Box Office Mojo’s yearly “In‑year releases” tables covering 2010 through 2025. I copied each year’s table by hand—one click per year using a saved bookmark—because the site blocks automated scraping. Those tables list opening weekend gross, opening theater count, total gross, release date, and distributor. Earlier I tried the “Calendar grosses” view, but it included holdovers and re‑runs and missed real releases for 2023‑2025; switching to the In‑year view solved both problems.  

Interview soundbite: **“I gathered the data manually from Box Office Mojo’s In‑year releases tables (2010‑2025) after confirming that view gives a clean list of true theatrical releases.”**  

### 3 Which films count  
Only films that opened in 800 or more theaters are included. The 800‑theater threshold is consistent because every yearly table lists films down to that level (the 2025 page ends at 800), giving a uniform definition across all years. Re‑releases are dropped, which leaves 1,959 films; 40 of them are event screenings—such as concert films, episodes of *The Chosen*, and Fathom one‑night events—which are flagged and excluded from the models. The rule was recorded beforehand in a pre‑registration file named HYPOTHESES.md as a dated amendment before any modeling began.  

Interview soundbite: **“I defined the sample as all movies with at least 800 opening theaters, removed re‑releases and 40 special‑event screenings, and locked that rule in a pre‑registration document.”**  

### 4 Adding film details (TMDB)  
For each film I pulled supplemental information from the TMDB API. This includes genre, MPAA rating, runtime, the top‑three billed cast members, director, franchise or collection membership, and keyword‑based flags that indicate whether the film is a sequel, based on a novel, comic, video game, true story, or remake.  

Interview soundbite: **“I enriched each movie with TMDB data such as genre, rating, runtime, cast, director, franchise tags, and source‑type flags like sequel or based on a novel.”**  

### 5 Checking the matches  
Matching the Box Office Mojo list to TMDB succeeded for 1,952 of the 1,959 films—a 99.6 % match rate. The seven unmatched records are all the event screenings previously excluded. During matching I noticed a few issues: foreign films with identical titles sometimes appeared first (e.g., *Flight* 2012, *Gold*, *One Life*, *Sight*, *The Letters*, *Unfriended*); the title “Spiral” was incorrectly linked to “The Spiral”; and TMDB uses alternate titles such as “Insurgent” for *The Divergent Series: Insurgent* and “Expend4bles” for *The Expendables 4*. I addressed these by tightening the matching rule (loose title matches must have near‑exact release dates, and a match with no US release on record and a far‑off date is rejected), building an alternate‑title list, and applying about 15 hand‑checked overrides that were verified by checking the lead actor.  

Interview soundbite: **“I matched 99.6 % of the films to TMDB, fixed title conflicts with stricter date rules, an alternate‑title list, and a handful of manually verified overrides.”**  

### 6 What we deliberately left out  
I intentionally omitted production budget because TMDB budget fields are usually populated after a film’s release, so using them would leak future information—upcoming movies would have no budget and the model would penalize them unfairly. I also left out trailer views and social‑media metrics, as those cannot be reconstructed for historical dates, and marketing spend, which is not publicly disclosed.  

Interview soundbite: **“I excluded budget, trailer/social media, and marketing spend to avoid look‑ahead bias and because those data are not reliably available for past releases.”**  

### 7 Known weak spots  
All “track record” features—such as star power, director history, franchise strength, and distributor effect—are built exclusively from films that opened at least seven days before the target movie, ensuring no future data creeps in. Nevertheless, the dataset has limitations: star‑power metrics for films from 2010‑2012 are weak because the history only begins in 2010, so I start testing star effects in 2013; for animated films I set star power to missing because a famous voice is not the same draw as a star on screen; the pandemic years 2020‑2021 are omitted from training; and a small number of releases that opened in 600‑799 theaters are absent from the data because they fall below the 800‑theater cutoff.  

Interview soundbite: **“I built track‑record variables from prior releases only, but note that early‑year star data are limited, animated stars are missing, 2020‑21 are excluded due to COVID, and films opening below 800 theaters are not represented.”**