"""Which features each forecast checkpoint may use. Shared by the backtest and the live forecaster."""

GENRE_FLAGS = ["g_action", "g_adventure", "g_animation", "g_comedy", "g_crime", "g_documentary", "g_drama",
               "g_family", "g_fantasy", "g_horror", "g_music", "g_mystery", "g_romance", "g_science_fiction",
               "g_thriller"]
CATEGORICAL = ["mpaa", "studio", "primary_genre"]

# known a month or more before release
EARLY = (["month", "weekofyear", "opens_weekday", "hol_memorial", "hol_july4", "hol_labor", "hol_thanksgiving",
          "hol_christmas", "hol_presidents_mlk", "runtime", "log_budget", "budget_known", "english",
          "in_collection", "sequel_like", "src_novel", "src_comic", "src_game", "src_true_story", "src_toy_tv",
          "remake", "star_mean", "star_best", "star_films", "star_n_with_history", "director_mean",
          "director_films", "franchise_prev_films", "franchise_prev_mean", "franchise_prev_last",
          "dist_recent_mean", "dist_recent_n", "comp_same_wkend_n", "mkt_recent_median"] + GENRE_FLAGS + CATEGORICAL)

# known about a week before release
LATE = ["open_theaters", "comp_same_wkend_theaters", "comp_recent_open_sum", "comp_recent_max"]


def checkpoint_features(cp):
    return EARLY + LATE if cp == "T-7" else EARLY
