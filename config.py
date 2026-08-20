import os

# Render'da "Environment" bo'limiga qo'shiladigan qiymatlar
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
PORT = int(os.getenv("PORT", "10000"))

# Boshlang'ich admin(lar). Keyin bot paneldan qo'shish/o'chirish mumkin.
# ADMIN_ID=123   yoki   ADMIN_IDS=123,456,789
def _parse_admin_ids():
    raw = (os.getenv("ADMIN_IDS") or os.getenv("ADMIN_ID") or "").strip()
    ids = []
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if part.isdigit():
            ids.append(int(part))
    return ids

SEED_ADMIN_IDS = _parse_admin_ids()
# Eski kod bilan moslik
ADMIN_ID = SEED_ADMIN_IDS[0] if SEED_ADMIN_IDS else 0
