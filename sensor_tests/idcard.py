from _project_path import ensure_project_root

ensure_project_root()

from lib.thaiidcard.card import ThaiIDCard

try:

    card = ThaiIDCard()

    info = card.read()

    print("=" * 50)
    print("CID      :", info.cid)
    print("TH NAME  :", info.th_name)
    print("EN NAME  :", info.en_name)
    print("BIRTH    :", info.birth_date)
    print("ADDRESS  :", info.address)
    print("=" * 50)

except Exception as e:

    print("ERROR:", e)
