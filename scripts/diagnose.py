"""
기초지수 실제 값 확인용 진단 스크립트
crawl.py 실행 전에 이걸 먼저 실행해서 분류 키워드를 맞춥니다.
"""
import os
from datetime import datetime, timedelta
import pandas as pd
from pykrx import stock

def get_recent_business_day(offset=1):
    date = datetime.now()
    days_back = 0
    while days_back < offset or date.weekday() >= 5:
        date -= timedelta(days=1)
        if date.weekday() < 5:
            days_back += 1
    return date.strftime("%Y%m%d")

end_date = get_recent_business_day(1)
print(f"조회 기준일: {end_date}")

etf_all = stock.get_etf_ohlcv_by_ticker(end_date)
print(f"전종목: {len(etf_all)}개")
print(f"컬럼: {list(etf_all.columns)}")
print(f"인덱스 이름: {etf_all.index.name}")
print(f"인덱스 샘플 (티커): {list(etf_all.index[:5])}")
print()

# 기초지수 실제 값 샘플 50개 출력
print("=== 기초지수 실제 값 샘플 (50개) ===")
idx_col = "기초지수"
sample = etf_all[idx_col].dropna().unique()[:50]
for v in sample:
    print(f"  [{v}]")

# 잘 알려진 티커의 기초지수 확인
print()
print("=== 주요 ETF 기초지수 확인 ===")
known = {
    "069500": "KODEX 200",
    "360750": "TIGER 미국S&P500",
    "133690": "TIGER 미국나스닥100",
    "148070": "KOSEF 국고채10년",
    "132030": "KODEX 골드선물",
    "305080": "TIGER 미국채10년선물",
}
for ticker, name in known.items():
    if ticker in etf_all.index:
        val = etf_all.loc[ticker, idx_col]
        print(f"  {name} ({ticker}): [{val}]")
    else:
        print(f"  {name} ({ticker}): 인덱스에 없음")
