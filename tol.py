import httpx

API_KEY = "737de0fb36b92ed396ea117066b9c250"
DOMAIN_ID = 1597430
START_DATE = "2025-05-01"
END_DATE = "2025-05-22"

headers = {
    "X-API-Key": API_KEY,
    "Accept": "application/json"
}

# Ambil placements dulu
url_placements = f"https://api3.adsterratools.com/publisher/domain/{DOMAIN_ID}/placements.json"
resp_placements = httpx.get(url_placements, headers=headers)
placements = resp_placements.json().get("items", [])
print(f"Total placements: {len(placements)}")

# Ambil report domain (tanpa placement_id)
url_report = "https://api3.adsterratools.com/publisher/report.json"
params = {
    "domain_id": DOMAIN_ID,
    "start_date": START_DATE,
    "end_date": END_DATE
}

resp_report = httpx.get(url_report, headers=headers, params=params)
print("Report status:", resp_report.status_code)
report_data = resp_report.json()
print(report_data)

# Contoh filter data report berdasarkan placement id (kalau struktur data memungkinkan)
# Misal report_data ada field 'items' yang tiap item punya 'placement_id'
# filtered_by_placement = {p['id']: [] for p in placements}
# for item in report_data.get("items", []):
#     pid = item.get("placement_id")
#     if pid in filtered_by_placement:
#         filtered_by_placement[pid].append(item)
