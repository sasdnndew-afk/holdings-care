"""JS 포팅이 원본 rules.py와 같은 판정을 내는지 라이브 업비트 데이터로 대조한다: python crosscheck.py"""
import json, subprocess, sys, requests
sys.path.insert(0, r"C:\Users\hseth\trading-assistant")
from rules import Candle, Position, evaluate
from sources import parse_upbit_candles

today = "2026-10-20"
cases = []
for m in ["KRW-BTC", "KRW-XRP", "KRW-ETH", "KRW-DOGE", "KRW-SOL"]:
    c = parse_upbit_candles(requests.get("https://api.upbit.com/v1/candles/days", params={"market": m, "count": 120}).json())
    closed = [x for x in c if x.ts < today]
    last = closed[-1].close
    for mult, stage, floor in [(1.0, 0, 0), (0.93, 0, 0), (1.12, 0, 0), (1.3, 1, 0), (0.99, 1, last * 0.97)]:
        cases.append({"c": [x.__dict__ for x in c], "avg": last, "price": last * mult, "stage": stage, "floor": floor, "bought": closed[-12].ts})
bad = 0
for k in cases:
    py = evaluate(Position("X", "coin", k["avg"], 1, k["bought"], k["stage"], k["floor"]),
                  [Candle(**x) for x in k["c"]], k["price"], today)
    js = json.loads(subprocess.run(["node", "-e", f"""const {{evaluate}}=require('./rules.js');const k={json.dumps(k)};
console.log(JSON.stringify(evaluate({{avg_price:k.avg,bought_at:k.bought,stage:k.stage,stop_floor:k.floor,market:'coin'}},k.c.map(x=>({{...x}})),k.price,'{today}')))"""],
                                   capture_output=True, text=True, encoding="utf-8", check=True).stdout)
    ok = js["status"] == py.status and abs(js["stop"] - py.stop) < 1e-6 * py.stop and js["stage"] == py.stage and js["reason"] == py.reason
    bad += not ok
    if not ok: print("MISMATCH", py, js)
print(f"{len(cases) - bad}/{len(cases)} 일치")
sys.exit(bad)
