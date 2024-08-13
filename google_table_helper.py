import json
import os
from pathlib import Path

import gspread
from dotenv import load_dotenv

# Load dotenv (config from .env file)
load_dotenv()

# Create var with absolute path
absolute_path = Path("main.py")

# File with cred for Google Sheets
GOOGLE_JSON = os.path.join(absolute_path.parent.absolute(), "fiverr-business-368713-69cb80e5acdb.json")

gc = gspread.service_account(GOOGLE_JSON)

# Open a sheet from a spreadsheet in one go
wks = gc.open(os.getenv("GOOGLE_TABLE_NAME")).sheet1

recwhole = gc.open(os.getenv("GOOGLE_TABLE_NAME")).get_worksheet(2)


def purge_cache_google_tabel_and_update():
    payments = wks.get_values(os.getenv("GOOGLE_TABLE_SHEET_AREA"))

    open("SheetLiveCache.json", "w+").write(
        json.dumps(payments, indent=1)
    )

    return payments


def google_table_get_message_templates() -> any:
    """

    :rtype: str[][]
    """
    # Loading templates from Google Sheets
    templates = gc.open(os.getenv("GOOGLE_TABLE_NAME")).get_worksheet(1).get_all_values()

    return templates


def read_local_json_cache():
    """

   :rtype: [str, str][][]
   """
    users_in_expire_table = []

    if os.path.isfile("SheetLiveCache.json"):
        users_in_expire_table = json.loads(open("SheetLiveCache.json", "r+").read())

    return users_in_expire_table