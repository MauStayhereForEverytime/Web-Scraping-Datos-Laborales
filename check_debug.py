import json, os, glob

files = sorted(glob.glob("debug_resp_*.json"))
for f in files:
    d = json.load(open(f, encoding="utf-8"))
    results = d.get("results", [])
    for ri, r in enumerate(results):
        ds_list = r.get("result", {}).get("data", {}).get("dsr", {}).get("DS", [])
        for di, ds in enumerate(ds_list):
            vd = ds.get("ValueDicts", {})
            ph_list = ds.get("PH", [])
            dm0_count = sum(len(ph.get("DM0", [])) for ph in ph_list)
            vd_summary = {k: f"len={len(v)}, first={v[:3]}" for k, v in vd.items()}
            first_row = None
            if ph_list and ph_list[0].get("DM0"):
                first_row = ph_list[0]["DM0"][0]
            print(f"{os.path.basename(f)} r[{ri}] DS[{di}]: DM0={dm0_count}, VD={vd_summary}")
            if first_row:
                print(f"  first={json.dumps(first_row, ensure_ascii=False)[:250]}")
