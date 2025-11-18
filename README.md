# **Fuzzy Movie Search 🎥✨**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)]()
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-blue.svg)](https://www.postgresql.org/)
[![Kaggle Dataset](https://img.shields.io/badge/Data-Kaggle%20930k%20Movies-lightgrey.svg)](https://www.kaggle.com/datasets/asaniczka/tmdb-movies-dataset-2023-930k-movies)

---

## **📌 Overview**

**Fuzzy Movie Search** is a Python-based tool that ranks movies using **fuzzy logic** instead of rigid filters.
It evaluates how well each movie matches your preferences (length, year, rating, popularity, language), computes a **fuzzy score**, and returns the top results.

Works both as:

* ✔ Interactive CLI
* ✔ Importable Python module

---

## **🎬 Dataset**

This project uses the public dataset:

**TMDB Movies Dataset 2023 (930k+ movies)**
🔗 [https://www.kaggle.com/datasets/asaniczka/tmdb-movies-dataset-2023-930k-movies](https://www.kaggle.com/datasets/asaniczka/tmdb-movies-dataset-2023-930k-movies)

---

## **🌐 Public Read-Only Database Access**

For convenience and testing, a **publicly accessible read-only PostgreSQL database** is provided:

```
DATABASE_URL = jdbc:postgresql://ep-bitter-breeze-ago1woyt-pooler.c-2.eu-central-1.aws.neon.tech/neondb?user=reader&password=npg_AS4rd3XwVvoH&sslmode=require&channelBinding=require
```

This Neon database contains the full processed TMDB Movies dataset.

⚠ **Note:**

* This URL is *read-only*
* Safe for public use
* No risk of modification or deletion

You can copy this directly into `.env` (converted to standard SQLAlchemy format if needed).

---

## **✨ Features**

| Category             | Options                                                     |
| -------------------- | ----------------------------------------------------------- |
| **Length**           | short / medium / long                                       |
| **Movie Age**        | new / older / retro                                         |
| **Rating**           | excellent / good / average / bad                            |
| **Popularity**       | blockbuster / average / unknown                             |
| **Language Filters** | EN, CZ, SK, ES, DE                                          |
| **Other**            | weighted scoring, fuzzy normalization, vote-count filtering |

---

## **📁 Project Structure**

```
project/
│
├── fuzzy_search.py
├── config.py
├── requirements.txt
├── README.md
└── .env   (you create this)
```

---

## **⚙ Installation**

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Create `.env`

```
DATABASE_URL=postgresql://user:pass@host:port/db
```

Or use the **public read-only DB**:

```
DATABASE_URL=postgresql://reader:npg_AS4rd3XwVvoH@ep-bitter-breeze-ago1woyt-pooler.c-2.eu-central-1.aws.neon.tech/neondb?sslmode=require&channelBinding=require
```

(Identical to the JDBC version but usable by SQLAlchemy.)

---

## **▶ Running the Search**

### **A) Interactive CLI**

```bash
python fuzzy_search.py
```

You will be asked to choose:

* length
* year
* rating
* popularity
* language
* number of results

---

### **B) Use as a Python module**

```python
from fuzzy_search import fuzzy_search

df = fuzzy_search(
    length_pref="medium",
    year_pref="new",
    rating_pref="excellent",
    pop_pref="blockbuster",
    lang_pref="EN",
    top_n=10,
)

print(df)
```

---

### **C) Optional: create a shortcut**

#### macOS/Linux

```bash
alias fuzzy="python /path/to/project/fuzzy_search.py"
```

#### Windows PowerShell

```powershell
Set-Alias fuzzy "python C:\path\to\project\fuzzy_search.py"
```

---

## **🧠 Fuzzy Logic Explained (Short)**

Each category uses trapezoidal membership functions, e.g.:

```
short movie: 0–60 → rising, 60–90 → full, 90–110 → decreasing
```

Each preference returns values from **0.0 to 1.0**.
Weighted categories are combined:

```
fuzzy_score = Σ( weight_i × membership_i )
```

Movies with poor matches (score < 0.2) are removed.

---

## **📦 Requirements**

* Python 3.10+
* PostgreSQL 14+
* Libraries:

  * pandas
  * numpy
  * SQLAlchemy
  * psycopg2-binary
  * python-dotenv

---

## **❗ Troubleshooting**

### “DATABASE_URL is not set”

Create `.env`.

### psycopg2 errors

```bash
pip install -r requirements.txt
```

### Nothing happens / fuzzy doesn't run

The code executes **only when called** — not on import.

---

## **📌 Quick Copy Snippet**

```
pip install -r requirements.txt
Add .env with DATABASE_URL
Run: python fuzzy_search.py
Dataset: TMDB Movies 2023 (Kaggle, 930k+ movies)
Public DB available (read-only)
Fuzzy filters: length, year, rating, popularity, language
Returns ranked movies by fuzzy_score
```

---

## **📜 License**

MIT License.

