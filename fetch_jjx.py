# -*- coding: utf-8 -*-
"""每天9:26抓取昨日涨停票的今日竞价数据"""
import urllib.request, json, datetime, os

# 1. 找最近一个交易日（昨天）
today = datetime.date.today()
yesterday = today - datetime.timedelta(days=1)
# 跳过周末
while yesterday.weekday() >= 5:
    yesterday = yesterday - datetime.timedelta(days=1)

date_str = yesterday.strftime("%Y%m%d")
print(f"拉取 {date_str} 涨停池...")

# 2. 拉昨日涨停池
zt_url = f"https://push2ex.eastmoney.com/getTopicZTPool?ut=7eea3edcaed734bea9cbfc24409ed989&dpt=wz.ztzt&Pageindex=0&pagesize=200&sort=fbt:asc&date={date_str}"
req = urllib.request.Request(zt_url, headers={"User-Agent":"Mozilla/5.0"})
r = urllib.request.urlopen(req, timeout=15)
j = json.loads(r.read().decode())
pool = j["data"]["pool"]
print(f"昨日涨停 {len(pool)} 只")

# 3. 拉今天竞价数据（腾讯行情）
codes = []
for s in pool:
    prefix = "sh" if s["c"].startswith("6") else "sz"
    codes.append(prefix + s["c"])

# 分批拉腾讯行情
all_quotes = {}
for i in range(0, len(codes), 30):
    batch = codes[i:i+30]
    url = "http://qt.gtimg.cn/q=" + ",".join(batch)
    req2 = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
    r2 = urllib.request.urlopen(req2, timeout=15)
    data = r2.read().decode("gbk", errors="ignore")
    for line in data.strip().split(";"):
        if not line.strip(): continue
        try:
            key = line.split("=")[0].strip()
            val = line.split("=")[1].strip('"').strip()
            arr = val.split("~")
            if len(arr) > 49:
                code = key.replace("v_", "")[2:]
                all_quotes[code] = {
                    "price": float(arr[3]),       # 当前价
                    "preClose": float(arr[4]),    # 昨收
                    "open": float(arr[5]),        # 今开
                    "hs": float(arr[38]),         # 换手率
                    "avr": float(arr[49]),        # 量比
                    "amt": float(arr[37]),        # 成交额（万）
                    "rtPct": float(arr[32]),      # 涨跌幅
                }
        except:
            pass

# 4. 组装竞价数据
result = []
for s in pool:
    code = s["c"]
    q = all_quotes.get(code, {})
    open_p = q.get("open", 0)
    pre_close = q.get("preClose", 0)
    apct = round((open_p - pre_close) / pre_close * 100, 2) if pre_close else 0
    result.append({
        "code": code,
        "name": s["n"],
        "lbc": s["lbc"],
        "hybk": s.get("hybk", ""),
        "ltsz": s.get("ltsz", 0),
        "apct": apct,
        "open": open_p,
        "price": q.get("price", 0),
        "rtPct": q.get("rtPct", 0),
        "hs": q.get("hs", 0),
        "avr": q.get("avr", 0),
        "amt": q.get("amt", 0),
    })

# 5. 存成JSON
output = {
    "date": today.strftime("%Y-%m-%d"),
    "ztDate": date_str,
    "count": len(result),
    "data": result
}

with open("jjx_data.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"完成，输出 jjx_data.json，共 {len(result)} 只")
