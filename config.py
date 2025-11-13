# config.py
import os
from dotenv import load_dotenv

# načíta .env súbor (ak existuje)
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL nie je nastavené. "
        "Nastav ho v .env alebo v systémových env premenných."
    )
