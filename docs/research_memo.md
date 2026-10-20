**What predicts a box office opening now? Stars, buzz, and the post-2020 market**  
*Research memo for film-industry analysts and academics*  

---

### Abstract  
This memo evaluates what information available before a film’s wide release predicts its opening-weekend gross in the United States from 2010-2025, focusing on star power, pre-release attention, and changes after the COVID-19 shutdown. Using a pre-registered analysis of 1,959 wide releases (≥800 theaters) with features drawn from TMDB, Wikipedia page-view histories, and market conditions, we test five hypotheses (H1–H5) with ridge regression, CatBoost, and CatBoost-with-attention models. Forecast accuracy is measured by median absolute percent error on a sealed 2025 hold-out (148 films). The only hypothesis that survives multiple-testing correction is H5: accelerating Wikipedia attention in the final weeks is associated with beating the traditional forecast. Star track records show little association with openings before or after 2020, and although forecast errors were higher after 2020, that difference did not survive the correction. Accelerating attention offers a measurable short-term signal; star track records add little to forecasts.  

---

## 1 Question and motivation  

The film industry continually seeks leading indicators of box-office performance to guide marketing spend, release-date selection, and exhibition negotiations. Prior work has highlighted star power, franchise status, and pre-release buzz as predictive, but the post-2020 market—characterized by shifted exhibition patterns, altered audience habits, and evolving digital media consumption—may have changed the relevance of these signals.  

Our central question is: **Which pre-release factors are associated with opening-weekend gross in the current market, and how have their associations evolved since 2020?** Answering this helps analysts distinguish durable drivers from transient noise and informs studios where to allocate forecasting resources.  

---

## 2 Data  

- **Sample**: 1,959 US wide releases (opening in ≥800 theaters) from 2010-2025. Re-releases, event screenings, and streaming-first titles were excluded. The years 2020-2021 were omitted from training and testing to avoid pandemic-related distortions.  
- **Outcome**: Opening-weekend gross and opening theater count from Box Office Mojo in-year release tables (manually copied).  
- **Metadata** (genre, MPAA rating, runtime, top-3 cast, director, franchise/collection, source keywords) sourced from TMDB (99.6% match rate; unmatched titles were event screenings).  
- **Attention features**:  
  - Wikipedia page-views for each film’s article (available from July 2015; usable from 2016 onward).  
  - Wikipedia page-views for the source work via Wikidata “based on” links (253 adaptations in the confirmatory test).  
  - Variables capture the level and growth of views from T-28 to T-8 (four weeks to one week before release) and source-work views in the 365-day window ending T-180.  
- **Track-record variables** (computed only from films at least seven days older):  
  - Calendar/holiday timing, genre, rating, runtime, English-language flag.  
  - Franchise history, source flags.  
  - Star track record: mean log opening of the top-3 cast’s prior five years.  
  - Director and distributor track records.  
  - Competition and current market level (median opening of the prior three months).  
  - Opening theater count (known one week out).  

All features satisfy the “knowable before release” requirement; any variable that could leak post-release information (e.g., TMDB budgets entered after release) was omitted per the pre-registration.  

---

## 3 Method  

### Pre-registration  
Hypotheses, analysis plan, and decision rules were written down and version-controlled in a git repository before historical data were collected. Four dated amendments refined the theater-count rule, removed budget because of leakage, set the star-test start at 2013 (to allow a burn-in for track records), and added H6 (to be evaluated on 2026 releases). The model specification was frozen in a git commit before any 2025 data were examined.  

### Features  
The feature set described in Section 2 was constructed for each film at two checkpoints:  

- **T-28** (approximately four weeks before release).  
- **T-7** (one week before release).  

### Models  
1. **Comps baseline** – median opening of recent films sharing the same genre and sequel status.  
2. **Ridge regression** – linear model with L2 penalty.  
3. **CatBoost** – gradient-boosted decision trees handling categorical variables natively.  
4. **CatBoost + attention** – CatBoost augmented with the attention features (level and growth of Wikipedia views).  

All models were evaluated with a rolling-origin backtest: for each quarter from Q1 2014 through Q4 2025, models were retrained on all films released before that quarter and then forecast that quarter's films. This mimics real-time forecasting and prevents look-ahead bias.  

### Uncertainty quantification  
For each checkpoint we derived 80 % prediction intervals from the 10th and 90th percentiles of each model's errors over the preceding eight quarters.  

### Sealed hold-out  
The 2025 slate (148 films) was never used during development (feature design, model choice, or the development tests); it entered only the single confirmatory run, after the specification was frozen.  

### Multiple-testing correction  
We applied the Holm-Bonferroni procedure to the five pre-registered hypotheses (H1–H5). Ordered p-values were compared to Holm thresholds:  

| Hypothesis | Holm threshold |
|------------|----------------|
| H1         | 0.050          |
| H2         | 0.0167         |
| H3         | 0.0250         |
| H4         | 0.0125         |
| H5         | 0.0100         |

A hypothesis is deemed *supported* only if its p-value is ≤ its Holm threshold.  

---

## 4 Results  

### Forecast accuracy (hold-out 2025)  

| Checkpoint | Model                | Median absolute % error | 80 % range coverage |
|------------|----------------------|------------------------|---------------------|
| T-7 | CatBoost | 32 % | 81 % |
| T-7 | CatBoost + attention | 35 % | 76 % |
| T-7 | Ridge | 36 % | 80 % |
| T-7 | Comps baseline | 73 % | 85 % |
| T-28 | CatBoost + attention | 42 % | 78 % |
| T-28 | CatBoost | 49 % | 86 % |
| T-28 | Ridge | 50 % | 82 % |

CatBoost + attention trains only on 2016 + films; against a traditional CatBoost trained on the same 2016+ window it was slightly better at T-7 (35% vs 36%), so the all-years traditional CatBoost's edge on 2025 likely comes from its longer training history.  

### Hypothesis tests  

| Hypothesis | Effect estimate (log units) | 95 % CI                | p-value | Holm threshold | Supported? |
|------------|-----------------------------|-----------------------|---------|----------------|------------|
| H1 – star effect smaller after 2020 (change) | +0.081 | –0.067 to +0.229 | 0.86 (0.94 with theater count) | 0.050 | No |
| H2 – less predictable after 2020 (increase in median absolute log error, CatBoost) | +0.080* | — | 0.004 (ridge 0.035) | 0.0167 | No |
| H3 – attention reduces error (CatBoost gain) | +0.029 | +0.016 to +0.042 | 0.25† (larger p across models) | 0.025 | No |
| H4 – source-work attention associated with beating the forecast (adaptations) | +0.048 | 0.000 to +0.095 | 0.024 | 0.0125 | No |
| H5 – accelerating attention in final weeks associated with beating the forecast (controlling for level) | +0.104 | +0.037 to +0.171 | 0.001 | 0.010 | **Yes** |

\*Increase computed as 0.416 − 0.336 (CatBoost).  
†The pre-registered test uses the larger p-value across CatBoost (p < 0.001) and ridge (p = 0.25); therefore H3 is not supported after correction.  

### Headline descriptive patterns  

- **Star effects**: Year-by-year regressions show the star coefficient hovering near zero in every year from 2013-2024, both before and after adjusting for theater count.  
- **Distributor track record**: The coefficient on a distributor’s recent log opening (per standard deviation) rose from roughly 0.4 in 2013 to about 0.9 in 2024, indicating growing predictive power of distributor reputation.  
- **Franchise premium**: Franchise films enjoyed a log-opening premium of approximately 0.5-0.8 before 2020 and 0.8-1.1 after 2020, suggesting a modest uplift in the post-pandemic market.  
---

## 5 Where the model fails (case studies)  

In the development back-test, attention improvements were most evident for films that initially under-performed relative to expectations:  

- **Flops**: Films opening below half the forecast saw their actual/forecast ratio rise from a median of 0.36 to 0.43 when attention features were added. Specific examples: *Babylon* (0.13× → 0.25×) and *Whitney Houston: I Wanna Dance with Somebody* (0.15× → 0.33×).  
- **Cultural events**: Attention also tempered over-forecasts for major events. *Barbie*’s ratio fell from 5.2× to 2.85× the forecast; similar improvements were noted for *Nosferatu*, *Wicked*, and *Conclave*.  
- **Audiences poorly captured by English Wikipedia**: Faith-oriented titles (*Sound of Freedom*, *Unplanned*, *I Can Only Imagine*) and Spanish-language comedies (*How to Be a Latin Lover*, *Overboard*) showed little to no improvement, because their core audiences are not reflected in English-language page-view metrics. This motivated the pre-registered H6: films from faith-focused and Spanish-language distributors are under-forecast by the traditional model, to be tested on 2026 releases only.  

These cases illustrate that while attention can improve forecasts for certain segments, it does not universally correct model misspecifications, especially when the relevant audience engages outside the measured digital trace.  

---

## 6 Limitations  

- **Attention as a proxy**: Wikipedia view levels may partially reflect marketing spend, which is not directly observable; thus the association does not isolate pure audience interest.  
- **Non-causal interpretation**: All reported relationships are associative; we cannot claim that altering star casting or attention will causally change box-office outcomes.  
- **Theater count endogeneity**: Studios set opening-theater counts based on expected demand, so including theater count may absorb some of the predictive signal otherwise attributed to stars or buzz.  
- **Data coverage**: Wikipedia renames and incomplete Wikidata “based on” links mean some adaptations or international titles are under-counted.  
- **Sample size post-2020**: Although the post-2020 training window includes several hundred films, it remains smaller than the pre-2020 corpus, potentially limiting power to detect subtle shifts.  
- **Excluded releases**: Films opening in 600-799 theaters were omitted, so results may not generalize to narrower releases.  

---

## 7 Implications for studios and distributors  

1. **Monitor attention trajectories** – The robust association between accelerating Wikipedia interest in the final two weeks and out-performance suggests that real-time tracking of view growth can refine short-term forecasts, especially for mid-range titles where traditional comps are noisy.  
2. **Treat star track records as a weak forecasting signal** - They add little once other pre-release information is known; this says nothing about stars' value for marketing, awards or long-tail revenue, which this study does not measure.
3. **Watch the distributor's recent record** - It has become an increasingly informative signal of opening performance (an association; it may reflect which films distributors choose and how they market them).
4. **Franchise strength persists** – Franchise premiums have remained stable or slightly increased after 2020, reinforcing the value of maintaining and extending existing properties.  
5. **Consider language-specific signals** – For audiences not well captured by English Wikipedia (faith-based, Spanish-language, or other linguistic groups), alternative attention metrics (e.g., local-language platforms, social media) may be required to improve forecasts.  

Overall, studios might achieve better opening-weekend predictions by combining traditional comps and distributor/reputation metrics with a dynamic attention signal, while treating star track records as a weak forecasting signal.  

---

## 8 Next steps  

- **Live forecast test**: Forecasts are frozen in git before release; *The Cat in the Hat* (Nov 6, 2026) is the headline test.  
- **H6 evaluation**: Test, on 2026 releases only, whether films from faith-focused and Spanish-language distributors open above the frozen traditional model's forecast.
- **Feature expansion**: Pre-register, then test, Spanish-language Wikipedia attention and community-distributor flags as new features.
- **Model updating**: As each new quarter becomes available, we will repeat the rolling-origin back-test to ensure that any evolving market dynamics (post-pandemic recovery, shifting streaming windows) are captured in the training data.  

By adhering to the pre-registered, transparent workflow outlined herein, we aim to provide the film industry with reliable, evidence-based tools for forecasting openings in an increasingly complex media landscape.  

---