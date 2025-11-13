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
    Trapezoid membership funkcia: 0 .. 1 .. 0
    a <= b <= c <= d
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
    Sigmoid (napr. pre 'vysoké hodnotenie').
    x0 = prah, k = strmosť.
    """
    x = np.asarray(x, dtype=float)
    return 1.0 / (1.0 + np.exp(-k * (x - x0)))


def text_similarity(a: str, b: str) -> float:
    """
    Rýchla textová podobnosť 0–1:
    Jaccard na množine slov (veľmi jednoduché, ale rýchle).
    """
    if not b:
        return 0.0
    a = (a or "").lower().split()
    b = b.lower().split()
    set_a, set_b = set(a), set(b)
    if not set_a or not set_b:
        return 0.0
    inter = len(set_a & set_b)
    union = len(set_a | set_b)
    return inter / union


# ---------------------------------------------------
# 3) hlavná funkcia na fuzzy vyhľadávanie
# ---------------------------------------------------
def fuzzy_search(
    q_text: str = "dream",
    prefer_short: bool = True,
    prefer_new: bool = True,
    high_rating: bool = True,
    prefer_niche: bool = True,
    limit_rows_from_db: int = 50_000,   # koľko filmov natiahnem z DB
    n_candidates_for_text: int = 5_000, # na koľkých rátam textovú podobnosť
    top_n: int = 30,                    # koľko výsledkov vrátim
    current_year: int = 2025,
) -> pd.DataFrame:
    """
    Vráti DataFrame top_n filmov zoradených podľa fuzzy_score.
    """

    # --------- 3.1 načítanie dát z DB ----------
    sql = text("""
        SELECT
            id,
            title,
            runtime,
            release_year,
            vote_average,
            popularity
        FROM movies
        WHERE release_year IS NOT NULL
          AND runtime IS NOT NULL
        LIMIT :limit_rows
    """)

    df = pd.read_sql(sql, engine, params={"limit_rows": limit_rows_from_db})

    # bezpečné typy
    df["runtime"] = pd.to_numeric(df["runtime"], errors="coerce")
    df["vote_average"] = pd.to_numeric(df["vote_average"], errors="coerce")
    df["popularity"] = pd.to_numeric(df["popularity"], errors="coerce")
    df["release_year"] = pd.to_numeric(df["release_year"], errors="coerce")

    df = df.dropna(subset=["runtime", "vote_average", "popularity", "release_year"])

    # --------- 3.2 fuzzy membershipy (bez textu) ----------
    # dĺžka: "krátky film" ~ 0–60–90–110 min
    mu_len = mu_trap(df["runtime"], 0, 60, 90, 110)

    # novota: "nový" ~ posledných 5 rokov
    age = current_year - df["release_year"].astype(int)
    mu_year = 1 - mu_sigmoid(age, x0=5, k=1.0)  # menší vek = väčšia μ

    # hodnotenie: "vysoké" od 7.0 vyššie
    mu_rate = mu_sigmoid(df["vote_average"], x0=7.0, k=1.2)

    # popularita: "niche" = klesajúca funkcia popularity
    mu_pop = 1.0 / (1.0 + (df["popularity"] / 50.0))

    # váhy podľa preferencií
    w_len = 0.35 if prefer_short else 0.10
    w_year = 0.25 if prefer_new else 0.10
    w_rate = 0.25 if high_rating else 0.10
    w_pop = 0.15 if prefer_niche else 0.05

    base_score = (
        w_len * mu_len +
        w_year * mu_year +
        w_rate * mu_rate +
        w_pop * mu_pop
    )

    df["mu_len"] = mu_len
    df["mu_year"] = mu_year
    df["mu_rate"] = mu_rate
    df["mu_pop"] = mu_pop
    df["base_score"] = base_score

    # hrubý filter – dropni úplne slabé filmy
    df = df[df["base_score"] > 0.2]

    if df.empty:
        return df  # nič nenašiel

    # --------- 3.3 textová podobnosť len na top kandidátoch ----------
    n_cand = min(len(df), n_candidates_for_text)
    df = df.nlargest(n_cand, "base_score").copy()

    df["mu_text"] = df["title"].apply(lambda t: text_similarity(t, q_text))

    # finálne skóre = base * (0.6 + 0.4 * mu_text)
    df["fuzzy_score"] = df["base_score"] * (0.6 + 0.4 * df["mu_text"])

    # --------- 3.4 zoradenie a výber stĺpcov ----------
    df = df.sort_values("fuzzy_score", ascending=False)

    cols = [
        "id", "title", "release_year", "runtime", "vote_average", "popularity",
        "mu_len", "mu_year", "mu_rate", "mu_pop", "mu_text", "fuzzy_score"
    ]
    return df[cols].head(top_n)


# ---------------------------------------------------
# 4) demo spustenie
# ---------------------------------------------------
if __name__ == "__main__":
    # príklad: hľadám krátke, nové, dobre hodnotené, skôr niche filmy,
    # ktorých názov súvisí so slovom "dream"
    results = fuzzy_search(
        q_text="dream",
        prefer_short=True,
        prefer_new=True,
        high_rating=True,
        prefer_niche=True,
        top_n=20
    )

    pd.set_option("display.max_colwidth", 80)
    print(results)
