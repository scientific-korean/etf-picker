"""
추적오차 컬럼명 및 종목명 조회 방법 진단 스크립트
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

end_date   = get_recent_business_day(1)
start_date = get_recent_business_day(20)
print(f"기간: {start_date} ~ {end_date}")

known = {
    "069500": "KODEX 200 (kospi200)",
    "360750": "TIGER 미국S&P500 (sp500)",
    "133690": "TIGER 미국나스닥100 (nasdaq100)",
    "148070": "KOSEF 국고채10년 (kr_gov10y)",
    "132030": "KODEX 골드선물 (gold)",
    "305080": "TIGER 미국채10년선물 (us10y)",
    "441680": "TIGER 미국배당다우존스 (us_dividend)",
    "229200": "KODEX 코스닥150 (kosdaq150)",
}

for ticker, label in known.items():
    print(f"\n{'='*50}")
    print(f"{label} - {ticker}")

    # 1. 추적오차 컬럼명 확인
    try:
        df_te = stock.get_etf_tracking_error(start_date, end_date, ticker)
        if df_te is not None and not df_te.empty:
            print(f"  추적오차 컬럼: {list(df_te.columns)}")
            print(f"  추적오차 샘플:\n{df_te.tail(2).to_string()}")
        else:
            print(f"  추적오차: 데이터 없음")
    except Exception as e:
        print(f"  추적오차 오류: {e}")

    # 2. 종목 기본정보 조회 시도
    try:
        df_info = stock.get_etf_portfolio_deposit_file(end_date, ticker)
        if df_info is not None and not df_info.empty:
            print(f"  portfolio_deposit 컬럼: {list(df_info.columns)[:10]}")
            print(f"  portfolio_deposit 샘플:\n{df_info.head(2).to_string()}")
        else:
            print(f"  portfolio_deposit: 데이터 없음")
    except Exception as e:
        print(f"  portfolio_deposit 오류: {e}")
