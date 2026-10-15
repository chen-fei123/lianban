# -*- coding: utf-8 -*-
"""
每日自动更新脚本：拉涨停池+竞价数据 -> 生成HTML -> 自动发布
Windows定时任务每天9:26运行
"""
import urllib.request, json, os, sys, subprocess
from datetime import datetime, timedelta
from collections import defaultdict

OUT = os.path.dirname(os.path.abspath(__file__))
HTML_PATH = os.path.join(OUT, "连板梯队.html")
APP_ID = "app_17g3rnjdt7g"
ZT_API = "http://push2ex.eastmoney.com/getTopicZTPool?ut=7eea3edcaed734bea9cbfc24409ed989&dpt=wz.ztzt&Pageindex=0&pagesize=500&sort=fbt:asc&date={date}"

BABY = {
    "14":"生气","41":"生气","67":"生气","76":"生气","39":"生气","93":"生气","28":"生气","82":"生气",
    "19":"延年","91":"延年","78":"延年","87":"延年","34":"延年","43":"延年","26":"延年","62":"延年",
    "13":"天医","31":"天医","68":"天医","86":"天医","49":"天医","94":"天医","27":"天医","72":"天医",
    "11":"伏位","22":"伏位","88":"伏位","99":"伏位","66":"伏位","77":"伏位","33":"伏位","44":"伏位",
    "12":"绝命","21":"绝命","69":"绝命","96":"绝命","48":"绝命","84":"绝命","37":"绝命","73":"绝命",
    "17":"祸害","71":"祸害","89":"祸害","98":"祸害","46":"祸害","64":"祸害","23":"祸害","32":"祸害",
    "16":"六煞","61":"六煞","47":"六煞","74":"六煞","38":"六煞","83":"六煞","29":"六煞","92":"六煞",
    "18":"五鬼","81":"五鬼","79":"五鬼","97":"五鬼","36":"五鬼","63":"五鬼","24":"五鬼","42":"五鬼",
}
AUSPICIOUS = {"生气","延年","天医","伏位"}

def baby_counts(code):
    c = defaultdict(int)
    for i in range(len(code)-1):
        p = code[i:i+2]
        if p[0]=="0": continue
        t = BABY.get(p)
        if t: c[t]+=1
    return c

def baby_tags(code):
    c = baby_counts(code)
    return [n if c[n]==1 else f"{n}×{c[n]}" for n in ["生气","延年","天医","伏位","绝命","祸害","六煞","五鬼"] if c[n]>0]

def judge(code):
    c = baby_counts(code)
    ji = sum(c[k] for k in AUSPICIOUS)
    xiong = sum(v for k,v in c.items() if k not in AUSPICIOUS)
    return "good" if ji>xiong else ("bad" if xiong>ji else "neutral")

def market_of(code):
    if code.startswith("60"): return "沪主板"
    if code.startswith(("000","001","002","003")): return "深主板"
    if code.startswith(("300","301")): return "创业板"
    if code.startswith("688"): return "科创板"
    return "北交所"

def fetch_zt(date_str):
    url = ZT_API.format(date=date_str)
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.loads(r.read().decode())
        return d.get("data",{}).get("pool",[]) if d.get("data") else []
    except: return []

def fetch_quotes(codes):
    result = {}
    for i in range(0, len(codes), 20):
        batch = codes[i:i+20]
        q = ",".join(("sh" if c.startswith("60") else "sz")+c for c in batch)
        url = f"http://qt.gtimg.cn/q={q}"
        req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0","Referer":"http://gu.qq.com/"})
        try:
            raw = urllib.request.urlopen(req, timeout=10).read().decode("gbk")
        except: continue
        for line in raw.strip().split(";"):
            line = line.strip()
            if "=" not in line: continue
            try:
                var, val = line.split("=",1)
                rc = var.split("_")[-1]
                code = rc[2:] if rc[:2] in ("sz","sh") else rc
                p = val.strip('"').split("~")
                if len(p) < 50: continue
                op = float(p[5]) if p[5] else 0
                pc = float(p[4]) if p[4] else 0
                result[code] = {
                    "apct": round((op-pc)/pc*100,2) if pc else 0,
                    "aamt": float(p[37]) if p[37] else 0,
                    "avr": float(p[49]) if p[49] else 0,
                }
            except: pass
    return result

def main():
    today = datetime.now().strftime("%Y%m%d")
    # 找最近交易日
    pool = []; yest = today
    for d_off in range(0,6):
        d = (datetime.now()-timedelta(days=d_off)).strftime("%Y%m%d")
        pool = fetch_zt(d)
        if pool: yest=d; break
    print(f"[*] {yest} 涨停 {len(pool)} 只")

    codes = [s["c"] for s in pool]
    quotes = fetch_quotes(codes)

    rows = []
    for s in pool:
        code = s["c"]
        q = quotes.get(code, {})
        rows.append({
            "code":code, "name":s.get("n",""),
            "lbc":s.get("lbc",1),
            "pct":s.get("zdp",0),
            "price":s.get("p",0)/1000,
            "industry":s.get("hybk","其他"),
            "ltsz":round(s.get("ltsz",0)/1e8,1),
            "hs":s.get("hs",0),
            "market":market_of(code),
            "baby":baby_tags(code),
            "judge":judge(code),
            "apct":q.get("apct",0),
            "aamt":q.get("aamt",0),
            "avr":q.get("avr",0),
        })
    # 龙一龙二
    by_ind = defaultdict(list)
    for r in rows: by_ind[r["industry"]].append(r)
    for ind,arr in by_ind.items():
        arr.sort(key=lambda x:-x["lbc"])
        for i,r in enumerate(arr): r["long"]=f"龙{i+1}" if i<3 else ""
    rows.sort(key=lambda x:(-x["lbc"],-x["apct"]))

    g = defaultdict(list)
    for r in rows: g[r["lbc"]].append(r)
    ladder = [{"boards":k,"stocks":v} for k,v in sorted(g.items(),key=lambda x:-x[0])]

    data = {"date":today,"yest":yest,"total":len(rows),
            "maxLbc":max(r["lbc"] for r in rows) if rows else 0,
            "jiCount":sum(1 for r in rows if r["judge"]=="good"),
            "industries":len(by_ind),"ladder":ladder}

    # 读HTML模板，替换数据
    template = os.path.join(OUT, "连板梯队_template.html")
    if not os.path.exists(template):
        print("[!] 模板不存在"); return
    html = open(template,"r",encoding="utf-8").read()
    html = html.replace("__DATA__", json.dumps(data,ensure_ascii=False))
    out_path = os.path.join(OUT, "index.html")
    open(out_path,"w",encoding="utf-8").write(html)
    print(f"[+] HTML已生成: {out_path}")

if __name__=="__main__":
    main()
