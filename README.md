# **Fuzzy Movie Search 🎥✨**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)]()
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-blue.svg)](https://www.postgresql.org/)
[![Kaggle Dataset](https://img.shields.io/badge/Data-Kaggle%20930k%20Movies-lightgrey.svg)](https://www.kaggle.com/datasets/asaniczka/tmdb-movies-dataset-2023-930k-movies)

---

## **📌 Overview**

**Fuzzy Movie Search** is a Python tool for searching movies using **fuzzy logic**, rather than binary filters.
Instead of “long movies only”, you get *how much* a movie matches your preference.

It loads movie metadata from a PostgreSQL database, evaluates fuzzy membership functions, and ranks movies by a final **fuzzy_score**.

Supports both:

* ✔ Interactive CLI
* ✔ Programmable API (import & call function)

---

## **🎬 Dataset**

This project uses the official public dataset:

**TMDB Movies Dataset 2023 (930k+ movies)**
🔗 [https://www.kaggle.com/datasets/asaniczka/tmdb-movies-dataset-2023-930k-movies](https://www.kaggle.com/datasets/asaniczka/tmdb-movies-dataset-2023-930k-movies)

Included fields:

* Title
* Runtime
* Release year
* Popularity
* Rating + vote count
* Languages
* Companies, countries, genres, etc.

You import the dataset into PostgreSQL and the tool fetches data using SQLAlchemy.

---

## **✨ Features**

| Category       | Options                            |
| -------------- | ---------------------------------- |
| **Length**     | short / medium / long              |
| **Movie Age**  | new / older / retro                |
| **Rating**     | excellent / good / average / bad   |
| **Popularity** | blockbuster / average / unknown    |
| **Language**   | EN, CZ, SK, ES, DE                 |
| **Other**      | weighted scoring, flexible filters |

Additional logic:

* Rejects movies with very low fuzzy_score
* Rejects movies with insufficient rating info (e.g., <100 votes)
* Normalizes weights only for enabled filters

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

### 2. Create `.env` file

```
DATABASE_URL=postgresql://user:password@host:port/database
```

Example:

```
DATABASE_URL=postgresql://myuser:mypass@ep-example.eu-central-1.aws.neon.tech/neondb
```

---

## **▶ Running the Search**

### **A) Interactive CLI**

Run:

```bash
python fuzzy_search.py
```

You will be asked for:

* movie length
* year
* rating
* popularity
* language
* number of results

And you get sorted results in your terminal.

---

### **B) Use it as a Python module**

```python
from fuzzy_search import fuzzy_search

df = fuzzy_search(
    length_pref="medium",
    year_pref="older",
    rating_pref="excellent",
    pop_pref="blockbuster",
    lang_pref="EN",
    top_n=15,
)

print(df)
```

Run:

```bash
python run_search.py
```

---

### **C) Optional: Create a shortcut**

#### macOS / Linux

```bash
echo 'alias fuzzy="python /path/to/project/fuzzy_search.py"' >> ~/.zshrc
source ~/.zshrc
```

#### Windows PowerShell

```powershell
Set-Alias fuzzy "python C:\path\to\project\fuzzy_search.py"
```

Then run:

```bash
fuzzy
```

---

## **🧠 How Fuzzy Logic Works (Short Version)**

We use **trapezoidal membership functions** like:

```
0 → rising edge → plateau → falling edge → 0
```

Example for "short movie":

```
0–60 min → rises
60–90 min → full membership
90–110 min → decreasing
```

Every category produces a membership value in **[0, 1]**.
All categories are weighted and combined into:

```
fuzzy_score = Σ weight_i * membership_i
```

Movies with extremely low match score (<0.2) are removed.

---

## **🛠 Requirements**

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

### **DATABASE_URL is not set**

Your `.env` is missing. Create one.

### **psycopg2 import errors**

```bash
pip install -r requirements.txt
```

### **High CPU / RAM**

Nothing runs automatically.
The fuzzy search only executes when you run the function.

---

## **📌 Quick Copy Snippet**

```
pip install -r requirements.txt
Create .env with DATABASE_URL
Run: python fuzzy_search.py
Dataset: Kaggle TMDB Movies 2023 (930k+ movies)
Supports fuzzy filters: length, year, rating, popularity, language
Outputs ranked results by fuzzy_score
```

---

## **📜 License**

MIT License — free to use, modify, and distribute.

