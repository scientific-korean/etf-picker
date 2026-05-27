"""
ETF 데이터 수집 스크립트
pykrx를 사용해 KRX에서 직접 데이터를 가져옵니다.
결과는 data/etf_data.json에 저장됩니다.

JSON 구조:
{
  "updatedAt": "2025-05-27",
  "data": {
    "sp500": [ { "name": "...", "trackingError": 0.12, ... }, ... ],
    "kospi200": [ ... ]
  }
}
"""

import json
import time
import os
from datetime import datetime, timedelta

import pandas as pd
from pykrx import stock

# pykrx 로그인 정보 가져오기
os.environ["KRX_ID"] = os.environ.get("KRX_ID", "")
os.environ["KRX_PW"] = os.environ.get("KRX_PW", "")

# -----------------------------------------------------------------
# 설정: 지수 ID -> 추종 ETF 티커 목록 (KRX 6자리 종목코드)
# 새 ETF 추가/제거 시 이 딕셔너리만 수정하세요.
# -----------------------------------------------------------------
INDEX_TICKERS = {
    # 국내주식
    "kospi200": [
        "069500",  # KODEX 200
        "102110",  # TIGER 200
        "278530",  # KODEX 200TR
        "278540",  # TIGER 200TR
    ],
    "kosdaq150": [
        "229200",  # KODEX 코스닥150
        "278600",  # TIGER 코스닥150
    ],
    "kr_dividend": [
        "279530",  # KODEX 배당성장
        "421460",  # TIGER 배당성장
        "270800",  # KODEX 배당가치
        "322400",  # KODEX 한국배당가치
    ],

    # 국내채권
    "kr_gov10y": [
        "148070",  # KOSEF 국고채10년
        "152380",  # TIGER 국채3년
        "114820",  # KODEX 국고채3년
    ],
    "kr_corp": [
        "136340",  # KBSTAR 우량회사채
        "159560",  # KODEX 종합채권AA이상
    ],

    # 해외주식
    "sp500": [
        "360750",  # TIGER 미국S&P500
        "379800",  # KODEX 미국S&P500TR
        "429500",  # KODEX 미국S&P500
        "360200",  # ACE 미국S&P500
        "449170",  # SOL 미국S&P500
        "458730",  # RISE 미국S&P500
    ],
    "nasdaq100": [
        "133690",  # TIGER 미국나스닥100
        "379810",  # KODEX 미국나스닥100TR
        "367380",  # ACE 미국나스닥100
        "449160",  # SOL 미국나스닥100
    ],
    "us_dividend": [
        "441680",  # TIGER 미국배당다우존스
        "466920",  # ACE 미국배당다우존스
        "455890",  # KODEX 미국배당프리미엄액티브
    ],
    "msci_world": [
        "251350",  # KODEX 선진국MSCI World
        "390390",  # TIGER 선진국MSCI World
    ],
    "msci_em": [
        "195930",  # TIGER 신흥국MSCI(합성)
        "291890",  # KODEX 신흥국MSCI(합성)
    ],
    "jp_equity": [
        "241180",  # KODEX 일본TOPIX100
        "396520",  # TIGER 일본니케이225
    ],
    "china_equity": [
        "256840",  # TIGER 차이나CSI300
    ],
    "india_equity": [
        "453810",  # KODEX 인도Nifty50
        "469070",  # TIGER 인도니프티50
    ],

    # 해외채권
    "us10y": [
        "305080",  # TIGER 미국채10년선물
        "308620",  # KODEX 미국채10년선물
    ],
    "us30y": [
        "304660",  # KODEX 미국채울트라30년선물
        "453850",  # ACE 미국30년국채액티브
    ],
    "tips": [
        "261240",  # TIGER 미국물가연동국채(합성)
    ],

    # 해외대체
    "gold": [
        "132030",  # KODEX 골드선물(H)
        "319640",  # TIGER 골드선물(H)
        "411060",  # ACE KRX금현물
    ],
    "oil": [
        "261220",  # TIGER 원유선물Enhanced(H)
        "271060",  # KODEX WTI원유선물(H)
    ],
    "us_reit": [
        "182480",  # TIGER 미국MSCI리츠(합성H)
        "352560",  # KODEX 미국부동산리츠(H)
    ],

    # 국내현금성
    "kr_cd": [
        "152100",  # KODEX 단기채권
        "214980",  # KODEX CD금리액티브(합성)
        "432350",  # KODEX KOFR금리액티브(합성)
    ],
}

# 레버리지/인버스 제외 키워드
EXCLUDE_KEYWORDS = ["레버리지", "인버스", "2X", "곱버스", "LEVERAGE", "INVERSE"]


# -----------------------------------------------------------------
# 유틸 함수
# -----------------------------------------------------------------

def get_recent_business_day(offset=1):
    """오늘로부터 offset 영업일 이전 날짜를 YYYYMMDD 형식으로 반환"""
    date = datetime.now()
    days_back = 0
    while days_back < offset or date.weekday() >= 5:
        date -= timedelta(days=1)
        if date.weekday() < 5:
            days_back += 1
    return date.strftime("%Y%m%d")


def is_excluded(name):
    return any(kw in name.upper() for kw in EXCLUDE_KEYWORDS)


def safe_col(df, keywords):
    """컬럼명에 keyword가 포함된 첫 번째 컬럼명 반환. 없으면 None."""
    for kw in keywords:
        cols = [c for c in df.columns if kw in c]
        if cols:
            return cols[0]
    return None


def fetch_etf_info(ticker, start, end):
    """단일 ETF 티커의 필요 데이터를 수집해 dict 반환. 실패 시 None."""
    try:
        name = stock.get_market_ticker_name(ticker)
        if not name or is_excluded(name):
            return None

        # 추적오차 데이터 (NAV, 기초지수, 추적오차율 포함)
        df_te = stock.get_etf_tracking_error(start, end, ticker)
        if df_te is None or df_te.empty:
            return None

        # 추적 오차: 최근 20거래일 절댓값 평균
        te_col = safe_col(df_te, ["추적오차", "오차"])
        tracking_error = round(float(df_te[te_col].abs().mean()), 4) if te_col else 0.0

        # 괴리율: (종가 - NAV) / NAV * 100 의 기간 평균
        discount_rate = 0.0
        try:
            ohlcv = stock.get_etf_ohlcv_by_date(start, end, ticker)
            nav_col = safe_col(df_te, ["NAV", "순자산가치"])
            if nav_col and ohlcv is not None and not ohlcv.empty and "종가" in ohlcv.columns:
                merged = pd.merge(
                    ohlcv[["종가"]], df_te[[nav_col]],
                    left_index=True, right_index=True, how="inner"
                )
                merged["gap"] = (merged["종가"] - merged[nav_col]) / merged[nav_col] * 100
                discount_rate = round(float(merged["gap"].mean()), 4)
        except Exception as e:
            print(f"    괴리율 계산 실패: {e}")

        # 순자산(AUM) - 억원 단위
        aum = 0.0
        try:
            df_fund = stock.get_etf_portfolio_deposit_file(end, ticker)
            if df_fund is not None and not df_fund.empty:
                fund_col = safe_col(df_fund, ["순자산", "AUM"])
                if fund_col:
                    aum = round(float(df_fund[fund_col].iloc[0]) / 1e8, 1)
        except Exception as e:
            print(f"    AUM 수집 실패: {e}")

        # 일평균 거래대금 - 억원 단위
        daily_volume = 0.0
        try:
            df_vol = stock.get_etf_trading_volume_and_value(start, end, ticker)
            if df_vol is not None and not df_vol.empty:
                vol_col = safe_col(df_vol, ["거래대금"])
                if vol_col:
                    daily_volume = round(float(df_vol[vol_col].mean()) / 1e8, 1)
        except Exception as e:
            print(f"    거래대금 수집 실패: {e}")

        # 상장 기간 (개월) - 첫 NAV 날짜 기준
        listing_months = 0
        try:
            first_date = df_te.index.min()
            listing_months = max(0, int((datetime.now() - pd.Timestamp(first_date)).days / 30))
        except Exception:
            pass

        return {
            "name":          name,
            "ticker":        ticker,
            "trackingError": tracking_error,
            "discountRate":  discount_rate,
            "aum":           aum,
            "dailyVolume":   daily_volume,
            "listingMonths": listing_months,
        }

    except Exception as e:
        print(f"  [오류] {ticker}: {e}")
        return None


# -----------------------------------------------------------------
# 메인
# -----------------------------------------------------------------

def main():
    end_date   = get_recent_business_day(1)
    start_date = get_recent_business_day(20)
    print(f"수집 기간: {start_date} ~ {end_date}")

    output = {}

    for index_id, tickers in INDEX_TICKERS.items():
        print(f"\n[{index_id}] 수집 시작 ({len(tickers)}개 티커)")
        etf_list = []

        for ticker in tickers:
            print(f"  {ticker} 수집 중...", end=" ", flush=True)
            result = fetch_etf_info(ticker, start_date, end_date)
            if result:
                print(f"완료 ({result['name']})")
                etf_list.append(result)
            else:
                print("건너뜀")
            time.sleep(0.5)

        output[index_id] = etf_list
        print(f"  -> {len(etf_list)}개 수집 완료")

    os.makedirs("data", exist_ok=True)
    payload = {
        "updatedAt": datetime.now().strftime("%Y-%m-%d"),
        "data": output,
    }
    with open("data/etf_data.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print("\n[완료] data/etf_data.json 저장 완료")


if __name__ == "__main__":
    main()
