import json

# Analyze capture_0 (the model/exploration)
with open('capture_0.json', encoding='utf-8') as f:
    data = json.load(f)

print('Top keys:', list(data.keys())[:10])

models = data.get('models', [])
print(f'Num models: {len(models)}')

if models:
    m = models[0]
    print(f'Model keys: {list(m.keys())}')
    tables = m.get('tables', [])
    print(f'Num tables: {len(tables)}')
    for t in tables:
        cols = t.get('columns', [])
        measures = t.get('measures', [])
        print(f"\n  Table '{t.get('name')}': {len(cols)} cols, {len(measures)} measures")
        for c in cols[:8]:
            print(f"    Col: {c.get('name')} ({c.get('dataType')})")
        for me in measures[:5]:
            print(f"    Measure: {me.get('name')}")

# Analyze capture_1 (first querydata response)
print("\n\n=== CAPTURE 1 (querydata) ===")
with open('capture_1.json', encoding='utf-8') as f:
    data1 = json.load(f)

print(f'Top keys: {list(data1.keys())}')
if 'results' in data1:
    for i, r in enumerate(data1['results'][:3]):
        print(f'\nResult {i}:')
        result = r.get('result', {})
        d = result.get('data', {})
        dsr = d.get('dsr', {})
        ds = dsr.get('DS', [])
        print(f'  DS count: {len(ds)}')
        if ds:
            ds0 = ds[0]
            print(f'  DS[0] keys: {list(ds0.keys())}')
            vd = ds0.get('ValueDicts', {})
            print(f'  ValueDicts keys: {list(vd.keys())}')
            for k, vals in vd.items():
                print(f'    {k}: (len={len(vals)}) first 5={vals[:5]}')
            ph = ds0.get('PH', [])
            print(f'  PH count: {len(ph)}')
            if ph:
                print(f'  PH[0] keys: {list(ph[0].keys())}')
                dm0 = ph[0].get('DM0', [])
                print(f'  DM0 row count: {len(dm0)}')
                for row in dm0[:5]:
                    print(f'    Row: {json.dumps(row, ensure_ascii=False)[:200]}')

# Try a bigger capture
print("\n\n=== CAPTURE 27 (large querydata) ===")
with open('capture_27.json', encoding='utf-8') as f:
    data27 = json.load(f)

if 'results' in data27:
    for i, r in enumerate(data27['results'][:2]):
        result = r.get('result', {})
        d = result.get('data', {})
        dsr = d.get('dsr', {})
        ds = dsr.get('DS', [])
        if ds:
            ds0 = ds[0]
            vd = ds0.get('ValueDicts', {})
            print(f'  ValueDicts keys: {list(vd.keys())}')
            for k, vals in vd.items():
                print(f'    {k}: (len={len(vals)}) first 10={vals[:10]}')
            ph = ds0.get('PH', [])
            if ph:
                dm0 = ph[0].get('DM0', [])
                print(f'  DM0 row count: {len(dm0)}')
                for row in dm0[:10]:
                    print(f'    Row: {json.dumps(row, ensure_ascii=False)[:300]}')
