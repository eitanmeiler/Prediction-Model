**Walkthrough 2 — How the model is built and tested**

### 1 Two forecast moments  
The model makes two predictions for each film. The first checkpoint, called T‑28, occurs four weeks before release. At this point the exact number of theaters is not yet known, so the forecast relies only on information that is already fixed, such as the month, genre, and franchise history.  
The second checkpoint, T‑7, arrives one week before opening. By then the theater count and the lineup of competing movies opening the same weekend are known, as well as the recent openings of those competitors. This extra information lets the model sharpen its estimate.  
**Interview soundbite:** The model gives an early, theater‑free guess four weeks out and a refined guess one week out when the competition and screen count are clear.

### 2 The features  
All inputs used by the model are known before the movie hits theaters. They include the release timing—month, week of the year, and whether the opening falls on a holiday weekend such as Memorial Day, July 4, Thanksgiving, or Christmas. Genre flags, MPAA rating, runtime, and whether the film is in English are also supplied.  
Franchise membership and the franchise’s own opening history are included, as are source flags that tell whether the movie is a sequel, based on a novel, comic, video game, true story, or a remake.  
The track record of the top‑three cast members is captured by the mean log opening of their films from the previous five years, and a similar measure is used for the director. The distributor’s recent performance and the current market level—the median opening of wide releases in the three months prior—are also features. Finally, the model accounts for competition: other wide releases opening the same weekend and films that arrived 5‑19 days earlier. Budget is deliberately omitted because TMDB budget figures are typically filled in only after release.  
**Interview soundbite:** Every factor the model looks at is something that can be known before the film opens, from release date and genre to cast history and the current market climate.

### 3 Three models  
Three different approaches are tested on the same set of features. The first is a simple baseline: it takes the median opening of recent movies that share the same main genre and sequel status. This “comps baseline” gives a quick reference point.  
The second approach is ridge regression, a linear model that shrinks its coefficients toward zero to avoid over‑fitting while still capturing the main effects of each feature.  
The third approach is CatBoost, a gradient‑boosted decision‑tree algorithm that can learn interactions between features, such as how a holiday release might matter more for an animated family film than for a horror film.  
**Interview soundbite:** I compare a plain‑average baseline, a penalized linear model, and a flexible tree‑based model to see which captures patterns best.

### 4 How we test (no peeking at the future)  
Testing follows a rolling‑origin backtest design. The data are split into quarters from the first quarter of 2014 through the last quarter of 2024. For each quarter, the models are trained only on movies that were released **before** that quarter begins, ensuring no future information leaks into the training set. Then the trained models predict the openings of movies that actually came out in that quarter.  
The years 2020 and 2021 are left out of this process because the pandemic disrupted normal patterns and would distort the learning. The year 2025 is kept completely sealed; no model sees any 2025 data until the final evaluation after development work is finished.  
Across all quarters, 1,128 films receive a prediction from each model, giving a sizable sample for assessing performance.  
**Interview soundbite:** By training on past quarters and predicting the next quarter—while skipping the pandemic years and sealing 2025—the test mimics real‑world forecasting without any forbidden look‑ahead.

### 5 Results  
At the T‑7 checkpoint, the comps baseline typically misses the actual opening by about 65 % and gets roughly 18 % of films within a ±25 % band around the true value.  
The ridge regression model improves on this, with a typical miss of about 38 % and about 36 % of films landing inside the ±25 % window.  
CatBoost shows very similar numbers: a typical miss around 38 % and roughly 36 % within ±25 %.  
A paired bootstrap test shows that the difference between ridge and CatBoost is not statistically significant, so the simpler ridge model is chosen as the primary model for practical use.  
When looking only at the earlier T‑28 checkpoint, the typical miss rises to about 45 %, reflecting the loss of theater‑count and competition information.  
**Interview soundbite:** Ridge regression cuts the typical error from 65 % with the baseline to about 38 % at one week out, and its performance is statistically indistinguishable from the more complex CatBoost.

### 6 The 2022 lesson  
The first version of the model learned mostly from pre‑pandemic films, when box‑office openings were generally larger. When it was applied to 2022—the first year of post‑COVID reopening—it over‑predicted openings by roughly 1.7 ×, because it expected the pre‑COVID market size to still hold.  
Adding a feature that captures the current market level—the median opening of wide releases in the three months before each film—removed most of this bias. After this adjustment, the 2023‑2024 forecasts showed only a small residual bias.  
Nevertheless, 2022 remains a year where the model still tends to over‑forecast, illustrating how a sudden shift in the market can affect learned patterns until the model sees enough post‑shift data.  
**Interview soundbite:** The model’s early over‑prediction of 2022 taught us to include a current‑market feature, which corrected the bias for later years while leaving 2022 itself still slightly high.

### 7 Ranges, not just numbers  
Each forecast is accompanied by an 80 % prediction interval. This range is built from the model’s own errors observed in the previous eight quarters of the backtest, so it reflects recent performance rather than a theoretical assumption.  
When the intervals are checked against the actual openings in the backtest, about 78 % of the real‑world results fall inside the 80 % range—very close to the nominal target.  
This shows that the model’s uncertainty quantification is well calibrated: the intervals are neither too narrow nor too wide on average.  
**Interview soundbite:** The model’s 80 % error‑based ranges contain about 78% of actual outcomes, close to the 80% target, so the uncertainty estimates are reasonably calibrated.

### 8 What this does NOT show yet  
All results described come from the development backtest; the 2025 holdout data remain unseen and will be used only for the final, sealed evaluation.  
Analyses of star power have shown little predictive effect even before 2020, and there is no evidence of a decline in that effect over time (hypothesis H1 is not supported in the development run).  
The apparent drop in predictability after 2020 largely disappears once the 2022 outlier is removed, which suggests the pattern comes mostly from the 2022 reopening year rather than a lasting change (hypothesis H2 not supported when 2022 is excluded).  
Tests of whether Wikipedia pageviews or other attention measures improve the forecast (hypotheses H3‑H5) are still underway and have not yet been incorporated into the reported model.  
Finally, while a typical miss of about 38 % sounds large, box‑office openings are extremely heavy‑tailed; beating the simple comps baseline by this margin represents an honest and meaningful improvement.  
**Interview soundbite:** The backtest shows solid performance, but the 2025 data are still sealed, star and attention effects are unproven, and the error size must be viewed against the naturally uneven distribution of box‑office results.