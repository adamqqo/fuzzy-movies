# **Fuzzy Movie Search 🎥✨**

*(Tento README bol vytvorený s pomocou AI.)*

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)]()
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-blue.svg)]()
[![License](https://img.shields.io/badge/License-MIT-green.svg)]()
[![Dataset](https://img.shields.io/badge/Dataset-TMDB%20930k%20Movies-blue.svg)](https://www.kaggle.com/datasets/asaniczka/tmdb-movies-dataset-2023-930k-movies)

---

## 📌 Prehľad

Fuzzy Movie Search je Python nástroj, ktorý hodnotí filmy pomocou **fuzzy logiky** – teda podľa toho, *ako veľmi* film zodpovedá tvojim preferenciám, nie iba či-zodpovedá/ne-zodpovedá.

Príklady:

* 95-minútový film môže byť čiastočne „krátky“.
* Film z roku 2012 môže byť „trochu starší“.
* Film s vysokou popularitou a dobrým hodnotením prispieva viac k celkovému skóre.

Výsledkom je **plynulejšie a intuitívnejšie vyhľadávanie** než pri klasických filtroch.

Nástroj podporuje:

* interaktívny CLI režim
* programové použitie v Pythone

---

## 🎬 Dataset

Nástroj používa tento verejný dataset filmov:

**TMDB Movies Dataset 2023 (930 000+ filmov)**
🔗 [https://www.kaggle.com/datasets/asaniczka/tmdb-movies-dataset-2023-930k-movies](https://www.kaggle.com/datasets/asaniczka/tmdb-movies-dataset-2023-930k-movies)

---

## 🌐 Verejná read-only databáza

Pre testovanie je dostupná verejná PostgreSQL Neon databáza:

```
jdbc:postgresql://ep-bitter-breeze-ago1woyt-pooler.c-2.eu-central-1.aws.neon.tech/neondb?user=reader&password=npg_AS4rd3XwVvoH&sslmode=require&channelBinding=require
```

Verzia kompatibilná so SQLAlchemy:

```
postgresql://reader:npg_AS4rd3XwVvoH@ep-bitter-breeze-ago1woyt-pooler.c-2.eu-central-1.aws.neon.tech/neondb?sslmode=require&channelBinding=require
```

Databáza obsahuje:

* názvy filmov
* dĺžku
* rok vydania
* hodnotenie (vote_average, vote_count)
* popularitu
* jazyky
* adult príznak

---

# 🧠 Ako funguje fuzzy systém

Vyhľadávač hodnotí každý film v niekoľkých **fuzzy kategóriách**.
Každá kategória dáva skóre od **0.0 do 1.0**, teda mieru zhody s požiadavkou.

Finálne skóre je vážený priemer týchto hodnôt.

Nižšie je jednoduché vysvetlenie každého komponentu:

---

## 1️⃣ Dĺžka filmu (short / medium / long)

Dĺžka nie je prah „pod/na/za“.

Príklady:

* 70 min → silne „krátky“
* 95 min → čiastočne „krátky“
* 150 min → výrazne „dlhý“

Používajú sa plynulé trapezoidné krivky, takže kategórie na seba prirodzene nadväzujú.

---

## 2️⃣ Vek filmu (new / older / retro)

Namiesto „po roku 2020“ sa používa **vek filmu**:

* **new:** 0–5 rokov
* **older:** 5–20 rokov
* **retro:** 20+ rokov

Film môže zapadať do dvoch kategórií zároveň (napr. 7-ročný → „trochu nový“ & „trochu starší“).

---

## 3️⃣ Rating (excellent / good / average / bad)

Hodnotenia sú rozdelené do štyroch fuzzy kategórií:

* excellent: 8.5+
* good: okolo 7
* average: okolo 5.5
* bad: pod ~5

A navyše:
**Filmy s menej ako 100 hlasmi nedostanú rating skóre**
(pretože ich rating je nespoľahlivý).

---

## 4️⃣ Popularita (unknown / average / blockbuster)

Popularita sa líši dataset od datasetu, preto sa počíta automaticky.

Používajú sa percentile:

* nízka popularita
* priemerný rozsah
* top populárne filmy

Tým pádom sa kategórie prispôsobia konkrétnemu datasetu.

---

## 5️⃣ Jazyk

Jazyk sa hodnotí jednoducho:

Ak preferuješ EN:

* ak film obsahuje „en“ → 1.0
* inak → 0.0

Jazyky nemajú „stupne“, preto je to úmyselne crisp logika.

---

## 6️⃣ Adult filter

Aplikuje sa *pred* fuzzy logikou:

* iba ne-adult filmy
* iba adult filmy
* všetko

Výsledok je predvídateľný a bezpečný.

---

## 7️⃣ Váhovanie preferencií

Nie všetky preferencie sú rovnako dôležité.

* ak používateľ nastaví preferenciu → dostane vyššiu váhu
* ak ju nechá prázdnu → nízka váha

Váhy sa normalizujú tak, aby dávali **súčet 1.0**.

---

## 8️⃣ Finálne skóre

Každý film dostane finálne skóre:

```
fuzzy_score =
    w_length * length_match +
    w_age    * age_match +
    w_rating * rating_match +
    w_pop    * popularity_match +
    w_lang   * language_match
```

Filmy so skóre < 0.2 sú odstránené.
Zvyšné sú zoradené od najlepších po najhoršie.

---

# 📁 Štruktúra projektu

```
project/
├── fuzzy_search.py
├── config.py
├── requirements.txt
└── README.md
```

---

# ⚙ Inštalácia

### 1. Nainštaluj závislosti

```bash
pip install -r requirements.txt
```

### 2. Vytvor `.env`

```
DATABASE_URL=postgresql://reader:npg_AS4rd3XwVvoH@ep-bitter-breeze-ago1woyt-pooler.c-2.eu-central-1.aws.neon.tech/neondb?sslmode=require
```

---

# ▶ Ako používať

## A) CLI režim

Spusti:

```bash
python fuzzy_search.py
```

Skript sa opýta na:

* preferovanú dĺžku
* vek
* rating
* popularitu
* jazyk
* adult filter
* počet výsledkov

Výsledok sa vypíše ako tabuľka.

---

## B) Použitie v Pythone

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

## C) Alias (voliteľné)

Linux/macOS:

```bash
alias fuzzy="python /path/to/fuzzy_search.py"
```

Windows PowerShell:

```powershell
Set-Alias fuzzy "python C:\path\to\fuzzy_search.py"
```

---

# ❗ Riešenie problémov

### “DATABASE_URL is not set”

Pridaj ho do `.env`.

### „Cannot connect to database“

Uisti sa, že URL obsahuje:

```
?sslmode=require
```

### Prázdne výsledky

Niektoré kombinácie sú príliš prísne.
Skús uvoľniť preferencie.

---

# 📜 Licencia

MIT License.

