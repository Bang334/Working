# -*- coding: utf-8 -*-
"""
Script to import the cleaned sample dataset into SQLite database project_receivables table.
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import get_db_connection
from app.services.receivables_service import create_receivable

SAMPLE_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app", "data", "receivables_sample_data.json")

def load_sample_data_into_db(clear_existing=True):
    if not os.path.exists(SAMPLE_JSON_PATH):
        print(f"Error: {SAMPLE_JSON_PATH} not found.")
        return 0

    with open(SAMPLE_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("receivables", [])
    if not items:
        print("No items in sample JSON.")
        return 0

    conn = get_db_connection()
    cursor = conn.cursor()

    if clear_existing:
        cursor.execute("DELETE FROM project_receivables")
        cursor.execute("DELETE FROM receivables_weekly_snapshots")
        conn.commit()
        print("Cleared existing project_receivables and snapshots.")

    conn.close()

    inserted = 0
    for it in items:
        create_receivable(it)
        inserted += 1

    print(f"Successfully loaded {inserted} cleaned sample records into project_receivables.")
    return inserted

if __name__ == "__main__":
    load_sample_data_into_db(clear_existing=True)
