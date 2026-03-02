"""Parse capture_33 precisely - the main employment time series data."""
import json

with open('capture_33.json', encoding='utf-8') as f:
    d = json.load(f)

ds = d['results'][0]['result']['data']['dsr']['DS'][0]
vd = ds.get('ValueDicts', {})
years = vd.get('D0', [])
dates = vd.get('D1', [])
dm0 = ds['PH'][0]['DM0']

print(f"Years: {years}")
print(f"Dates: {dates[:5]}...{dates[-3:]}")
print(f"Rows: {len(dm0)}")
print()

# In Power BI DSR format:
# - First row has 'S' (schema): defines column names (G0, G1, ...) and measures (M0, M1, ...)
# - 'C' array: values for columns (indices into ValueDicts if DN is defined, or direct values)
# - 'R' bitmask: which columns REPEAT from previous row (1=G0, 2=G1, 4=G2, etc.)
# - 'X' array: extension data (measures not in C)
# - 'M0' in X: the actual employment value

# First understand the schema from row 0
schema = dm0[0].get('S', [])
print(f"Schema: {json.dumps(schema, ensure_ascii=False)}")
# [{"N": "G0", "T": 1, "DN": "D0"}, {"N": "G1", "T": 1, "DN": "D1"}, {"N": "M0", "T": 4}]
# G0 = year index (into D0), G1 = date index (into D1), M0 = employment count

# Parse all rows
prev = {}
results = []

for row in dm0:
    c = row.get('C', [])
    r = row.get('R', 0)
    
    # Figure out how many group columns vs measure columns are in C
    # Schema tells us: G0 (DN: D0), G1 (DN: D1), M0 (type 4 = number)
    # The C array contains values for G0, G1, M0 in order
    # When R bitmask is set, those columns repeat from previous row
    
    # Determine which positions in C correspond to which schema elements
    # R bitmask: bit 0 = col 0 repeats, bit 1 = col 1 repeats, etc.
    
    curr = dict(prev)  # start from previous values
    
    c_idx = 0
    for si, s in enumerate(schema if 'S' in row else schema):
        bit = 1 << si
        if r & bit:
            # This column repeats from previous
            pass
        else:
            # This column has a new value in C
            if c_idx < len(c):
                curr[s['N']] = c[c_idx]
                c_idx += 1
    
    # Check X for measures
    x = row.get('X', None)
    if x and isinstance(x, list):
        for xitem in x:
            if isinstance(xitem, dict):
                for k, v in xitem.items():
                    if k != 'S':
                        curr[k] = v
    
    prev = dict(curr)
    
    # Resolve ValueDicts
    year_idx = curr.get('G0', 0)  
    date_idx = curr.get('G1', 0)
    empleo = curr.get('M0', None)
    
    year = years[year_idx] if isinstance(year_idx, int) and year_idx < len(years) else str(year_idx)
    date = dates[date_idx] if isinstance(date_idx, int) and date_idx < len(dates) else str(date_idx)
    
    results.append({'año': year, 'fecha': date, 'empleo': empleo})
    print(f"  {year} | {date:12s} | {empleo:>12,}" if empleo else f"  {year} | {date:12s} | None")

print(f"\nTotal: {len(results)} rows")

# Also check capture_27 (which has X format for measures)
print("\n\n=== capture_27 ===")
with open('capture_27.json', encoding='utf-8') as f:
    d27 = json.load(f)

ds27 = d27['results'][0]['result']['data']['dsr']['DS'][0]
vd27 = ds27.get('ValueDicts', {})
dm0_27 = ds27['PH'][0]['DM0']
schema27 = dm0_27[0].get('S', [])
print(f"Schema: {json.dumps(schema27, ensure_ascii=False)}")
print(f"First 3 rows:")
for row in dm0_27[:3]:
    print(f"  {json.dumps(row, ensure_ascii=False)[:300]}")
