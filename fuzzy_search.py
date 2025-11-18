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
# 4) hlavná fuzzy funkcia
# ---------------------------------------------------
def fuzzy_search(
    length_pref: str = "none",   # "short", "medium", "long", "none"
    year_pref: str = "none",     # "new", "older", "retro", "none"
    rating_pref: str = "none",   # "excellent", "good", "average", "bad", "none"
    pop_pref: str = "none",      # "blockbuster", "average", "unknown", "none"
    lang_pref: str = "none",     # "EN", "CZ", "SK", "ES", "DE", "none"
    adult_pref: str = "non_adult_only",  # "adult_only", "non_adult_only", "none"
    limit_rows_from_db: int = 500_000,
    top_n: int = 30,
    current_year: int = 2025,
    verbose: bool = True,
) -> pd.DataFrame:
    """
    Fuzzy vyhľadávanie filmov podľa:
      - dĺžky (length_pref)
      - roku (year_pref)
      - ratingu (rating_pref) – rating sa ráta len pre filmy s vote_count >= 100
      - popularity (pop_pref)
      - jazyka (lang_pref)
      - adult filtra (adult_pref)
    """

    # --- 4.1 načítanie dát z DB ---
    if verbose:
        print("📥  Krok 1/5: Načítavam dáta z databázy...")

    sql = text("""
        SELECT
            id,
            title,
            runtime,
            release_year,
            vote_average,
            vote_count,
            popularity,
            spoken_languages,
            original_language,
            adult
        FROM movies
        WHERE release_year IS NOT NULL
          AND runtime IS NOT NULL
        LIMIT :limit_rows
    """)

    df = pd.read_sql(sql, engine, params={"limit_rows": limit_rows_from_db})

    # bezpečné typovanie
    df["runtime"] = pd.to_numeric(df["runtime"], errors="coerce")
    df["vote_average"] = pd.to_numeric(df["vote_average"], errors="coerce")
    df["vote_count"] = pd.to_numeric(df["vote_count"], errors="coerce").fillna(0).astype(int)
    df["popularity"] = pd.to_numeric(df["popularity"], errors="coerce")
    df["release_year"] = pd.to_numeric(df["release_year"], errors="coerce")
    df["adult"] = df["adult"].astype(bool)

    df = df.dropna(subset=["runtime", "vote_average", "popularity", "release_year"])

    # --- 4.1.1 filter na adult filmy ---
    if verbose:
        print("🔎  Krok 2/5: Aplikujem hard filter na adult filmy...")

    if adult_pref == "adult_only":
        df = df[df["adult"] == True]
    elif adult_pref == "non_adult_only":
        df = df[df["adult"] == False]

    if df.empty:
        if verbose:
            print("❗ Po filtroch neostal žiadny film.")
        return df

    # --- 4.2 fuzzy membershipy ---
    if verbose:
        print("🧮  Krok 3/5: Počítam fuzzy membership funkcie pre jednotlivé kritériá...")

    # 4.2.1 dĺžka – tri fuzzy sety
    # krátky: max ~ 90 min
    mu_short = mu_trap(df["runtime"], 0, 60, 90, 110)
    # stredný: okolo 100–120 min
    mu_medium = mu_trap(df["runtime"], 80, 100, 120, 140)
    # dlhý: 2+ hodiny
    mu_long = mu_trap(df["runtime"], 120, 140, 180, 260)

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

    # nové: cca 0–5 rokov
    mu_year_new = mu_trap(age, -1, 0, 3, 6)
    # staršie: 5–20 rokov
    mu_year_older = mu_trap(age, 4, 8, 15, 30)
    # retro: >20 rokov
    mu_year_retro = mu_trap(age, 20, 30, 60, 120)

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

    # --- filter na rating podľa počtu hodnotení ---
    # filmy s vote_count < 100 majú rating membership = 0
    has_enough_votes = df["vote_count"] >= 100

    mu_rating_excellent = np.where(has_enough_votes, mu_rating_excellent, 0.0)
    mu_rating_good = np.where(has_enough_votes, mu_rating_good, 0.0)
    mu_rating_average = np.where(has_enough_votes, mu_rating_average, 0.0)
    mu_rating_bad = np.where(has_enough_votes, mu_rating_bad, 0.0)

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
        mu_pop_unknown = np.zeros_like(pop, dtype=float)
        mu_pop_average = np.ones_like(pop, dtype=float)
        mu_pop_blockbuster = np.zeros_like(pop, dtype=float)
    else:
        q1 = float(pop.quantile(0.33))
        q2 = float(pop.quantile(0.66))

        # neznáme: skôr nízka popularita
        mu_pop_unknown = mu_trap(pop, pmin - 1, pmin, q1, q2)
        # priemerné: okolo stredu distribúcie
        mu_pop_average = mu_trap(pop, q1 * 0.8, q1, q2, q2 * 1.2)
        # blockbuster: horná tretina
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
    if verbose:
        print("⚖️  Krok 4/5: Nastavujem váhy pre jednotlivé kritériá...")

    # "surové" váhy podľa toho, či je kritérium zapnuté
    raw_w_len = 0.20 if length_pref != "none" else 0.05
    raw_w_year = 0.20 if year_pref != "none" else 0.05
    raw_w_rating = 0.25 if rating_pref != "none" else 0.05
    raw_w_pop = 0.20 if pop_pref != "none" else 0.05
    raw_w_lang = 0.15 if lang_pref != "none" else 0.0

    raw_weights = np.array([raw_w_len, raw_w_year, raw_w_rating, raw_w_pop, raw_w_lang], dtype=float)
    total_raw = raw_weights.sum()

    if total_raw == 0:
        raw_weights = np.array([0.2, 0.2, 0.2, 0.2, 0.2], dtype=float)
        total_raw = 1.0

    weights = raw_weights / total_raw
    w_len, w_year, w_rating, w_pop, w_lang = weights

    if verbose:
        print("   Surové váhy (pred normalizáciou):")
        print(f"     length   (dĺžka)    = {raw_w_len:.3f}")
        print(f"     year     (vek)      = {raw_w_year:.3f}")
        print(f"     rating   (rating)   = {raw_w_rating:.3f}")
        print(f"     pop      (popul.)   = {raw_w_pop:.3f}")
        print(f"     lang     (jazyk)    = {raw_w_lang:.3f}")
        print(f"     súčet               = {total_raw:.3f}\n")

        print("   Normalizované váhy (súčet = 1):")
        print(f"     w_length   = {w_len:.3f}")
        print(f"     w_year     = {w_year:.3f}")
        print(f"     w_rating   = {w_rating:.3f}")
        print(f"     w_popular  = {w_pop:.3f}")
        print(f"     w_language = {w_lang:.3f}\n")

    # finálne fuzzy skóre
    if verbose:
        print("🧩  Krok 5/5: Skladám fuzzy skóre pre každý film...")
        print("     fuzzy_score = w_len*μ_len_pref + w_year*μ_year_pref + "
              "w_rating*μ_rating_pref + w_pop*μ_pop_pref + w_lang*μ_lang\n")

    base_score = (
        w_len * mu_len_pref +
        w_year * mu_year_pref +
        w_rating * mu_rating_pref +
        w_pop * mu_pop_pref +
        w_lang * mu_lang
    )

    # uložíme si membershipy do DF (hodí sa na debug / prezentáciu)
    df["mu_len_pref"] = mu_len_pref
    df["mu_year_pref"] = mu_year_pref
    df["mu_rating_pref"] = mu_rating_pref
    df["mu_pop_pref"] = mu_pop_pref
    df["mu_lang"] = mu_lang
    df["fuzzy_score"] = base_score

    # hrubý filter – vyhoď úplne slabé filmy
    df = df[df["fuzzy_score"] > 0.2]

    if df.empty:
        if verbose:
            print("❗ Po výpočte fuzzy skóre neostal žiadny film s dostatočným skóre.")
        return df

    # zoradenie
    df = df.sort_values("fuzzy_score", ascending=False)

    cols = [
        "id", "title", "release_year", "runtime",
        "vote_average", "vote_count", "popularity",
        "spoken_languages", "original_language", "adult",
        "mu_len_pref", "mu_year_pref", "mu_rating_pref",
        "mu_pop_pref", "mu_lang", "fuzzy_score"
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


def _ask_adult_pref() -> str:
    """
    Adult filter:
      1 = len ne-adult (default)
      2 = len adult
      3 = všetko
    """
    raw = input(
        "Adult filter: [1] len ne-adult, [2] len adult, [3] všetko (Enter = 1): "
    ).strip()

    if raw == "2":
        return "adult_only"
    if raw == "3":
        return "none"
    return "non_adult_only"


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
    print("==============================================")
    print("🎬 Fuzzy vyhľadávač filmov (bez názvu, podľa pocitu)")
    print("==============================================\n")

    length_pref = _ask_length_pref()
    year_pref = _ask_year_pref()
    rating_pref = _ask_rating_pref()
    pop_pref = _ask_pop_pref()
    lang_pref = _ask_lang_pref()
    adult_pref = _ask_adult_pref()

    top_n = _ask_int("\nKoľko výsledkov chceš zobraziť? [20]: ", default=20)

    print("\n==============================================")
    print("🧠 Ako nad tým uvažujem (nastavené preferencie)")
    print("==============================================")

    print("➡️  Dĺžka filmu: ",
          {"short": "krátky", "medium": "stredný",
           "long": "dlhý", "none": "nezáleží"}[length_pref])

    print("➡️  Vek filmu: ",
          {"new": "nové (0–5 rokov)",
           "older": "staršie (5–20 rokov)",
           "retro": "retro (>20 rokov)",
           "none": "nezáleží"}[year_pref])

    print("➡️  Rating: ",
          {"excellent": "vynikajúce",
           "good": "dobré",
           "average": "priemerné",
           "bad": "zlé",
           "none": "nezáleží"}[rating_pref])

    print("➡️  Popularita: ",
          {"blockbuster": "blockbuster (veľmi populárne)",
           "average": "priemerná popularita",
           "unknown": "neznáme / low-pop",
           "none": "nezáleží"}[pop_pref])

    print("➡️  Jazyk: ",
          {"EN": "angličtina", "CZ": "čeština", "SK": "slovenčina",
           "ES": "španielčina", "DE": "nemčina",
           "none": "nezáleží"}[lang_pref])

    print("➡️  Adult filter: ",
          {"non_adult_only": "iba ne-adult filmy",
           "adult_only": "iba adult filmy",
           "none": "adult nefiltrujem"}[adult_pref])

    print("\n🔬 Fuzzy logika v skratke:")
    print("   - Dĺžka: tri fuzzy množiny (krátky, stredný, dlhý) cez trapezoidné funkcie")
    print("   - Vek: nové / staršie / retro podľa veku v rokoch")
    print("   - Rating: 4 fuzzy kategórie, ale len pre filmy s vote_count ≥ 100")
    print("   - Popularita: delenie na unknown / average / blockbuster podľa distribúcie v dátach")
    print("   - Jazyk: crisp logika (1 ak jazyk sedí, inak 0)")
    print("   - Výsledné skóre je vážený priemer týchto membershipov\n")

    print("🚀 Poďme na to! Výsledky dopočítam a vypíšem tabuľku najlepších kandidátov.\n")

    results = fuzzy_search(
        length_pref=length_pref,
        year_pref=year_pref,
        rating_pref=rating_pref,
        pop_pref=pop_pref,
        lang_pref=lang_pref,
        adult_pref=adult_pref,
        top_n=top_n,
        verbose=True,
    )

    pd.set_option("display.max_colwidth", 80)
    print("\n==============================================")
    print("📊 TOP výsledky podľa fuzzy skóre")
    print("==============================================\n")
    print(results)
