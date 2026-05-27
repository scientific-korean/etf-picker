"""
ETF 데이터 수집 스크립트 - pykrx 1.2.x 호환
"""

import json
import time
import os
from datetime import datetime, timedelta

import pandas as pd
from pykrx import stock


# -----------------------------------------------------------------
# 설정: 지수 ID -> { 티커: 종목명 }
# -----------------------------------------------------------------
INDEX_TICKERS = {
    "kospi200": {
        "069500": "KODEX 200",
        "102110": "TIGER 200",
        "278530": "KODEX 200TR",
        "278540": "TIGER 200TR",
    },
    "kosdaq150": {
        "229200": "KODEX 코스닥150",
        "278600": "TIGER 코스닥150",
    },
    "kr_dividend": {
        "279530": "KODEX 배당성장",
        "421460": "TIGER 배당성장",
        "270800": "KODEX 배당가치",
        "322400": "KODEX 한국배당가치",
    },
    "kr_gov10y": {
        "148070": "KOSEF 국고채10년",
        "152380": "TIGER 국채3년",
        "114820": "KODEX 국고채3년",
    },
    "kr_corp": {
        "136340": "KBSTAR 우량회사채",
        "159560": "KODEX 종합채권AA이상",
    },
    "sp500": {
        "360750": "TIGER 미국S&P500",
        "379800": "KODEX 미국S&P500TR",
        "429500": "KODEX 미국S&P500",
        "360200": "ACE 미국S&P500",
        "449170": "SOL 미국S&P500",
        "458730": "RISE 미국S&P500",
    },
    "nasdaq100": {
        "133690": "TIGER 미국나스닥100",
        "379810": "KODEX 미국나스닥100TR",
        "367380": "ACE 미국나스닥100",
        "449160": "SOL 미국나스닥100",
    },
    "us_dividend": {
        "441680": "TIGER 미국배당다우존스",
        "466920": "ACE 미국배당다우존스",
        "455890": "KODEX 미국배당프리미엄액티브",
    },
    "msci_world": {
        "251350": "KODEX 선진국MSCI World",
        "390390": "TIGER 선진국MSCI World",
    },
    "msci_em": {
        "195930": "TIGER 신흥국MSCI(합성)",
        "291890": "KODEX 신흥국MSCI(합성)",
    },
    "jp_equity": {
        "241180": "KODEX 일본TOPIX100",
        "396520": "TIGER 일본니케이225",
    },
    "china_equity": {
        "256840": "TIGER 차이나CSI300",
    },
    "india_equity": {
        "453810": "KODEX 인도Nifty50",
        "469070": "TIGER 인도니프티50",
    },
    "us10y": {
        "305080": "TIGER 미국채10년선물",
        "308620": "KODEX 미국채10년선물",
    },
    "us30y": {
        "304660": "KODEX 미국채울트라30년선물",
        "453850": "ACE 미국30년국채액티브",
    },
    "tips": {
        "261240": "TIGER 미국물가연동국채(합성)",
    },
    "gold": {
        "132030": "KODEX 골드선물(H)",
        "319640": "TIGER 골드선물(H)",
        "411060": "ACE KRX금현물",
    },
    "oil": {
        "261220": "TIGER 원유선물Enhanced(H)",
        "271060": "KODEX WTI원유선물(H)",
    },
    "us_reit": {
        "182480": "TIGER 미국MSCI리츠(합성H)",
        "352560": "KODEX 미국부동산리츠(H)",
    },
    "kr_cd": {
        "152100": "KODEX 단기채권",
        "214980": "KODEX CD금리액티브(합성)",
        "432350": "KODEX KOFR금리액티브(합성)",
    },
}


# -----------------------------------------------------------------
# 유틸
# -----------------------------------------------------------------

def get_recent_business_day(offset=1):
    date = datetime.now()
    days_back = 0
    while days_back < offset or date.weekday() >= 5:
        date -= timedelta(days=1)
        if date.weekday() < 5:
            days_back += 1
    return date.strftime("%Y%m%d")


def safe_col(df, keywords):
    for kw in keywords:
        cols = [c for c in df.columns if kw in str(c)]
        if cols:
            return cols[0]
    return None


def get_aum_and_listing(ticker, end_date):
    """
    get_etf_ohlcv_by_date 로 AUM(순자산총액)과 상장일을 가져옵니다.
    pykrx에서 ETF OHLCV 결과에 '상장시가총액' 또는 'NAV' 컬럼이 포함됩니다.
    상장일은 전체 기간(2000-01-01~) 조회 후 첫 인덱스로 계산합니다.
    """
    aum = 0.0
    listing_months = 0

    try:
        # AUM: 당일 기준 ETF 기본 정보
        df_info = stock.get_etf_ohlcv_by_ticker(end_date)
        if df_info is not None and isinstance(df_info, pd.DataFrame) and not df_info.empty:
            print(f"    ETF 전종목 컬럼: {list(df_info.columns)}")
            if ticker in df_info.index:
                row = df_info.loc[ticker]
                aum_col = safe_col(df_info, ["순자산총액", "순자산", "AUM", "시가총액"])
                if aum_col:
                    aum = round(float(row[aum_col]) / 1e8, 1)
                    print(f"    AUM: {aum}억 (컬럼: {aum_col})")
    except Exception as e:
        print(f"    AUM 수집 실패: {e}")

    try:
        # 상장일: 가능한 먼 과거부터 조회해서 첫 거래일 확인
        df_old = stock.get_etf_ohlcv_by_date("20000101", end_date, ticker)
        if df_old is not None and isinstance(df_old, pd.DataFrame) and not df_old.empty:
            first_date = df_old.index.min()
            listing_months = max(1, int((datetime.now() - pd.Timestamp(first_date)).days / 30))
            print(f"    상장일: {first_date.date()} -> {listing_months}개월")
    except Exception as e:
        print(f"    상장일 수집 실패: {e}")

    return aum, listing_months


def fetch_etf_info(ticker, name, start, end):
    try:
        # 추적오차 데이터
        df_te = stock.get_etf_tracking_error(start, end, ticker)
        if df_te is None or not isinstance(df_te, pd.DataFrame) or df_te.empty:
            print(f"    추적오차 데이터 없음")
            return None

        print(f"    추적오차 컬럼: {list(df_te.columns)}")

        # 추적 오차
        te_col = safe_col(df_te, ["추적오차", "오차", "TrackingError", "tracking", "Tracking"])
        tracking_error = round(float(df_te[te_col].abs().mean()), 4) if te_col else 0.0

        # 괴리율
        discount_rate = 0.0
        try:
            ohlcv = stock.get_etf_ohlcv_by_date(start, end, ticker)
            nav_col = safe_col(df_te, ["NAV", "순자산가치", "기준가", "nav"])
            if (nav_col
                    and ohlcv is not None
                    and isinstance(ohlcv, pd.DataFrame)
                    and not ohlcv.empty
                    and "종가" in ohlcv.columns):
                merged = pd.merge(
                    ohlcv[["종가"]], df_te[[nav_col]],
                    left_index=True, right_index=True, how="inner"
                )
                merged["gap"] = (merged["종가"] - merged[nav_col]) / merged[nav_col] * 100
                discount_rate = round(float(merged["gap"].mean()), 4)
        except Exception as e:
            print(f"    괴리율 계산 실패: {e}")

        # 일평균 거래대금
        daily_volume = 0.0
        try:
            df_vol = stock.get_etf_trading_volume_and_value(start, end, ticker)
            if df_vol is not None and isinstance(df_vol, pd.DataFrame) and not df_vol.empty:
                vol_col = safe_col(df_vol, ["거래대금", "value", "Value"])
                if vol_col:
                    daily_volume = round(float(df_vol[vol_col].mean()) / 1e8, 1)
        except Exception as e:
            print(f"    거래대금 수집 실패: {e}")

        # AUM + 상장 기간
        aum, listing_months = get_aum_and_listing(ticker, end)

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
        print(f"    [오류] {e}")
        return None


# -----------------------------------------------------------------
# 메인
# -----------------------------------------------------------------

def main():
    end_date   = get_recent_business_day(1)
    start_date = get_recent_business_day(20)
    print(f"수집 기간: {start_date} ~ {end_date}")

    # ETF 전종목 정보를 1회만 조회해서 재사용 (AUM용)
    print("\nETF 전종목 기본정보 사전 조회...")
    etf_all = None
    try:
        etf_all = stock.get_etf_ohlcv_by_ticker(end_date)
        if etf_all is not None and not etf_all.empty:
            print(f"전종목 조회 완료: {len(etf_all)}개, 컬럼: {list(etf_all.columns)}")
        else:
            print("전종목 조회 결과 없음")
    except Exception as e:
        print(f"전종목 조회 실패: {e}")

    output = {}

    for index_id, ticker_map in INDEX_TICKERS.items():
        print(f"\n[{index_id}] 수집 시작 ({len(ticker_map)}개 티커)")
        etf_list = []

        for ticker, name in ticker_map.items():
            print(f"  {ticker} ({name}) 수집 중...", flush=True)

            try:
                # 추적오차
                df_te = stock.get_etf_tracking_error(start_date, end_date, ticker)
                if df_te is None or not isinstance(df_te, pd.DataFrame) or df_te.empty:
                    print(f"    추적오차 없음 -> 건너뜀")
                    continue

                te_col = safe_col(df_te, ["추적오차", "오차", "TrackingError", "tracking", "Tracking"])
                tracking_error = round(float(df_te[te_col].abs().mean()), 4) if te_col else 0.0

                # 괴리율
                discount_rate = 0.0
                try:
                    ohlcv = stock.get_etf_ohlcv_by_date(start_date, end_date, ticker)
                    nav_col = safe_col(df_te, ["NAV", "순자산가치", "기준가", "nav"])
                    if (nav_col and ohlcv is not None
                            and isinstance(ohlcv, pd.DataFrame)
                            and not ohlcv.empty and "종가" in ohlcv.columns):
                        merged = pd.merge(
                            ohlcv[["종가"]], df_te[[nav_col]],
                            left_index=True, right_index=True, how="inner"
                        )
                        merged["gap"] = (merged["종가"] - merged[nav_col]) / merged[nav_col] * 100
                        discount_rate = round(float(merged["gap"].mean()), 4)
                except Exception as e:
                    print(f"    괴리율 실패: {e}")

                # 일평균 거래대금
                daily_volume = 0.0
                try:
                    df_vol = stock.get_etf_trading_volume_and_value(start_date, end_date, ticker)
                    if df_vol is not None and isinstance(df_vol, pd.DataFrame) and not df_vol.empty:
                        vol_col = safe_col(df_vol, ["거래대금", "value", "Value"])
                        if vol_col:
                            daily_volume = round(float(df_vol[vol_col].mean()) / 1e8, 1)
                except Exception as e:
                    print(f"    거래대금 실패: {e}")

                # AUM - 전종목 데이터에서 추출
                aum = 0.0
                if etf_all is not None and ticker in etf_all.index:
                    aum_col = safe_col(etf_all, ["순자산총액", "순자산", "AUM", "시가총액"])
                    if aum_col:
                        aum = round(float(etf_all.loc[ticker, aum_col]) / 1e8, 1)

                # 상장 기간 - 전체 기간 조회
                listing_months = 0
                try:
                    df_all = stock.get_etf_ohlcv_by_date("20000101", end_date, ticker)
                    if df_all is not None and isinstance(df_all, pd.DataFrame) and not df_all.empty:
                        first_date = df_all.index.min()
                        listing_months = max(1, int(
                            (datetime.now() - pd.Timestamp(first_date)).days / 30
                        ))
                except Exception as e:
                    print(f"    상장일 실패: {e}")

                result = {
                    "name":          name,
                    "ticker":        ticker,
                    "trackingError": tracking_error,
                    "discountRate":  discount_rate,
                    "aum":           aum,
                    "dailyVolume":   daily_volume,
                    "listingMonths": listing_months,
                }
                print(f"  -> 완료: 추적오차={tracking_error} 괴리율={discount_rate} AUM={aum}억 거래대금={daily_volume}억 상장={listing_months}개월")
                etf_list.append(result)

            except Exception as e:
                print(f"  -> [오류] {e}")

            time.sleep(0.3)

        output[index_id] = etf_list
        print(f"  [{index_id}] {len(etf_list)}개 수집 완료")

    os.makedirs("data", exist_ok=True)
    payload = {
        "updatedAt": datetime.now().strftime("%Y-%m-%d"),
        "data": output,
    }
    with open("data/etf_data.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    total = sum(len(v) for v in output.values())
    print(f"\n[완료] 총 {total}개 ETF 데이터 저장 -> data/etf_data.json")


if __name__ == "__main__":
    main()
