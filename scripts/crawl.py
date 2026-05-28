"""
ETF 데이터 수집 스크립트 - 전종목 자동 분류 방식
pykrx get_etf_ticker_list() 로 전체 ETF를 가져온 뒤
종목명 키워드로 지수별 자동 분류합니다.
"""

import json
import time
import os
from datetime import datetime, timedelta

import pandas as pd
from pykrx import stock


# -----------------------------------------------------------------
# 분류 규칙: 우선순위 순서대로 정의
# (index_id, 포함 키워드 목록, 제외 키워드 목록)
# 첫 번째로 매칭되는 규칙에 배정됩니다.
# -----------------------------------------------------------------
CLASSIFY_RULES = [
    # ── 국내주식 ──────────────────────────────────────────────
    ("kospi200",    ["KOSPI200", "코스피200", "KSP200", "200TR", "KODEX 200", "TIGER 200",
                     "RISE 200", "ACE 200", "SOL 200", "HANARO 200", "PLUS 200",
                     "KIWOOM 200", "KOSEF 200"],
                   ["인버스", "레버리지", "선물", "곱버스", "동일가중", "ESG", "고배당",
                    "배당", "미국", "나스닥", "섹터"]),

    ("kosdaq150",   ["코스닥150", "KOSDAQ150", "KOSDAQ 150"],
                   ["인버스", "레버리지", "선물"]),

    ("kr_dividend", ["고배당", "배당성장", "배당가치", "한국배당", "코리아배당",
                     "KODIV", "배당귀족"],
                   ["미국", "해외", "인버스", "레버리지"]),

    # ── 국내채권 ──────────────────────────────────────────────
    ("kr_gov10y",   ["국고채10년", "국채10년", "국고채 10년", "국채 10년"],
                   ["인버스", "레버리지"]),

    ("kr_gov3y",    ["국고채3년", "국채3년", "국고채 3년", "국채 3년"],
                   ["인버스", "레버리지"]),

    ("kr_corp",     ["회사채", "종합채권", "크레딧", "우량채"],
                   ["인버스", "레버리지", "미국", "해외"]),

    # ── 국내현금성 ────────────────────────────────────────────
    ("kr_cd",       ["CD금리", "KOFR", "단기채권", "머니마켓", "MMF", "초단기"],
                   ["미국", "해외"]),

    # ── 해외주식 ──────────────────────────────────────────────
    ("sp500",       ["S&P500", "S&P 500", "미국S&P", "미국 S&P"],
                   ["인버스", "레버리지", "선물인버스", "배당", "커버드콜",
                    "섹터", "산업재", "헬스케어", "금융", "에너지",
                    "나스닥", "GOLD", "골드", "(H)"]),

    ("nasdaq100",   ["나스닥100", "NASDAQ100", "NASDAQ 100", "미국나스닥100"],
                   ["인버스", "레버리지", "커버드콜"]),

    ("us_dividend", ["미국배당", "미국 배당", "다우존스배당", "배당다우존스",
                     "미국고배당"],
                   ["인버스", "레버리지"]),

    ("msci_world",  ["선진국MSCI", "MSCI World", "MSCI WORLD", "선진국 MSCI"],
                   ["인버스", "레버리지", "이머징", "신흥국"]),

    ("msci_em",     ["신흥국MSCI", "MSCI EM", "이머징", "EM지수"],
                   ["인버스", "레버리지"]),

    ("eu_equity",   ["유럽", "유로스탁스", "유로STOXX", "EURO STOXX"],
                   ["인버스", "레버리지"]),

    ("jp_equity",   ["일본", "니케이", "NIKKEI", "TOPIX", "닛케이"],
                   ["인버스", "레버리지"]),

    ("china_equity",["중국", "차이나", "CSI300", "항셍", "홍콩H",
                     "HSCEI", "항항"],
                   ["인버스", "레버리지"]),

    ("india_equity",["인도", "Nifty", "NIFTY", "SENSEX"],
                   ["인버스", "레버리지"]),

    # ── 해외채권 ──────────────────────────────────────────────
    ("us30y",       ["미국채30년", "미국30년국채", "미국채 30년",
                     "미국채울트라30년", "미국30년"],
                   ["인버스", "레버리지"]),

    ("us10y",       ["미국채10년", "미국10년국채", "미국채 10년",
                     "미국채선물"],
                   ["인버스", "레버리지", "30년"]),

    ("tips",        ["물가연동", "TIPS", "인플레"],
                   ["인버스", "레버리지"]),

    ("hy_bond",     ["하이일드", "HIGH YIELD", "HY"],
                   ["인버스", "레버리지"]),

    ("em_bond",     ["신흥국채권", "EM채권", "이머징채권"],
                   ["인버스", "레버리지"]),

    # ── 해외현금성 ────────────────────────────────────────────
    ("us_tbill",    ["미국단기채", "T-Bill", "TBILL", "미국초단기",
                     "미국MMF", "달러단기"],
                   ["인버스", "레버리지"]),

    # ── 해외대체: 원자재 ──────────────────────────────────────
    ("gold",        ["골드", "금현물", "금선물", "GOLD", "KRX금"],
                   ["인버스", "레버리지", "금채굴", "금광"]),

    ("silver",      ["은선물", "실버", "SILVER"],
                   ["인버스", "레버리지"]),

    ("oil",         ["원유", "WTI", "Oil", "OIL", "브렌트", "BRENT"],
                   ["인버스", "레버리지"]),

    ("commodity",   ["원자재", "Commodity", "COMMODITY", "농산물",
                     "에너지선물"],
                   ["인버스", "레버리지"]),

    # ── 해외대체: 부동산 ──────────────────────────────────────
    ("us_reit",     ["미국리츠", "미국 리츠", "미국부동산", "글로벌리츠",
                     "글로벌 리츠", "MSCI리츠"],
                   ["인버스", "레버리지"]),

    ("kr_reit",     ["리츠", "부동산투자"],
                   ["인버스", "레버리지", "미국", "글로벌"]),

    # ── 해외대체: 통화 ────────────────────────────────────────
    ("usd",         ["달러인덱스", "달러 인덱스", "DXY"],
                   ["인버스", "레버리지"]),
]

# 완전 제외 키워드 (어디에도 분류하지 않음)
GLOBAL_EXCLUDE = [
    "레버리지", "인버스", "곱버스", "2X", "선물인버스",
    "액티브ETN", "ETN", "스팩", "SPAC",
]


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


def classify(name):
    """
    ETF 이름을 받아 지수 ID를 반환합니다.
    매칭 규칙 없으면 None 반환.
    """
    name_upper = name.upper()

    # 전역 제외 체크
    for kw in GLOBAL_EXCLUDE:
        if kw.upper() in name_upper:
            return None

    # 분류 규칙 순차 적용
    for index_id, includes, excludes in CLASSIFY_RULES:
        matched = any(kw.upper() in name_upper for kw in includes)
        if not matched:
            continue
        excluded = any(kw.upper() in name_upper for kw in excludes)
        if excluded:
            continue
        return index_id

    return None


# -----------------------------------------------------------------
# 데이터 수집
# -----------------------------------------------------------------

def fetch_etf_info(ticker, name, start, end, etf_all):
    """단일 ETF 데이터 수집. 실패 시 None 반환."""
    try:
        # 추적오차
        df_te = stock.get_etf_tracking_error(start, end, ticker)
        if df_te is None or not isinstance(df_te, pd.DataFrame) or df_te.empty:
            return None

        te_col = safe_col(df_te, ["추적오차", "오차", "TrackingError", "tracking"])
        tracking_error = round(float(df_te[te_col].abs().mean()), 4) if te_col else 0.0

        # 괴리율
        discount_rate = 0.0
        try:
            ohlcv = stock.get_etf_ohlcv_by_date(start, end, ticker)
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

        # 일평균 거래대금 (억원)
        daily_volume = 0.0
        try:
            df_vol = stock.get_etf_trading_volume_and_value(start, end, ticker)
            if df_vol is not None and isinstance(df_vol, pd.DataFrame) and not df_vol.empty:
                vol_col = safe_col(df_vol, ["거래대금", "value", "Value"])
                if vol_col:
                    daily_volume = round(float(df_vol[vol_col].mean()) / 1e8, 1)
        except Exception as e:
            print(f"    거래대금 실패: {e}")

        # AUM (억원) - 전종목 데이터에서 추출
        aum = 0.0
        if etf_all is not None and ticker in etf_all.index:
            aum_col = safe_col(etf_all, ["순자산총액", "순자산", "AUM", "시가총액"])
            if aum_col:
                aum = round(float(etf_all.loc[ticker, aum_col]) / 1e8, 1)

        # 상장 기간 (개월) - 전체 기간 OHLCV의 첫 날짜 기준
        listing_months = 0
        try:
            df_all = stock.get_etf_ohlcv_by_date("20000101", end, ticker)
            if df_all is not None and isinstance(df_all, pd.DataFrame) and not df_all.empty:
                first_date = df_all.index.min()
                listing_months = max(1, int(
                    (datetime.now() - pd.Timestamp(first_date)).days / 30
                ))
        except Exception as e:
            print(f"    상장일 실패: {e}")

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

    # 전종목 티커 목록 조회
    print("\n전체 ETF 티커 목록 조회 중...")
    all_tickers = stock.get_etf_ticker_list(end_date)
    print(f"총 {len(all_tickers)}개 ETF 티커 확인")

    # 전종목 기본정보 (AUM용) - 1회만 조회
    print("전종목 기본정보 조회 중...")
    etf_all = None
    try:
        etf_all = stock.get_etf_ohlcv_by_ticker(end_date)
        if etf_all is not None and not etf_all.empty:
            print(f"전종목 기본정보 조회 완료: {len(etf_all)}개, 컬럼: {list(etf_all.columns)}")
    except Exception as e:
        print(f"전종목 기본정보 조회 실패: {e}")

    # 티커별 이름 조회 및 분류
    # pykrx 1.2.x에서 get_market_ticker_name이 깨져 있으므로
    # get_etf_ohlcv_by_ticker 인덱스 이름을 활용하거나
    # 추적오차 데이터가 있는 ETF만 처리합니다.
    print("\n티커 분류 중...")

    # etf_all의 인덱스가 티커, index.name 또는 별도 컬럼에 이름이 있을 수 있음
    # 이름 조회: get_etf_ticker_list 결과로 순회하며 개별 조회 시도
    ticker_name_map = {}
    for ticker in all_tickers:
        try:
            # pykrx 1.2.x: get_market_ticker_name 우회
            # 이름이 포함된 다른 함수 시도
            result = stock.get_market_ticker_name(ticker)
            if isinstance(result, str) and result:
                ticker_name_map[ticker] = result
            elif isinstance(result, pd.DataFrame) and not result.empty:
                val = result.iloc[0, 0] if result.shape[1] > 0 else str(result.index[0])
                ticker_name_map[ticker] = str(val)
            elif isinstance(result, pd.Series) and not result.empty:
                ticker_name_map[ticker] = str(result.iloc[0])
        except Exception:
            pass

    print(f"이름 조회 성공: {len(ticker_name_map)}개")

    # 이름 조회 실패한 경우: ETF 기본정보 DataFrame의 index name 활용 시도
    if len(ticker_name_map) < len(all_tickers) // 2:
        print("이름 조회 실패 비율 높음. 대안 방법 시도...")
        try:
            df_master = stock.get_etf_portfolio_deposit_file(end_date)
            if df_master is not None and not df_master.empty:
                print(f"  portfolio_deposit_file 컬럼: {list(df_master.columns)[:10]}")
        except Exception as e:
            print(f"  portfolio_deposit_file 실패: {e}")

        # 최후 수단: etf_all index가 티커이고 별도 이름 컬럼 확인
        if etf_all is not None and not etf_all.empty:
            name_col = safe_col(etf_all, ["종목명", "Name", "name", "ETF명"])
            if name_col:
                for ticker in all_tickers:
                    if ticker not in ticker_name_map and ticker in etf_all.index:
                        ticker_name_map[ticker] = str(etf_all.loc[ticker, name_col])
                print(f"  etf_all 이름 컬럼 활용 후: {len(ticker_name_map)}개")

    # 분류 실행
    classified = {}   # { index_id: [(ticker, name), ...] }
    unclassified = []

    for ticker in all_tickers:
        name = ticker_name_map.get(ticker, "")
        if not name:
            unclassified.append((ticker, "이름없음"))
            continue
        index_id = classify(name)
        if index_id:
            classified.setdefault(index_id, []).append((ticker, name))
        else:
            unclassified.append((ticker, name))

    print(f"\n분류 결과:")
    for idx, items in sorted(classified.items()):
        print(f"  {idx}: {len(items)}개")
    print(f"  미분류: {len(unclassified)}개")

    # 지수별 데이터 수집
    output = {idx: [] for idx, _, _ in CLASSIFY_RULES}

    for index_id, ticker_list in classified.items():
        print(f"\n[{index_id}] 수집 시작 ({len(ticker_list)}개)")
        etf_list = []

        for ticker, name in ticker_list:
            print(f"  {ticker} ({name}) 수집 중...", flush=True)
            result = fetch_etf_info(ticker, name, start_date, end_date, etf_all)
            if result:
                print(f"  -> 완료: 추적오차={result['trackingError']} "
                      f"괴리율={result['discountRate']} "
                      f"AUM={result['aum']}억 "
                      f"거래대금={result['dailyVolume']}억 "
                      f"상장={result['listingMonths']}개월")
                etf_list.append(result)
            else:
                print(f"  -> 건너뜀")
            time.sleep(0.3)

        output[index_id] = etf_list
        print(f"  [{index_id}] {len(etf_list)}개 수집 완료")

    # 저장
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
