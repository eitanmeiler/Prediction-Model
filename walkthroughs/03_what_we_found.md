**Walkthrough 3 — What we found (so far)**  

### 1 The question  
We started by asking whether the forces that drive opening‑weekend box office have shifted since 2020. In particular, we wanted to know if something beyond the usual suspects — star power, franchise status, and distributor track record — could explain why some films become surprise hits or flops. This work is still in development; the 2025 data are sealed and will be added later in a confirmatory run.  

**Interview soundbite:** Our goal was to see if the rules of the game changed after the pandemic and whether a new factor could be spotted.  

### 2 Stars: the myth check  
The first hypothesis (H1) suggested that star power declined after 2020. Our analysis shows that a star’s track record — measured as the mean opening of the top‑3 cast’s films in the prior five years — barely predicted openings even in the 2013‑2019 period, about 0.06 in log terms per unit, and it fell to about zero once theater count was accounted for. After 2020 the estimated change was +0.03, with a 95 % interval ranging from –0.14 to +0.20, indicating no clear decline. This matches earlier academic work that found stars were never strong predictors of opening performance.  

**Interview soundbite:** Stars do not appear to have lost or gained predictive power in recent years.  

### 3 Did openings get harder to predict?  
The second hypothesis (H2) argued that opening weekends became less predictable after 2020. We found that the model’s typical error was indeed higher in 2022‑2024 than in 2016‑2019, but almost all of that increase came from 2022, the reopening year, when a model trained on the larger pre‑COVID market over‑forecast openings by about 1.7 ×. When we removed 2022 from the analysis, the difference was not statistically significant. Thus, once the anomalous reopening year is set aside, there is no evidence that predictability has worsened.  

**Interview soundbite:** The apparent drop in forecast accuracy looks to be driven mainly by the unusual 2022 reopening window.  

### 4 The X factor: audience attention  
The third hypothesis (H3) examined whether pre‑release attention could improve forecasts. We defined attention as the number of Wikipedia page views for a film’s article (and its source material, when applicable) in the weeks before release. Adding this attention variable to a CatBoost model reduced prediction error by roughly 7 %, a gain that was clearly statistically significant. For a simpler ridge model the improvement was small and not significant. The benefit of attention was larger after 2020 than before it. With attention included, the typical one-week-out miss is about 34%, versus about 39–40% for the models without it; four weeks out it is about 41% versus about 47%.

Two follow-up tests looked at *which* kind of attention explains the misses. Films whose source material (a book, game or comic) already had a large Wikipedia audience tended to beat the forecast, but this was only borderline (H4, p = 0.038) and does not survive the correction for testing five hypotheses. Films whose attention was accelerating in the final weeks also tended to beat the forecast (H5, p = 0.014), which narrowly misses the corrected threshold.  

**Interview soundbite:** Pre‑release Wikipedia attention helps sharpen forecasts, especially in the post‑2020 period.  

### 5 What the misses look like  
Our review of the biggest forecasting errors reveals a pattern. Over‑performers include Barbie (about 5.7 × the forecast), *The Super Mario Bros. Movie*, *Moana 2*, *Deadpool*, and *Star Wars: The Force Awakens*. Video‑game adaptations beat the forecast by 50 % or more in 26 % of cases, compared with 17 % for other films, while comic adaptations rarely miss badly. On the under‑performance side, six of the fifteen largest misses were 2022 adult dramas or biopics. These examples are useful for case‑study work, but they are not presented as formal findings.  

**Interview soundbite:** The biggest upside surprises were cultural events like Barbie, video-game adaptations beat the forecast more often than other films, and several 2022 adult dramas fell well short — leads for case studies, not conclusions.  

### 6 What we can't say  
We must note that the attention metric may partly reflect marketing spend, which is not publicly available, so we cannot separate pure fan enthusiasm from advertising effects. Consequently, we can only speak of associations, not causal relationships. Additionally, the 2025 data remain sealed; the confirmatory run that will incorporate that information has not yet been performed.  

**Interview soundbite:** Attention correlates with better forecasts, but we cannot claim it drives box office results on its own.  

### 7 What happens next  
The next steps are to lock in live forecasts ahead of each release — starting with *The Cat in the Hat* on November 6 as the headline test, with *Klara and the Sun* and *Clayface* on October 23 as possible early trials — compare those forecasts to the actual openings, run the sealed 2025 evaluation exactly once, and then draft the final research memo summarizing all findings.  

**Interview soundbite:** We will soon test our model in real time and then incorporate the 2025 data to see if the patterns hold.