# fuzzy_search.py

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

from config import DATABASE_URL   # DATABASE_URL z .env cez config.py


# ---------------------------------------------------
# 1) pripojenie na PostgreSQL
# ---------------------------------------------------
engine = create_engine(DATABASE_URL)


# ---------------------------------------------------
# 2) fuzzy membership funkcie
# ---------------------------------------------------
def mu_trap(x, a, b, c, d):
    """
    Trapezoid membership: 0 -> 1 -> 0 na intervale [a,d]
    """
    x = np.asarray(x, dtype=float)
    res = np.zeros_like(x, dtype=float)

    # stúpajúca hrana
    mask = (x > a) & (x < b)
    res[mask] = (x[mask] - a) / (b - a)

    # plateau
    mask = (x >= b) & (x <= c)
    res[mask] = 1.0

    # klesajúca hrana
    mask = (x > c) & (x < d)
    res[mask] = (d - x[mask]) / (d - c)

    return res


def mu_sigmoid(x, x0, k):
    """
    Sigmoid (napr. pre 'vysoké hodnotenie' / 'nový film').
    """
    x = np.asarray(x, dtype=float)
    return 1.0 / (1.0 + np.exp(-k * (x - x0)))


# ---------------------------------------------------
# 3) pomocná funkcia pre jazyk
# ---------------------------------------------------
def compute_lang_mu(df: pd.DataFrame, lang_pref: str) -> np.ndarray:
    """
    Jazyková "fuzzy" (v podstate crisp) membership.
    lang_pref: "EN", "CZ", "SK", "ES", "DE", "none"
    Pozerá do stĺpcov spoken_languages + original_language.
    """
    if lang_pref == "none":
        return np.zeros(len(df), dtype=float)

    code_map = {
        "EN": "en",
        "CZ": "cs",
        "SK": "sk",
        "ES": "es",
        "DE": "de",
    }
    code = code_map.get(lang_pref.upper())
    if code is None:
        return np.zeros(len(df), dtype=float)

    def row_mu(row):
        all_langs = (
            str(row.get("spoken_languages", "") or "") + " " +
            str(row.get("original_language", "") or "")
        ).lower()
        return 1.0 if code in all_langs else 0.0

    return df.apply(row_mu, axis=1).to_numpy(dtype=float)


# ---------------------------------------------------
# 4) hlavná fuzzy funkcia (bez názvu, bez text similarity)
# ---------------------------------------------------
def fuzzy_search(
    length_pref: str = "none",   # "short", "medium", "long", "none"
    year_pref: str = "none",     # "new", "older", "retro", "none"
    rating_pref: str = "none",   # "excellent", "good", "average", "bad", "none"
    pop_pref: str = "none",      # "blockbuster", "average", "unknown", "none"
    lang_pref: str = "none",     # "EN", "CZ", "SK", "ES", "DE", "none"
    limit_rows_from_db: int = 50_000,
    top_n: int = 30,
    current_year: int = 2025,
) -> pd.DataFrame:
    """
    Fuzzy vyhľadávanie filmov podľa:
      - dĺžky (length_pref)
      - roku (year_pref)
      - ratingu (rating_pref)
      - popularity (pop_pref)
      - jazyka (lang_pref)
    """

    # --- 4.1 načítanie dát z DB ---
    sql = text("""
        SELECT
            id,
            title,
            runtime,
            release_year,
            vote_average,
            popularity,
            spoken_languages,
            original_language
        FROM movies
        WHERE release_year IS NOT NULL
          AND runtime IS NOT NULL
        LIMIT :limit_rows
    """)

    df = pd.read_sql(sql, engine, params={"limit_rows": limit_rows_from_db})

    # bezpečné typovanie
    df["runtime"] = pd.to_numeric(df["runtime"], errors="coerce")
    df["vote_average"] = pd.to_numeric(df["vote_average"], errors="coerce")
    df["popularity"] = pd.to_numeric(df["popularity"], errors="coerce")
    df["release_year"] = pd.to_numeric(df["release_year"], errors="coerce")

    df = df.dropna(subset=["runtime", "vote_average", "popularity", "release_year"])

    if df.empty:
        return df

    # --- 4.2 fuzzy membershipy ---

    # 4.2.1 dĺžka – tri fuzzy sety
    mu_short = mu_trap(df["runtime"], 0, 60, 90, 110)      # krátky
    mu_medium = mu_trap(df["runtime"], 80, 100, 120, 140)  # stredný
    mu_long = mu_trap(df["runtime"], 120, 140, 180, 260)   # dlhý

    if length_pref == "short":
        mu_len_pref = mu_short
    elif length_pref == "medium":
        mu_len_pref = mu_medium
    elif length_pref == "long":
        mu_len_pref = mu_long
    else:
        mu_len_pref = np.zeros_like(mu_short)

    # 4.2.2 rok – nové / staršie / retro podľa veku (age)
    age = current_year - df["release_year"].astype(int)

    mu_year_new = mu_trap(age, -1, 0, 3, 6)          # nové (cca do 5 rokov)
    mu_year_older = mu_trap(age, 4, 8, 15, 30)       # staršie (taký middle)
    mu_year_retro = mu_trap(age, 20, 30, 60, 120)    # retro, veľmi staré

    if year_pref == "new":
        mu_year_pref = mu_year_new
    elif year_pref == "older":
        mu_year_pref = mu_year_older
    elif year_pref == "retro":
        mu_year_pref = mu_year_retro
    else:
        mu_year_pref = np.zeros_like(mu_year_new)

    # 4.2.3 rating – vynikajúce / dobre / priemerne / zle
    score = df["vote_average"]

    mu_rating_excellent = mu_trap(score, 7.5, 8.5, 10.0, 11.0)
    mu_rating_good = mu_trap(score, 6.0, 7.0, 8.0, 9.0)
    mu_rating_average = mu_trap(score, 4.5, 5.5, 6.5, 7.5)
    mu_rating_bad = mu_trap(score, -1.0, 0.0, 4.5, 6.0)

    if rating_pref == "excellent":
        mu_rating_pref = mu_rating_excellent
    elif rating_pref == "good":
        mu_rating_pref = mu_rating_good
    elif rating_pref == "average":
        mu_rating_pref = mu_rating_average
    elif rating_pref == "bad":
        mu_rating_pref = mu_rating_bad
    else:
        mu_rating_pref = np.zeros_like(mu_rating_excellent)

    # 4.2.4 popularita – dynamicky podľa distribúcie
    pop = df["popularity"].astype(float)
    pmin = float(pop.min())
    pmax = float(pop.max())

    if pmax == pmin:
        # všetko má rovnakú popularitu → ber to ako priemer
        mu_pop_unknown = np.zeros_like(pop, dtype=float)
        mu_pop_average = np.ones_like(pop, dtype=float)
        mu_pop_blockbuster = np.zeros_like(pop, dtype=float)
    else:
        q1 = float(pop.quantile(0.33))
        q2 = float(pop.quantile(0.66))

        mu_pop_unknown = mu_trap(pop, pmin - 1, pmin, q1, q2)
        mu_pop_average = mu_trap(pop, q1 * 0.8, q1, q2, q2 * 1.2)
        mu_pop_blockbuster = mu_trap(pop, q2, q2 * 1.05, pmax, pmax * 1.05)

    if pop_pref == "unknown":
        mu_pop_pref = mu_pop_unknown
    elif pop_pref == "average":
        mu_pop_pref = mu_pop_average
    elif pop_pref == "blockbuster":
        mu_pop_pref = mu_pop_blockbuster
    else:
        mu_pop_pref = np.zeros_like(pop, dtype=float)

    # 4.2.5 jazyk – z `spoken_languages` + `original_language`
    mu_lang = compute_lang_mu(df, lang_pref)

    # --- 4.3 váhy (podľa toho, čo ťa zaujíma) ---
    w_len = 0.20 if length_pref != "none" else 0.05
    w_year = 0.20 if year_pref != "none" else 0.05
    w_rating = 0.25 if rating_pref != "none" else 0.05
    w_pop = 0.20 if pop_pref != "none" else 0.05
    w_lang = 0.15 if lang_pref != "none" else 0.0

    weights = np.array([w_len, w_year, w_rating, w_pop, w_lang], dtype=float)
    total_w = weights.sum()
    if total_w == 0:
        # fallback – keby si dal všade "none"
        weights = np.array([0.2, 0.2, 0.2, 0.2, 0.2], dtype=float)
        total_w = 1.0
    weights /= total_w

    w_len, w_year, w_rating, w_pop, w_lang = weights

    base_score = (
        w_len * mu_len_pref +
        w_year * mu_year_pref +
        w_rating * mu_rating_pref +
        w_pop * mu_pop_pref +
        w_lang * mu_lang
    )

    df["mu_short"] = mu_short
    df["mu_medium"] = mu_medium
    df["mu_long"] = mu_long
    df["mu_len_pref"] = mu_len_pref

    df["mu_year_new"] = mu_year_new
    df["mu_year_older"] = mu_year_older
    df["mu_year_retro"] = mu_year_retro
    df["mu_year_pref"] = mu_year_pref

    df["mu_rating_excellent"] = mu_rating_excellent
    df["mu_rating_good"] = mu_rating_good
    df["mu_rating_average"] = mu_rating_average
    df["mu_rating_bad"] = mu_rating_bad
    df["mu_rating_pref"] = mu_rating_pref

    df["mu_pop_unknown"] = mu_pop_unknown
    df["mu_pop_average"] = mu_pop_average
    df["mu_pop_blockbuster"] = mu_pop_blockbuster
    df["mu_pop_pref"] = mu_pop_pref

    df["mu_lang"] = mu_lang

    df["fuzzy_score"] = base_score

    # hrubý filter – vyhoď úplne slabé filmy
    df = df[df["fuzzy_score"] > 0.2]

    if df.empty:
        return df

    # zoradenie
    df = df.sort_values("fuzzy_score", ascending=False)

    cols = [
        "id", "title", "release_year", "runtime", "vote_average",
        "popularity", "spoken_languages", "original_language",
        "mu_len_pref", "mu_year_pref", "mu_rating_pref", "mu_pop_pref",
        "mu_lang", "fuzzy_score"
    ]
    return df[cols].head(top_n)


# ---------------------------------------------------
# 5) CLI vstup – výbery kategórií
# ---------------------------------------------------
def _ask_length_pref() -> str:
    """
    s = short, m = medium, l = long, Enter = none
    """
    raw = input(
        "Akú dĺžku filmu preferuješ? "
        "[s] krátky, [m] stredný, [l] dlhý, Enter = je mi to jedno: "
    ).strip().lower()

    if raw == "s":
        return "short"
    if raw == "m":
        return "medium"
    if raw == "l":
        return "long"
    return "none"


def _ask_year_pref() -> str:
    """
    n = nové, s = staršie, r = retro, Enter = none
    """
    raw = input(
        "Aký vek filmu chceš? "
        "[n] nové, [s] staršie, [r] retro, Enter = je mi to jedno: "
    ).strip().lower()

    if raw == "n":
        return "new"
    if raw == "s":
        return "older"
    if raw == "r":
        return "retro"
    return "none"


def _ask_rating_pref() -> str:
    """
    1 = vynikajúce, 2 = dobré, 3 = priemerné, 4 = zlé, Enter = none
    """
    raw = input(
        "Aký rating preferuješ? "
        "[1] vynikajúce, [2] dobré, [3] priemerné, [4] zlé, Enter = je mi to jedno: "
    ).strip().lower()

    if raw == "1":
        return "excellent"
    if raw == "2":
        return "good"
    if raw == "3":
        return "average"
    if raw == "4":
        return "bad"
    return "none"


def _ask_pop_pref() -> str:
    """
    b = blockbuster, p = priemerné, n = neznáme, Enter = none
    """
    raw = input(
        "Akú popularitu chceš? "
        "[b] blockbuster, [p] priemerné, [n] neznáme, Enter = je mi to jedno: "
    ).strip().lower()

    if raw == "b":
        return "blockbuster"
    if raw == "p":
        return "average"
    if raw == "n":
        return "unknown"
    return "none"


def _ask_lang_pref() -> str:
    """
    Jazyk: EN, CZ, SK, ES, DE alebo Enter = none
    """
    raw = input(
        "Preferovaný jazyk? "
        "[EN] English, [CZ] Czech, [SK] Slovak, [ES] Spanish, [DE] German, Enter = je mi to jedno: "
    ).strip().upper()

    if raw in ("EN", "CZ", "SK", "ES", "DE"):
        return raw
    return "none"


def _ask_int(prompt: str, default: int) -> int:
    raw = input(prompt).strip()
    if raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        print("Neplatné číslo, beriem default:", default)
        return default


if __name__ == "__main__":
    print("=== Fuzzy vyhľadávanie filmov (bez názvu) ===")

    length_pref = _ask_length_pref()
    year_pref = _ask_year_pref()
    rating_pref = _ask_rating_pref()
    pop_pref = _ask_pop_pref()
    lang_pref = _ask_lang_pref()

    top_n = _ask_int("Koľko výsledkov chceš zobraziť? [20]: ", default=20)

    results = fuzzy_search(
        length_pref=length_pref,
        year_pref=year_pref,
        rating_pref=rating_pref,
        pop_pref=pop_pref,
        lang_pref=lang_pref,
        top_n=top_n,
    )

    pd.set_option("display.max_colwidth", 80)
    print(results)
