import { useState, useMemo, useEffect, useCallback } from "react";

// ── 설정 ───────────────────────────────────────────────────────
// GitHub Pages에 배포된 JSON 파일 URL로 교체하세요
const DATA_URL = "https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/data/etf_data.json";

// ── 지수 카탈로그 ──────────────────────────────────────────────
const THEME_CATALOG = [
  {
    id: "domestic_equity", label: "국내주식", color: "#34d399",
    indices: [
      { id: "kospi200",    label: "KOSPI 200",    desc: "국내 대형주 200종목" },
      { id: "kosdaq150",   label: "KOSDAQ 150",   desc: "국내 중소형 기술주" },
      { id: "kr_dividend", label: "국내 고배당",   desc: "고배당·배당성장 ETF" },
      { id: "kr_value",    label: "국내 가치주",   desc: "저PBR·저PER 스타일" },
      { id: "kr_sector",   label: "국내 섹터",     desc: "반도체·2차전지 등" },
    ],
  },
  {
    id: "domestic_bond", label: "국내채권", color: "#4ade80",
    indices: [
      { id: "kr_gov3y",    label: "국내 국채 3년",  desc: "단기 국고채" },
      { id: "kr_gov10y",   label: "국내 국채 10년", desc: "장기 국고채" },
      { id: "kr_corp",     label: "국내 회사채",    desc: "투자등급 크레딧" },
    ],
  },
  {
    id: "domestic_alt", label: "국내대체", color: "#86efac",
    indices: [
      { id: "kr_reit",     label: "국내 리츠",   desc: "부동산투자신탁 (부동산)" },
      { id: "kr_infra",    label: "국내 인프라", desc: "인프라·에너지 (부동산)" },
    ],
  },
  {
    id: "domestic_cash", label: "국내현금성", color: "#bbf7d0",
    indices: [
      { id: "kr_mmf",      label: "국내 MMF형",  desc: "머니마켓·단기채 ETF" },
      { id: "kr_cd",       label: "국내 CD금리", desc: "CD 91일물 연동" },
    ],
  },
  {
    id: "global_equity", label: "해외주식", color: "#60a5fa",
    indices: [
      { id: "sp500",        label: "S&P 500",     desc: "미국 대형주 500종목" },
      { id: "nasdaq100",    label: "NASDAQ 100",  desc: "미국 기술주 100종목" },
      { id: "us_dividend",  label: "미국 배당주", desc: "S&P 배당 귀족·고배당" },
      { id: "msci_world",   label: "MSCI World",  desc: "선진국 전체 주식" },
      { id: "msci_em",      label: "MSCI EM",     desc: "신흥국 주식" },
      { id: "eu_equity",    label: "유럽 주식",   desc: "유로존·범유럽 지수" },
      { id: "jp_equity",    label: "일본 주식",   desc: "Nikkei·TOPIX" },
      { id: "china_equity", label: "중국 주식",   desc: "CSI300·항셍 등" },
      { id: "india_equity", label: "인도 주식",   desc: "Nifty50·SENSEX" },
    ],
  },
  {
    id: "global_bond", label: "해외채권", color: "#93c5fd",
    indices: [
      { id: "us10y",    label: "미국채 10년",    desc: "미국 장기국채" },
      { id: "us30y",    label: "미국채 30년",    desc: "미국 초장기국채" },
      { id: "tips",     label: "미국 물가연동채", desc: "TIPS" },
      { id: "hy_bond",  label: "미국 하이일드",  desc: "고수익 회사채" },
      { id: "em_bond",  label: "신흥국 채권",    desc: "USD 표시 EM 국채" },
    ],
  },
  {
    id: "global_alt", label: "해외대체", color: "#c4b5fd",
    indices: [
      { id: "gold",        label: "금",          desc: "금 현물·선물 (원자재)" },
      { id: "silver",      label: "은",          desc: "은 현물·선물 (원자재)" },
      { id: "oil",         label: "원유",        desc: "WTI·브렌트 (원자재)" },
      { id: "commodity",   label: "원자재 종합", desc: "에너지·농산물·금속 (원자재)" },
      { id: "global_reit", label: "글로벌 리츠", desc: "선진국 부동산 (부동산)" },
      { id: "us_reit",     label: "미국 리츠",   desc: "미국 상업 부동산 (부동산)" },
      { id: "usd",         label: "달러화",      desc: "달러 인덱스·환헤지 (통화)" },
      { id: "jpy",         label: "엔화",        desc: "엔 선물·환 ETF (통화)" },
    ],
  },
  {
    id: "global_cash", label: "해외현금성", color: "#bfdbfe",
    indices: [
      { id: "us_mmf",   label: "미국 MMF형",   desc: "달러 단기채·T-Bill" },
      { id: "us_tbill", label: "미국 T-Bill",  desc: "미국 3개월 국채" },
    ],
  },
];

const PRESETS = {
  장기투자: { tracking: 50, discountRate: 20, aum: 30 },
  단기매매: { tracking: 20, discountRate: 50, aum: 30 },
  균형:     { tracking: 37, discountRate: 33, aum: 30 },
};

const FILTER_DEFAULTS = { minAum: 500, minDailyVolume: 10, minListingMonths: 6 };

const W_COLOR = { tracking: "#60a5fa", discountRate: "#34d399", aum: "#f59e0b" };
const W_LABEL = { tracking: "추적 오차", discountRate: "괴리율", aum: "순자산 규모" };

// ── 헬퍼 ──────────────────────────────────────────────────────
function findIndexMeta(indexId) {
  for (const theme of THEME_CATALOG) {
    const found = theme.indices.find(i => i.id === indexId);
    if (found) return { ...found, themeColor: theme.color };
  }
  return null;
}

function percentileScore(value, allValues, lowerIsBetter) {
  const sorted = [...allValues].sort((a, b) => a - b);
  const below  = sorted.filter(v => v < value).length;
  const pct    = below / Math.max(sorted.length - 1, 1);
  return lowerIsBetter ? (1 - pct) * 100 : pct * 100;
}

function computeScores(etfs, weights, filters) {
  const passing = etfs.filter(e =>
    e.aum           >= filters.minAum &&
    e.dailyVolume   >= filters.minDailyVolume &&
    e.listingMonths >= filters.minListingMonths
  );
  if (passing.length === 0) return { results: [], filtered: etfs };

  const tVals  = passing.map(e => e.trackingError);
  const drVals = passing.map(e => Math.abs(e.discountRate));
  const aVals  = passing.map(e => e.aum);

  const results = passing.map(e => {
    const tScore = percentileScore(e.trackingError,          tVals,  true);
    const sScore = percentileScore(Math.abs(e.discountRate), drVals, true);
    const aScore = percentileScore(e.aum,                    aVals,  false);
    const total  = (tScore * weights.tracking + sScore * weights.discountRate + aScore * weights.aum) / 100;
    return { ...e, tScore, sScore, aScore, total };
  }).sort((a, b) => b.total - a.total);

  const passingNames = new Set(passing.map(e => e.name));
  return { results, filtered: etfs.filter(e => !passingNames.has(e.name)) };
}

// ── 서브 컴포넌트 ──────────────────────────────────────────────
function ScoreRing({ score }) {
  const r = 20, circ = 2 * Math.PI * r;
  const dash  = (score / 100) * circ;
  const color = score >= 70 ? "#4ade80" : score >= 40 ? "#facc15" : "#f87171";
  return (
    <svg width={52} height={52} style={{ transform: "rotate(-90deg)", flexShrink: 0 }}>
      <circle cx={26} cy={26} r={r} fill="none" stroke="#1e2235" strokeWidth={5} />
      <circle cx={26} cy={26} r={r} fill="none" stroke={color} strokeWidth={5}
        strokeDasharray={`${dash} ${circ}`} strokeLinecap="round"
        style={{ transition: "stroke-dasharray .7s cubic-bezier(.4,0,.2,1)" }} />
      <text x={26} y={30} textAnchor="middle" fill={color}
        style={{ transform: "rotate(90deg) translate(0,-52px)", fontSize: 12, fontWeight: 700, fontFamily: "monospace" }}>
        {Math.round(score)}
      </text>
    </svg>
  );
}

function MiniBar({ value, color }) {
  return (
    <div style={{ background: "#1e2235", borderRadius: 3, height: 5, width: "100%", overflow: "hidden" }}>
      <div style={{ height: "100%", width: `${value}%`, background: color, borderRadius: 3, transition: "width .5s ease" }} />
    </div>
  );
}

function Badge({ children, color = "#334155", text = "#94a3b8" }) {
  return (
    <span style={{ fontSize: 10, padding: "2px 7px", borderRadius: 4, background: color, color: text, whiteSpace: "nowrap" }}>
      {children}
    </span>
  );
}

function Input({ label, value, onChange, type = "number" }) {
  return (
    <div>
      <div style={{ fontSize: 11, color: "#475569", marginBottom: 4 }}>{label}</div>
      <input type={type} value={value} onChange={e => onChange(e.target.value)}
        style={{
          width: "100%", background: "#0d0f1e", border: "1px solid #1e2235",
          borderRadius: 6, color: "#e2e8f0", padding: "8px 10px",
          fontSize: 13, fontFamily: "inherit", outline: "none", boxSizing: "border-box",
        }} />
    </div>
  );
}

// ── 메인 컴포넌트 ─────────────────────────────────────────────
export default function ETFPicker() {
  // 선택 상태
  const [selectedTheme, setSelectedTheme] = useState(null);
  const [selectedIndex, setSelectedIndex] = useState(null);

  // 전체 JSON 데이터 { indexId: ETF[] }
  const [allData, setAllData]     = useState(null);
  const [dataStatus, setDataStatus] = useState("idle"); // idle | loading | ok | error
  const [updatedAt, setUpdatedAt]   = useState(null);

  // 수동 추가 (현재 지수에만 적용)
  const [manualEtf, setManualEtf] = useState({ name:"", trackingError:"", discountRate:"", aum:"", dailyVolume:"", listingMonths:"" });
  const [manualOverrides, setManualOverrides] = useState({}); // { indexId: ETF[] }

  // 스코어링 설정
  const [weights, setWeights]           = useState(PRESETS["균형"]);
  const [filters, setFilters]           = useState(FILTER_DEFAULTS);
  const [selectedPreset, setSelectedPreset] = useState("균형");
  const [activeTab, setActiveTab]       = useState("score");
  const [sensitivity, setSensitivity]   = useState(false);

  // ── JSON 로드 (마운트 시 1회) ──
  useEffect(() => {
    setDataStatus("loading");
    fetch(DATA_URL)
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then(json => {
        setAllData(json.data ?? json);
        setUpdatedAt(json.updatedAt ?? null);
        setDataStatus("ok");
      })
      .catch(() => setDataStatus("error"));
  }, []);

  // 현재 지수의 ETF 목록 (JSON + 수동 추가 병합)
  const currentEtfs = useMemo(() => {
    if (!selectedIndex) return [];
    const base     = (allData?.[selectedIndex] ?? []);
    const overrides = (manualOverrides[selectedIndex] ?? []);
    return [...base, ...overrides];
  }, [selectedIndex, allData, manualOverrides]);

  const { results, filtered } = useMemo(
    () => computeScores(currentEtfs, weights, filters),
    [currentEtfs, weights, filters]
  );

  const currentTheme    = THEME_CATALOG.find(t => t.id === selectedTheme);
  const currentIndexMeta = findIndexMeta(selectedIndex);

  // ── 가중치 조정 ──
  const handleWeightChange = (key, raw) => {
    const v      = Math.max(0, Math.min(100, Number(raw)));
    const others = Object.keys(weights).filter(k => k !== key);
    const otherSum = others.reduce((s, k) => s + weights[k], 0);
    const newW   = { ...weights, [key]: v };
    if (otherSum > 0) {
      others.forEach(k => { newW[k] = Math.round((weights[k] / otherSum) * (100 - v)); });
      const diff = 100 - Object.values(newW).reduce((s, x) => s + x, 0);
      newW[others[others.length - 1]] += diff;
    }
    setWeights(newW);
    setSelectedPreset(null);
  };

  // ── 수동 ETF 추가 ──
  const addManual = () => {
    if (!manualEtf.name || !selectedIndex) return;
    const entry = {
      name:          manualEtf.name,
      trackingError: parseFloat(manualEtf.trackingError) || 0,
      discountRate:  parseFloat(manualEtf.discountRate)  || 0,
      aum:           parseFloat(manualEtf.aum)           || 0,
      dailyVolume:   parseFloat(manualEtf.dailyVolume)   || 0,
      listingMonths: parseInt(manualEtf.listingMonths)   || 0,
      manual: true,
    };
    setManualOverrides(prev => ({
      ...prev,
      [selectedIndex]: [...(prev[selectedIndex] ?? []), entry],
    }));
    setManualEtf({ name:"", trackingError:"", discountRate:"", aum:"", dailyVolume:"", listingMonths:"" });
  };

  const removeEtf = (name) => {
    // 수동 추가 항목만 삭제 가능
    setManualOverrides(prev => ({
      ...prev,
      [selectedIndex]: (prev[selectedIndex] ?? []).filter(e => e.name !== name),
    }));
  };

  // ── 민감도 분석 ──
  const sensitivityData = useMemo(() => {
    if (!sensitivity || results.length === 0) return null;
    return Object.entries(PRESETS).map(([label, w]) => ({
      label,
      scores: computeScores(currentEtfs, w, filters).results.map((e, i) => ({ name: e.name, rank: i + 1 })),
    }));
  }, [sensitivity, currentEtfs, filters, results]);

  const hasSelection = !!selectedIndex;

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  return (
    <div style={{ minHeight: "100vh", background: "#080c18", color: "#e2e8f0", fontFamily: "'DM Mono', monospace" }}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Syne:wght@700;800&display=swap" rel="stylesheet" />

      {/* ── 헤더 ── */}
      <div style={{ background: "linear-gradient(180deg,#0d1122 0%,#080c18 100%)", borderBottom: "1px solid #141928", padding: "28px 20px 20px" }}>
        <div style={{ maxWidth: 880, margin: "0 auto" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
            <div style={{ width: 4, height: 28, background: "linear-gradient(180deg,#60a5fa,#34d399)", borderRadius: 2 }} />
            <h1 style={{ margin: 0, fontFamily: "'Syne',sans-serif", fontWeight: 800, fontSize: 24, color: "#f0f6ff", letterSpacing: "-0.3px" }}>
              ETF Picker
            </h1>
          </div>
          {/* 데이터 상태 표시 */}
          <div style={{ marginLeft: 14, fontSize: 11, color: "#334155", display: "flex", gap: 12, alignItems: "center" }}>
            {dataStatus === "loading" && <span style={{ color: "#475569" }}>⏳ 데이터 로딩 중…</span>}
            {dataStatus === "ok"      && <span style={{ color: "#4ade80" }}>● 데이터 정상</span>}
            {dataStatus === "error"   && <span style={{ color: "#f87171" }}>● 데이터 로드 실패 — 수동 입력 사용</span>}
            {updatedAt && <span style={{ color: "#1e2235" }}>최종 업데이트: {updatedAt}</span>}
          </div>
        </div>
      </div>

      <div style={{ maxWidth: 880, margin: "0 auto", padding: "20px 16px 60px" }}>

        {/* ── 지수 선택 패널 ── */}
        <div style={{ background: "#0d1122", border: "1px solid #141928", borderRadius: 14, padding: 20, marginBottom: 20 }}>

          {/* 테마 버튼 */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 14 }}>
            {THEME_CATALOG.map(theme => {
              const isActive = selectedTheme === theme.id;
              return (
                <button key={theme.id}
                  onClick={() => { setSelectedTheme(theme.id); setSelectedIndex(null); }}
                  style={{
                    padding: "6px 13px", border: `1px solid ${isActive ? theme.color + "66" : "#1e2235"}`,
                    borderRadius: 20, background: isActive ? `${theme.color}18` : "transparent",
                    color: isActive ? theme.color : "#475569",
                    fontSize: 12, cursor: "pointer", fontFamily: "inherit", transition: "all .18s",
                  }}>
                  {theme.label}
                </button>
              );
            })}
          </div>

          {/* 지수 드롭다운 */}
          {selectedTheme && (
            <select value={selectedIndex || ""}
              onChange={e => { setSelectedIndex(e.target.value || null); setActiveTab("score"); }}
              style={{
                width: "100%", background: "#080c18",
                border: `1px solid ${currentTheme?.color + "44" || "#1e2235"}`,
                borderRadius: 8, color: selectedIndex ? "#e2e8f0" : "#475569",
                padding: "10px 12px", fontSize: 13, fontFamily: "inherit", outline: "none",
                cursor: "pointer", appearance: "none",
                backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23475569' d='M6 8L1 3h10z'/%3E%3C/svg%3E")`,
                backgroundRepeat: "no-repeat", backgroundPosition: "right 12px center",
              }}>
              <option value="">— 지수를 선택하세요 —</option>
              {currentTheme?.indices.map(idx => {
                const hasData = !!(allData?.[idx.id]?.length);
                return (
                  <option key={idx.id} value={idx.id}>
                    {idx.label}  ({idx.desc}){hasData ? "  ✓" : ""}
                  </option>
                );
              })}
            </select>
          )}
        </div>

        {/* ── 선택 없을 때 안내 ── */}
        {!hasSelection && (
          <div style={{ textAlign: "center", color: "#1e2235", padding: "60px 0", fontSize: 14 }}>
            위에서 테마 → 지수를 선택하면 분석이 시작됩니다.
          </div>
        )}

        {/* ── 메인 탭 영역 ── */}
        {hasSelection && (
          <>
            {/* 탭 */}
            <div style={{ display: "flex", gap: 4, background: "#0d1122", borderRadius: 10, padding: 4, marginBottom: 20 }}>
              {[["score","📊 스코어"],["config","⚙ 가중치"],["data","📋 데이터"]].map(([k,l]) => (
                <button key={k} onClick={() => setActiveTab(k)} style={{
                  flex: 1, padding: "9px 0", border: "none", borderRadius: 7, cursor: "pointer",
                  background: activeTab === k ? "#141928" : "transparent",
                  color: activeTab === k ? "#93c5fd" : "#475569",
                  fontSize: 13, fontFamily: "inherit", transition: "all .2s",
                }}>{l}</button>
              ))}
            </div>

            {/* ── 스코어 탭 ── */}
            {activeTab === "score" && (
              <div>
                {filtered.length > 0 && (
                  <div style={{ background:"#1c0a0a", border:"1px solid #7f1d1d", borderRadius:8, padding:"10px 14px", marginBottom:14, fontSize:12 }}>
                    <span style={{ color:"#f87171" }}>⚠ 필터 탈락 {filtered.length}개</span>
                    <span style={{ color:"#64748b", marginLeft:8 }}>{filtered.map(e=>e.name).join(" · ")}</span>
                  </div>
                )}

                {currentEtfs.length === 0 ? (
                  <div style={{ textAlign:"center", color:"#334155", padding:"60px 0", fontSize:13, lineHeight:1.8 }}>
                    {dataStatus === "error"
                      ? "데이터를 불러오지 못했습니다.\n데이터 탭에서 수동으로 입력하세요."
                      : dataStatus === "loading"
                      ? "데이터 로딩 중입니다…"
                      : "이 지수에 해당하는 ETF 데이터가 없습니다.\n데이터 탭에서 직접 추가할 수 있습니다."}
                  </div>
                ) : results.length === 0 ? (
                  <div style={{ textAlign:"center", color:"#475569", padding:"60px 0", fontSize:13 }}>
                    필터 기준을 통과한 ETF가 없습니다.<br />
                    <span style={{ fontSize:12 }}>가중치 탭에서 필터 기준을 완화하세요.</span>
                  </div>
                ) : (
                  <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
                    {results.map((e, i) => (
                      <div key={e.name} style={{
                        background: i === 0 ? "#0e1628" : "#0d1122",
                        border: `1px solid ${i === 0 ? "#1e3a5f" : "#141928"}`,
                        borderRadius: 12, padding: "18px 18px 14px",
                        transition: "transform .15s",
                      }}
                        onMouseEnter={el => el.currentTarget.style.transform = "translateY(-1px)"}
                        onMouseLeave={el => el.currentTarget.style.transform = "translateY(0)"}
                      >
                        <div style={{ display:"flex", alignItems:"center", gap:14, marginBottom:14 }}>
                          <span style={{ fontSize:12, color:"#334155", minWidth:22 }}>#{i+1}</span>
                          <ScoreRing score={e.total} />
                          <div style={{ flex:1, minWidth:0 }}>
                            <div style={{ display:"flex", alignItems:"center", gap:8, flexWrap:"wrap", marginBottom:3 }}>
                              <span style={{ fontSize:14, fontWeight:500, color:"#f0f6ff" }}>{e.name}</span>
                              {e.manual && <Badge color="#0c1a10" text="#34d399">수동입력</Badge>}
                              {i === 0   && <Badge color="#0c1a30" text="#60a5fa">BEST</Badge>}
                            </div>
                            <div style={{ fontSize:11, color:"#334155" }}>
                              추적 오차 {e.trackingError}% · 괴리율 {e.discountRate}% · 순자산 {e.aum?.toLocaleString()}억 · 거래대금 {e.dailyVolume}억
                            </div>
                          </div>
                        </div>
                        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:10 }}>
                          {[
                            ["추적 오차", e.tScore, W_COLOR.tracking],
                            ["괴리율",   e.sScore, W_COLOR.discountRate],
                            ["순자산",   e.aScore, W_COLOR.aum],
                          ].map(([lbl, sc, col]) => (
                            <div key={lbl}>
                              <div style={{ display:"flex", justifyContent:"space-between", fontSize:11, color:"#475569", marginBottom:4 }}>
                                <span>{lbl}</span><span style={{ color:col }}>{Math.round(sc)}</span>
                              </div>
                              <MiniBar value={sc} color={col} />
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* 민감도 분석 */}
                {results.length > 0 && (
                  <div style={{ marginTop:20 }}>
                    <button onClick={() => setSensitivity(!sensitivity)} style={{
                      background:"transparent", border:"1px solid #141928", borderRadius:7,
                      padding:"8px 14px", color:"#475569", fontSize:12, cursor:"pointer", fontFamily:"inherit",
                    }}>
                      {sensitivity ? "▲ 민감도 분석 닫기" : "▼ 가중치 민감도 분석"}
                    </button>
                    {sensitivity && sensitivityData && (
                      <div style={{ marginTop:10, background:"#0d1122", border:"1px solid #141928", borderRadius:12, overflow:"hidden" }}>
                        <div style={{ padding:"12px 18px", borderBottom:"1px solid #141928", fontSize:11, color:"#475569" }}>
                          가중치를 바꿔도 순위가 일정한 ETF → 진짜 좋은 ETF
                        </div>
                        <div style={{ overflowX:"auto" }}>
                          <table style={{ width:"100%", borderCollapse:"collapse", fontSize:12 }}>
                            <thead>
                              <tr style={{ background:"#080c18" }}>
                                <th style={{ padding:"9px 18px", textAlign:"left", color:"#334155", fontWeight:400 }}>ETF명</th>
                                {sensitivityData.map(r => (
                                  <th key={r.label} style={{ padding:"9px 12px", textAlign:"center", color:"#334155", fontWeight:400 }}>{r.label}</th>
                                ))}
                                <th style={{ padding:"9px 12px", textAlign:"center", color:"#334155", fontWeight:400 }}>안정성</th>
                              </tr>
                            </thead>
                            <tbody>
                              {results.map(etf => {
                                const ranks = sensitivityData.map(r => {
                                  const f = r.scores.find(s => s.name === etf.name);
                                  return f ? f.rank : null;
                                });
                                const valid  = ranks.filter(Boolean);
                                const stable = valid.length > 0 && Math.max(...valid) - Math.min(...valid) <= 1;
                                return (
                                  <tr key={etf.name} style={{ borderTop:"1px solid #141928" }}>
                                    <td style={{ padding:"9px 18px", color:"#94a3b8" }}>{etf.name}</td>
                                    {ranks.map((r,i) => (
                                      <td key={i} style={{ padding:"9px 12px", textAlign:"center", color: r===1?"#4ade80":"#475569" }}>
                                        {r ? `#${r}` : "—"}
                                      </td>
                                    ))}
                                    <td style={{ padding:"9px 12px", textAlign:"center" }}>
                                      <Badge color={stable?"#052e16":"#1c1917"} text={stable?"#4ade80":"#64748b"}>
                                        {stable ? "안정" : "변동"}
                                      </Badge>
                                    </td>
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* ── 가중치 탭 ── */}
            {activeTab === "config" && (
              <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
                {/* 프리셋 */}
                <div style={{ background:"#0d1122", border:"1px solid #141928", borderRadius:12, padding:18 }}>
                  <div style={{ fontSize:11, color:"#475569", letterSpacing:"0.1em", marginBottom:12 }}>가중치 프리셋</div>
                  <div style={{ display:"flex", gap:8 }}>
                    {Object.keys(PRESETS).map(p => (
                      <button key={p} onClick={() => { setWeights(PRESETS[p]); setSelectedPreset(p); }} style={{
                        flex:1, padding:"9px 0",
                        border:`1px solid ${selectedPreset===p?"#1e3a5f":"#141928"}`,
                        borderRadius:7, background: selectedPreset===p?"#0e1628":"transparent",
                        color: selectedPreset===p?"#93c5fd":"#475569",
                        fontSize:13, cursor:"pointer", fontFamily:"inherit", transition:"all .2s",
                      }}>{p}</button>
                    ))}
                  </div>
                </div>

                {/* 슬라이더 */}
                <div style={{ background:"#0d1122", border:"1px solid #141928", borderRadius:12, padding:18 }}>
                  <div style={{ fontSize:11, color:"#475569", letterSpacing:"0.1em", marginBottom:16 }}>가중치 직접 조정 (합계 100%)</div>
                  {Object.entries(weights).map(([key, val]) => (
                    <div key={key} style={{ marginBottom:18 }}>
                      <div style={{ display:"flex", justifyContent:"space-between", marginBottom:6 }}>
                        <span style={{ fontSize:13, color:W_COLOR[key] }}>{W_LABEL[key]}</span>
                        <span style={{ fontSize:13, color:"#e2e8f0" }}>{val}%</span>
                      </div>
                      <input type="range" min={0} max={100} value={val}
                        onChange={e => handleWeightChange(key, e.target.value)}
                        style={{ width:"100%", accentColor:W_COLOR[key], cursor:"pointer" }} />
                      <div style={{ fontSize:11, color:"#1e2235", marginTop:3 }}>
                        {key==="tracking"     && "추적 오차: 장기 성과 편차. 수수료 효과를 내포."}
                        {key==="discountRate" && "괴리율: NAV 대비 시장가 괴리. 절댓값 기준으로 평가."}
                        {key==="aum"          && "순자산 규모: ETF 지속 가능성과 안정성 반영."}
                      </div>
                    </div>
                  ))}
                  <div style={{ display:"flex", gap:4, height:6, borderRadius:3, overflow:"hidden" }}>
                    {Object.entries(weights).map(([key, val]) => (
                      <div key={key} style={{ flex:val, background:W_COLOR[key], transition:"flex .3s" }} />
                    ))}
                  </div>
                </div>

                {/* 필터 */}
                <div style={{ background:"#0d1122", border:"1px solid #141928", borderRadius:12, padding:18 }}>
                  <div style={{ fontSize:11, color:"#475569", letterSpacing:"0.1em", marginBottom:14 }}>최소 기준 필터</div>
                  {[
                    ["minAum",          "최소 순자산 (억원)",       "500억 미만 → ETF 폐지 리스크"],
                    ["minDailyVolume",  "최소 일평균 거래대금 (억원)", "10억 미만 → 유동성 부족"],
                    ["minListingMonths","최소 상장 기간 (개월)",     "6개월 미만 → 데이터 부족"],
                  ].map(([k,l,h]) => (
                    <div key={k} style={{ marginBottom:14 }}>
                      <Input label={l} value={filters[k]} onChange={v => setFilters({...filters,[k]:Number(v)})} />
                      <div style={{ fontSize:11, color:"#1e2235", marginTop:3 }}>{h}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* ── 데이터 탭 ── */}
            {activeTab === "data" && (
              <div style={{ display:"flex", flexDirection:"column", gap:16 }}>

                {/* ETF 목록 */}
                <div style={{ background:"#0d1122", border:"1px solid #141928", borderRadius:12, overflow:"hidden" }}>
                  <div style={{ padding:"12px 18px", borderBottom:"1px solid #141928", fontSize:11, color:"#475569", letterSpacing:"0.08em" }}>
                    {currentIndexMeta?.label} — {currentEtfs.length}개 ETF
                    {updatedAt && <span style={{ marginLeft:8, color:"#1e2235" }}>({updatedAt} 기준)</span>}
                  </div>
                  {currentEtfs.length === 0 ? (
                    <div style={{ padding:"28px", textAlign:"center", color:"#1e2235", fontSize:13 }}>
                      데이터 없음 — 아래에서 수동으로 추가하세요.
                    </div>
                  ) : currentEtfs.map(e => {
                    const isOut = e.aum < filters.minAum || e.dailyVolume < filters.minDailyVolume || e.listingMonths < filters.minListingMonths;
                    return (
                      <div key={e.name} style={{ display:"flex", alignItems:"center", padding:"11px 18px", borderBottom:"1px solid #0d1122", gap:10 }}>
                        <div style={{ flex:1, minWidth:0 }}>
                          <div style={{ display:"flex", alignItems:"center", gap:6, flexWrap:"wrap" }}>
                            <span style={{ fontSize:13, color: isOut?"#334155":"#94a3b8" }}>{e.name}</span>
                            {e.manual && <Badge color="#0c1a10" text="#34d399">수동입력</Badge>}
                            {isOut     && <Badge color="#1c0a0a" text="#ef4444">필터 탈락</Badge>}
                          </div>
                          <div style={{ fontSize:11, color:"#1e2235", marginTop:2 }}>
                            추적오차 {e.trackingError}% · 괴리율 {e.discountRate}% · 순자산 {e.aum?.toLocaleString()}억 · 거래대금 {e.dailyVolume}억 · {e.listingMonths}개월
                          </div>
                        </div>
                        {e.manual && (
                          <button onClick={() => removeEtf(e.name)} style={{
                            background:"transparent", border:"1px solid #2d1515", borderRadius:5,
                            color:"#7f1d1d", padding:"3px 9px", fontSize:11, cursor:"pointer", fontFamily:"inherit",
                          }}>삭제</button>
                        )}
                      </div>
                    );
                  })}
                </div>

                {/* 수동 추가 */}
                <div style={{ background:"#0d1122", border:"1px solid #141928", borderRadius:12, padding:18 }}>
                  <div style={{ fontSize:11, color:"#475569", letterSpacing:"0.1em", marginBottom:14 }}>ETF 수동 추가</div>
                  <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:10, marginBottom:12 }}>
                    <div style={{ gridColumn:"1 / -1" }}>
                      <Input label="ETF명" value={manualEtf.name} onChange={v => setManualEtf({...manualEtf,name:v})} type="text" />
                    </div>
                    <Input label="추적 오차 (%)"       value={manualEtf.trackingError} onChange={v => setManualEtf({...manualEtf,trackingError:v})} />
                    <Input label="괴리율 (%)"          value={manualEtf.discountRate}  onChange={v => setManualEtf({...manualEtf,discountRate:v})} />
                    <Input label="순자산 (억원)"        value={manualEtf.aum}           onChange={v => setManualEtf({...manualEtf,aum:v})} />
                    <Input label="일평균 거래대금 (억원)" value={manualEtf.dailyVolume}   onChange={v => setManualEtf({...manualEtf,dailyVolume:v})} />
                    <div style={{ gridColumn:"1 / -1" }}>
                      <Input label="상장 기간 (개월)" value={manualEtf.listingMonths} onChange={v => setManualEtf({...manualEtf,listingMonths:v})} />
                    </div>
                  </div>
                  <button onClick={addManual} style={{
                    width:"100%", padding:"11px 0",
                    background:"linear-gradient(135deg,#1e3a5f,#1a4731)",
                    border:"1px solid #1e3a5f", borderRadius:8, color:"#93c5fd",
                    fontSize:13, cursor:"pointer", fontFamily:"inherit", letterSpacing:"0.04em",
                  }}>+ 추가</button>
                </div>

                <div style={{ fontSize:11, color:"#1e2235", lineHeight:1.8, padding:"0 2px" }}>
                  ※ 데이터는 매일 오전 8시(KST) pykrx를 통해 KRX에서 자동 갱신됩니다.<br />
                  ※ 수동 입력 항목은 현재 세션에서만 유지됩니다.<br />
                  ※ 동일 지수 추종 ETF끼리만 비교해야 의미 있습니다.
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
