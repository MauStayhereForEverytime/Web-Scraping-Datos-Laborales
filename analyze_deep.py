"""
Deep analysis of capture_26 (timestamps from 2016+) and capture_33 (dates 2022+)
to understand how to extract the full time series.
"""
import json

# === capture_26: timestamps from 2016 ===
print("=== capture_26 (timestamps) ===")
with open('capture_26.json', encoding='utf-8') as f:
    d26 = json.load(f)

r = d26['results'][0]['result']['data']['dsr']['DS'][0]
dm0 = r['PH'][0]['DM0']
print(f"Rows: {len(dm0)}")
# Convert timestamps
from datetime import datetime
for row in dm0[:5]:
    ts = row.get('G0', row.get('C', [None])[0] if 'C' in row else None)
    if isinstance(ts, (int, float)):
        dt = datetime.utcfromtimestamp(ts / 1000)
        print(f"  ts={ts} → {dt.strftime('%Y-%m-%d')}")
    else:
        print(f"  raw: {json.dumps(row, ensure_ascii=False)[:200]}")

print("...")
for row in dm0[-5:]:
    ts = row.get('G0', row.get('C', [None])[0] if 'C' in row else None)
    if isinstance(ts, (int, float)):
        dt = datetime.utcfromtimestamp(ts / 1000)
        print(f"  ts={ts} → {dt.strftime('%Y-%m-%d')}")
    else:
        print(f"  raw: {json.dumps(row, ensure_ascii=False)[:200]}")


# === capture_38: timestamps (longer range) ===
print("\n=== capture_38 (timestamps) ===")
with open('capture_38.json', encoding='utf-8') as f:
    d38 = json.load(f)

r38 = d38['results'][0]['result']['data']['dsr']['DS'][0]
dm38 = r38['PH'][0]['DM0']
print(f"Rows: {len(dm38)}")
for row in dm38[:5]:
    ts = row.get('G0', row.get('C', [None])[0] if 'C' in row else None)
    if isinstance(ts, (int, float)):
        dt = datetime.utcfromtimestamp(ts / 1000)
        print(f"  ts={ts} → {dt.strftime('%Y-%m-%d')}")
    else:
        print(f"  raw: {json.dumps(row, ensure_ascii=False)[:200]}")
print("...")
for row in dm38[-5:]:
    ts = row.get('G0', row.get('C', [None])[0] if 'C' in row else None)
    if isinstance(ts, (int, float)):
        dt = datetime.utcfromtimestamp(ts / 1000)
        print(f"  ts={ts} → {dt.strftime('%Y-%m-%d')}")
    else:
        print(f"  raw: {json.dumps(row, ensure_ascii=False)[:200]}")


# === capture_33: date strings with employment data ===
print("\n=== capture_33 result[0] (date strings + employment) ===")
with open('capture_33.json', encoding='utf-8') as f:
    d33 = json.load(f)

r33 = d33['results'][0]['result']['data']['dsr']['DS'][0]
vd = r33.get('ValueDicts', {})
print(f"ValueDicts D0 (years): {vd.get('D0', [])}")
print(f"ValueDicts D1 (dates): {vd.get('D1', [])}")

dm33 = r33['PH'][0]['DM0']
print(f"\nDM0 rows: {len(dm33)}")
# Parse ALL rows with carry-forward logic
last_c = [None, None]
for row in dm33:
    schema = row.get('S', None)
    c = row.get('C', [])
    r_flag = row.get('R', 0)  # R = repeat mask
    x = row.get('X', [{}])
    
    # Update carries
    if c:
        for i, val in enumerate(c):
            last_c[i] = val
    
    # R flag tells which columns repeat from previous row
    # R=1 means col 0 repeats, R=2 means col 1 repeats, R=3 means both repeat
    
    # Get indices
    c0 = c[0] if len(c) > 0 else last_c[0]
    c1 = c[1] if len(c) > 1 else last_c[1]
    
    # If R flag, the missing columns repeat from previous
    if r_flag:
        if r_flag & 1:  # bit 0 set = col 0 repeats
            c0 = last_c[0]
        if r_flag & 2:  # bit 1 set = col 1 repeats
            c1 = last_c[1]
    
    # Resolve via ValueDicts
    year = vd['D0'][c0] if c0 is not None and c0 < len(vd.get('D0', [])) else '?'
    date_str = vd['D1'][c1] if c1 is not None and c1 < len(vd.get('D1', [])) else '?'
    
    # Get measure
    empleo = None
    if x and isinstance(x, list) and x[0]:
        empleo = x[0].get('M0', None)
    elif 'M0' in row.get('C', [None, None, None]).__class__.__name__:
        pass
    # For capture_33 format: C has [year_idx, date_idx, empleo_value]
    if len(c) >= 3:
        empleo = c[2]
    
    # Update last_c for next iteration
    if c:
        for i, val in enumerate(c):
            last_c[i] = val
    
    print(f"  year={year}, date={date_str}, empleo={empleo}, raw_C={c}, R={r_flag}")
