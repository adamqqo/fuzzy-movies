Below is a clean, copy-paste-ready **README document** written in English.
No bullshit, no fluff — formatted exactly like a proper GitHub README.

---

# **README – Fuzzy Movie Search**

## **Overview**

Fuzzy Movie Search is a lightweight Python tool for fuzzy-logic-based movie filtering.
It connects to a PostgreSQL database, loads movie metadata, applies fuzzy membership functions, computes a combined fuzzy score, and returns the top-ranked movies that match user preferences.

The project includes both an **interactive CLI** and a **callable Python API**.

---

## **Features**

* Fuzzy evaluation of:

  * **Movie length** → short / medium / long
  * **Movie age** → new / older / retro
  * **Rating** → excellent / good / average / bad
  * **Popularity** → blockbuster / average / unknown
* Language filter (EN, CZ, SK, ES, DE)
* Automatic weighting of selected criteria
* Top-N ranking based on `fuzzy_score`
* PostgreSQL connection via SQLAlchemy
* `.env`-based configuration

---

## **Project Structure**

```
project/
│
├── fuzzy_search.py
├── config.py
├── requirements.txt
└── .env   (you create this)
```

---

## **1. Installation**

### **Install dependencies**

```bash
pip install -r requirements.txt
```

Dependencies include:

* pandas
* numpy
* SQLAlchemy
* psycopg2-binary
* python-dotenv

---

## **2. Environment Setup**

Create a file named **`.env`** in the project root:

```
DATABASE_URL=postgresql://user:password@host:port/database
```

Example:

```
DATABASE_URL=postgresql://myuser:mypass@ep-example.eu-central-1.aws.neon.tech/neondb
```

`config.py` loads this automatically and raises an error if missing.

---

## **3. Running Fuzzy Search**

### **A) Interactive Mode (CLI)**

Run the script:

```bash
python fuzzy_search.py
```

It will ask for:

* length preference
* movie age
* rating
* popularity
* language
* number of results

Then prints the best fuzzy-matched movies.

---

### **B) Programmatic Usage (from another Python file)**

Create a file `run_search.py`:

```python
from fuzzy_search import fuzzy_search

df = fuzzy_search(
    length_pref="short",
    year_pref="new",
    rating_pref="excellent",
    pop_pref="blockbuster",
    lang_pref="EN",
    top_n=20,
)

print(df)
```

Run:

```bash
python run_search.py
```

---

### **C) Create a Shortcut (Alias)**

#### **macOS / Linux**

Add to `~/.bashrc` or `~/.zshrc`:

```bash
alias fuzzy="python /path/to/project/fuzzy_search.py"
```

#### **Windows PowerShell**

```powershell
Set-Alias fuzzy "python C:\path\to\project\fuzzy_search.py"
```

Then simply run:

```bash
fuzzy
```

---

## **4. Troubleshooting**

### **“DATABASE_URL is not set”**

Your `.env` file is missing or empty → create it.

### **psycopg2 import errors**

Reinstall dependencies:

```bash
pip install -r requirements.txt
```

### **High CPU / RAM usage**

In this version, nothing runs automatically on import —
the fuzzy logic executes **only when you call the function or run the script**.

---

## **5. Quick Summary (copy-ready snippet)**

```
pip install -r requirements.txt
Create .env with DATABASE_URL
Run interactively: python fuzzy_search.py
Or programmatically via: from fuzzy_search import fuzzy_search
Supports fuzzy filters for length, age, rating, popularity, language
Returns top-N results sorted by fuzzy_score
```

---
