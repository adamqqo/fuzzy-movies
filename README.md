# **Fuzzy Movie Search 🎥✨**

*(This README was written with assistance from AI.)*

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)]()
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-blue.svg)]()
[![License](https://img.shields.io/badge/License-MIT-green.svg)]()
[![Dataset](https://img.shields.io/badge/Dataset-TMDB%20930k%20Movies-blue.svg)](https://www.kaggle.com/datasets/asaniczka/tmdb-movies-dataset-2023-930k-movies)

---

## 📌 Overview

Fuzzy Movie Search is a Python tool that ranks movies using **fuzzy logic**, which evaluates *how well* each film matches your preferences instead of filtering them strictly.

For example:

* A 95-minute movie can still partially fit “short.”
* A 2012 movie can be “somewhat older.”
* A film with high popularity and good rating contributes more to the final score.

This approach gives **smoother, more intuitive search results** than classic filtering.

The tool supports:

* interactive CLI mode
* programmatic usage in Python

---

## 🎬 Dataset

The tool uses the following public movie dataset:

**TMDB Movies Dataset 2023 (930,000+ movies)**
🔗 [https://www.kaggle.com/datasets/asaniczka/tmdb-movies-dataset-2023-930k-movies](https://www.kaggle.com/datasets/asaniczka/tmdb-movies-dataset-2023-930k-movies)

---

## 🌐 Public Read-Only Database

A public PostgreSQL Neon database is available for testing:

```
jdbc:postgresql://ep-bitter-breeze-ago1woyt-pooler.c-2.eu-central-1.aws.neon.tech/neondb?user=reader&password=npg_AS4rd3XwVvoH&sslmode=require&channelBinding=require
```

SQLAlchemy-compatible version:

```
postgresql://reader:npg_AS4rd3XwVvoH@ep-bitter-breeze-ago1woyt-pooler.c-2.eu-central-1.aws.neon.tech/neondb?sslmode=require&channelBinding=require
```

This database includes:

* titles
* runtimes
* release years
* ratings (vote_average, vote_count)
* popularity
* languages
* adult flag

---

# 🧠 How the Fuzzy System Works

The search engine evaluates each movie using several **fuzzy categories**.
Each category produces a score from **0.0 to 1.0**, representing how well the movie matches your preference.

The final result is a weighted combination of these scores : 

```
fuzzy_score =
    w_length * length_match +
    w_age    * age_match +
    w_rating * rating_match +
    w_pop    * popularity_match +
    w_lang   * language_match
```

Movies with very low scores (<0.2) are removed, and the rest are sorted from best to worst.

---

# 📁 Project Structure

```
project/
├── fuzzy_search.py
├── config.py
├── requirements.txt
└── README.md
```

---

# ⚙ Installation

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Create `.env`

```
DATABASE_URL=postgresql://reader:npg_AS4rd3XwVvoH@ep-bitter-breeze-ago1woyt-pooler.c-2.eu-central-1.aws.neon.tech/neondb?sslmode=require
```

---

# ▶ How to Use

## A) CLI Mode

Run:

```bash
python fuzzy_search.py
```

The script will ask you:

* preferred length
* age
* rating
* popularity
* language
* adult filter
* number of results

Results will be printed as a table.

---

## B) Use from Python

```python
from fuzzy_search import fuzzy_search

df = fuzzy_search(
    length_pref="medium",
    year_pref="new",
    rating_pref="excellent",
    pop_pref="average",
    lang_pref="EN",
    top_n=20,
)

print(df)
```

---

## C) Create a Shortcut (Optional)

Linux/macOS:

```bash
alias fuzzy="python /path/to/fuzzy_search.py"
```

Windows PowerShell:

```powershell
Set-Alias fuzzy "python C:\path\to\fuzzy_search.py"
```

---

# ❗ Troubleshooting

### “DATABASE_URL is not set”

Add it to `.env`.

### “Cannot connect to database”

Ensure:

```
?sslmode=require
```

### Empty results

Some combinations are too strict.
Try loosening preferences.

