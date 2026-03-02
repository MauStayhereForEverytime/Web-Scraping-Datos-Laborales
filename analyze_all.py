import json, os, glob

# Scan ALL capture files to find the ones with employment data
files = sorted(glob.glob('capture_*.json'), key=lambda f: int(f.split('_')[1].split('.')[0]))

for fname in files:
    with open(fname, encoding='utf-8') as f:
        data = json.load(f)
    
    # Skip the model file  
    if 'models' in data:
        print(f"\n{'='*60}")
        print(f"{fname}: MODEL/EXPLORATION (skip)")
        continue
    
    if 'results' not in data:
        print(f"\n{fname}: No 'results' key")
        continue
        
    for ri, r in enumerate(data['results']):
        result = r.get('result', {})
        d = result.get('data', {})
        dsr = d.get('dsr', {})
        ds = dsr.get('DS', [])
        
        for di, ds_item in enumerate(ds):
            vd = ds_item.get('ValueDicts', {})
            ph = ds_item.get('PH', [])
            dm0_count = sum(len(ph_item.get('DM0', [])) for ph_item in ph)
            
            # Get first row schema
            schema = ""
            first_row = ""
            for ph_item in ph:
                dm0 = ph_item.get('DM0', [])
                if dm0:
                    row0 = dm0[0]
                    if 'S' in row0:
                        schema = str([(s.get('N','?'), s.get('T','?'), s.get('DN','')) for s in row0['S']])
                    first_row = json.dumps(row0, ensure_ascii=False)[:200]
                    break
            
            vd_summary = {k: f"len={len(v)}, first={v[:3]}" for k, v in vd.items()}
            
            if dm0_count > 0:
                print(f"\n{'='*60}")
                print(f"{fname} result[{ri}] DS[{di}]:")
                print(f"  DM0 rows: {dm0_count}")
                print(f"  ValueDicts: {vd_summary}")
                print(f"  Schema: {schema}")
                print(f"  First row: {first_row}")
                
                # Check if there are month-year patterns in ValueDicts
                for k, v in vd.items():
                    if any('-' in str(x) for x in v[:5]):
                        print(f"  *** HAS DATE DATA in {k}: {v[:5]}")
                    if any(x in str(v).lower() for x in ['lima', 'arequipa', 'cusco', 'piura']):
                        print(f"  *** HAS REGION DATA in {k}: {v[:5]}...")
