const now = new Date();

const baseStocks = [
  {
    symbol: "002594.SZ",
    name: "比亚迪",
    market: "A",
    marketLabel: "A 股",
    currency: "CNY",
    price: 214.36,
    change: 2.8,
    action: "重点观察",
    score: 82,
    lagMinutes: 1,
    freshnessStatus: "fresh",
    truthScore: 88,
    factors: { 基本面: 84, 估值: 63, 技术: 79, 催化: 86, 情绪: 74, 风险: 68 },
    spark: [188, 191, 190, 196, 201, 199, 204, 209, 207, 214],
    thesis: "趋势和催化同时偏强，估值不算便宜，适合进入观察池并等待成交量确认。若真实行情或公告源过期，结论自动降级。",
    reasons: ["行业景气与订单催化较强", "价格站上关键均线，成交额同步放大", "估值处于中性偏高区间"],
    risks: ["估值容错较低", "行业政策和价格战会放大波动"],
    evidence: [
      { tier: "S", source: "交易所公告", claim: "近期公告未发现停牌或重大风险提示", confidence: 0.93 },
      { tier: "A", source: "财务数据", claim: "收入和现金流质量维持正向", confidence: 0.84 },
      { tier: "B", source: "新闻情绪", claim: "行业订单和出口话题热度上升", confidence: 0.72 }
    ],
    reflection: [
      { round: "第 1 轮", label: "数据闸门", status: "pass", text: "行情延迟 1 分钟，财务和公告字段完整，可继续分析。" },
      { round: "第 2 轮", label: "证据闸门", status: "pass", text: "主要 claim 有公告或结构化财务支撑，情绪仅作辅助。" },
      { round: "第 3 轮", label: "投资逻辑", status: "warn", text: "逻辑成立但估值偏高，动作从小仓试探降级为重点观察。" }
    ]
  },
  {
    symbol: "0700.HK",
    name: "腾讯控股",
    market: "HK",
    marketLabel: "港股",
    currency: "HKD",
    price: 391.8,
    change: 1.4,
    action: "等待回踩",
    score: 78,
    lagMinutes: 8,
    freshnessStatus: "fresh",
    truthScore: 84,
    factors: { 基本面: 86, 估值: 70, 技术: 67, 催化: 72, 情绪: 76, 风险: 74 },
    spark: [370, 374, 377, 381, 386, 383, 388, 392, 389, 391],
    thesis: "基本面稳健，短线价格已接近压力区，当前更适合等待回踩或业绩催化确认。",
    reasons: ["盈利质量和现金流稳定", "回购与业务韧性支持估值", "短线技术位置不够从容"],
    risks: ["监管和平台经济政策扰动", "港股流动性和汇率波动"],
    evidence: [
      { tier: "S", source: "HKEXnews 公告", claim: "公告源可追溯，未发现冲突信息", confidence: 0.91 },
      { tier: "A", source: "公司财务", claim: "利润率稳定，现金流良好", confidence: 0.82 },
      { tier: "B", source: "财经新闻", claim: "回购和 AI 业务话题带动情绪", confidence: 0.68 }
    ],
    reflection: [
      { round: "第 1 轮", label: "数据闸门", status: "pass", text: "港股行情延迟 8 分钟，仍在数据闸门阈值内。" },
      { round: "第 2 轮", label: "证据闸门", status: "pass", text: "公司动作以 HKEXnews 公告为核心证据，新闻未单独触发结论。" },
      { round: "第 3 轮", label: "投资逻辑", status: "warn", text: "基本面支持持有观察，但技术面追价性价比不足。" }
    ]
  },
  {
    symbol: "NVDA",
    name: "NVIDIA",
    market: "US",
    marketLabel: "美股",
    currency: "USD",
    price: 118.64,
    change: -0.9,
    action: "持有复核",
    score: 80,
    lagMinutes: 18,
    freshnessStatus: "warn",
    truthScore: 81,
    factors: { 基本面: 91, 估值: 48, 技术: 73, 催化: 88, 情绪: 82, 风险: 54 },
    spark: [104, 109, 113, 117, 121, 119, 123, 126, 120, 118],
    thesis: "基本面和催化很强，但估值与波动风险同样突出。若用于建仓，必须有仓位上限和失效条件。",
    reasons: ["AI 算力需求仍是强催化", "估值分位较高，安全边际不足", "短期波动放大，需要等待确认"],
    risks: ["高估值回撤", "供应链和出口限制", "预期过热"],
    evidence: [
      { tier: "S", source: "SEC EDGAR 披露", claim: "财报字段完整，可核验收入和利润", confidence: 0.9 },
      { tier: "A", source: "结构化基本面", claim: "增长和毛利率维持高位", confidence: 0.86 },
      { tier: "B", source: "新闻情绪", claim: "AI 芯片需求叙事仍强", confidence: 0.7 }
    ],
    reflection: [
      { round: "第 1 轮", label: "数据闸门", status: "warn", text: "美股当前按上一交易日数据分析，盘前/盘中需要刷新。" },
      { round: "第 2 轮", label: "证据闸门", status: "pass", text: "核心财务 claim 来自 SEC EDGAR，新闻情绪只做辅助。" },
      { round: "第 3 轮", label: "投资逻辑", status: "warn", text: "强趋势与高估值并存，动作保留为持有复核。" }
    ]
  },
  {
    symbol: "600519.SH",
    name: "贵州茅台",
    market: "A",
    marketLabel: "A 股",
    currency: "CNY",
    price: 1518.2,
    change: -1.7,
    action: "减仓观察",
    score: 61,
    lagMinutes: 2,
    freshnessStatus: "fresh",
    truthScore: 79,
    factors: { 基本面: 82, 估值: 55, 技术: 42, 催化: 46, 情绪: 38, 风险: 62 },
    spark: [1620, 1608, 1599, 1570, 1556, 1562, 1540, 1531, 1522, 1518],
    thesis: "基本面质量仍强，但技术面和情绪转弱，若已持有应复核核心假设和仓位暴露。",
    reasons: ["盈利质量仍有支撑", "趋势弱化，缺少短期催化", "消费预期和估值分歧扩大"],
    risks: ["需求预期下修", "高股价流动性影响仓位管理"],
    evidence: [
      { tier: "S", source: "交易所公告", claim: "公告源未出现硬性利空", confidence: 0.88 },
      { tier: "A", source: "财务数据", claim: "盈利质量仍高", confidence: 0.8 },
      { tier: "B", source: "情绪数据", claim: "消费板块情绪偏弱", confidence: 0.62 }
    ],
    reflection: [
      { round: "第 1 轮", label: "数据闸门", status: "pass", text: "关键行情和财务字段可用。" },
      { round: "第 2 轮", label: "证据闸门", status: "warn", text: "负面情绪主要来自新闻和价格行为，未见公告级别硬利空。" },
      { round: "第 3 轮", label: "投资逻辑", status: "warn", text: "卖出理由不能只靠短线下跌，建议减仓观察而非直接退出。" }
    ]
  },
  {
    symbol: "1810.HK",
    name: "小米集团",
    market: "HK",
    marketLabel: "港股",
    currency: "HKD",
    price: 29.72,
    change: 3.1,
    action: "重点观察",
    score: 76,
    lagMinutes: 22,
    freshnessStatus: "warn",
    truthScore: 73,
    factors: { 基本面: 70, 估值: 66, 技术: 81, 催化: 82, 情绪: 79, 风险: 57 },
    spark: [24, 25, 25.7, 26.5, 27.4, 26.8, 28.1, 28.9, 29.2, 29.7],
    thesis: "催化和技术面较强，但部分情绪来自市场传闻，必须用公告和销量数据核验。",
    reasons: ["智能硬件和汽车业务催化明显", "趋势强于港股大盘", "情绪热度高但未证实比例偏高"],
    risks: ["新业务估值波动", "传闻驱动导致追高风险"],
    evidence: [
      { tier: "S", source: "HKEXnews 公告", claim: "公告字段可追溯", confidence: 0.86 },
      { tier: "B", source: "新闻情绪", claim: "汽车业务话题热度上升", confidence: 0.66 },
      { tier: "C", source: "社媒热度", claim: "短线讨论度快速上升", confidence: 0.38 }
    ],
    reflection: [
      { round: "第 1 轮", label: "数据闸门", status: "warn", text: "行情延迟 22 分钟，接近数据闸门阈值上限。" },
      { round: "第 2 轮", label: "证据闸门", status: "warn", text: "催化中有传闻成分，未证实比例偏高。" },
      { round: "第 3 轮", label: "投资逻辑", status: "warn", text: "保留观察，不升级为买入候选。" }
    ]
  },
  {
    symbol: "AAPL",
    name: "Apple",
    market: "US",
    marketLabel: "美股",
    currency: "USD",
    price: 203.44,
    change: 0.4,
    action: "等待催化",
    score: 69,
    lagMinutes: 20,
    freshnessStatus: "warn",
    truthScore: 83,
    factors: { 基本面: 78, 估值: 58, 技术: 62, 催化: 55, 情绪: 64, 风险: 75 },
    spark: [197, 199, 198, 201, 203, 204, 202, 205, 204, 203],
    thesis: "质量稳定但短期催化不强，适合放在关注池等待财报、产品或回购信息确认。",
    reasons: ["现金流和回购能力强", "增长催化不够清晰", "风险相对可控"],
    risks: ["估值和增长匹配度", "新品周期不确定"],
    evidence: [
      { tier: "S", source: "SEC EDGAR 披露", claim: "财务披露完整", confidence: 0.9 },
      { tier: "A", source: "公司 IR", claim: "回购和现金流可核验", confidence: 0.82 },
      { tier: "B", source: "新闻情绪", claim: "产品周期讨论度中性", confidence: 0.64 }
    ],
    reflection: [
      { round: "第 1 轮", label: "数据闸门", status: "warn", text: "美股按上一交易日数据，盘中需刷新。" },
      { round: "第 2 轮", label: "证据闸门", status: "pass", text: "财务和回购 claim 有较高等级证据。" },
      { round: "第 3 轮", label: "投资逻辑", status: "pass", text: "结论与证据匹配：等待催化，暂不追高。" }
    ]
  }
];

const metricProfiles = {
  "002594.SZ": {
    avgAmountCny: 12800000000,
    turnoverRate: 2.1,
    spreadBps: 4,
    pe: 24.8,
    pePercentile: 68,
    pb: 4.2,
    roe: 18.6,
    revenueGrowth: 21.4,
    fcfMargin: 6.1,
    debtRatio: 52,
    volumeRatio: 1.48,
    ma20GapPct: 5.6,
    atrPct: 3.2,
    catalystScore: 86,
    newsCount72h: 18,
    verifiedCatalystRatio: 0.78,
    sentimentScore: 42,
    unverifiedRatio: 0.19,
    volatility20d: 28,
    maxDrawdown60d: 12
  },
  "0700.HK": {
    avgAmountCny: 9600000000,
    turnoverRate: 0.62,
    spreadBps: 5,
    pe: 18.7,
    pePercentile: 54,
    pb: 3.8,
    roe: 20.4,
    revenueGrowth: 9.8,
    fcfMargin: 18.2,
    debtRatio: 38,
    volumeRatio: 1.08,
    ma20GapPct: 2.4,
    atrPct: 2.6,
    catalystScore: 72,
    newsCount72h: 23,
    verifiedCatalystRatio: 0.81,
    sentimentScore: 36,
    unverifiedRatio: 0.16,
    volatility20d: 21,
    maxDrawdown60d: 9
  },
  NVDA: {
    avgAmountCny: 196000000000,
    turnoverRate: 1.35,
    spreadBps: 2,
    pe: 39.6,
    pePercentile: 91,
    pb: 26.4,
    roe: 72.8,
    revenueGrowth: 78.1,
    fcfMargin: 33.5,
    debtRatio: 19,
    volumeRatio: 1.31,
    ma20GapPct: 4.2,
    atrPct: 4.8,
    catalystScore: 88,
    newsCount72h: 41,
    verifiedCatalystRatio: 0.74,
    sentimentScore: 55,
    unverifiedRatio: 0.23,
    volatility20d: 42,
    maxDrawdown60d: 17
  },
  "600519.SH": {
    avgAmountCny: 7600000000,
    turnoverRate: 0.28,
    spreadBps: 6,
    pe: 22.1,
    pePercentile: 57,
    pb: 8.8,
    roe: 31.6,
    revenueGrowth: 13.7,
    fcfMargin: 29.1,
    debtRatio: 17,
    volumeRatio: 0.86,
    ma20GapPct: -4.9,
    atrPct: 2.1,
    catalystScore: 46,
    newsCount72h: 12,
    verifiedCatalystRatio: 0.68,
    sentimentScore: -22,
    unverifiedRatio: 0.26,
    volatility20d: 18,
    maxDrawdown60d: 14
  },
  "1810.HK": {
    avgAmountCny: 18200000000,
    turnoverRate: 2.85,
    spreadBps: 7,
    pe: 27.5,
    pePercentile: 63,
    pb: 3.6,
    roe: 12.9,
    revenueGrowth: 17.2,
    fcfMargin: 4.8,
    debtRatio: 48,
    volumeRatio: 1.76,
    ma20GapPct: 8.1,
    atrPct: 5.4,
    catalystScore: 82,
    newsCount72h: 35,
    verifiedCatalystRatio: 0.52,
    sentimentScore: 49,
    unverifiedRatio: 0.41,
    volatility20d: 46,
    maxDrawdown60d: 21
  },
  AAPL: {
    avgAmountCny: 82000000000,
    turnoverRate: 0.74,
    spreadBps: 2,
    pe: 29.4,
    pePercentile: 72,
    pb: 38.1,
    roe: 151.2,
    revenueGrowth: 4.8,
    fcfMargin: 23.7,
    debtRatio: 56,
    volumeRatio: 0.96,
    ma20GapPct: 1.3,
    atrPct: 2.4,
    catalystScore: 55,
    newsCount72h: 28,
    verifiedCatalystRatio: 0.72,
    sentimentScore: 18,
    unverifiedRatio: 0.14,
    volatility20d: 17,
    maxDrawdown60d: 8
  }
};

const filterCatalog = [
  {
    group: "流动性",
    items: [
      { id: "amount-high", label: "成交额 >= 50亿", test: (stock) => stock.metrics.avgAmountCny >= 5000000000, logic: "取最新交易日成交额 amount；过滤机构资金能进出的高流动性标的。", keywords: ["成交额", "流动性", "活跃", "大成交"] },
      { id: "amount-active", label: "成交额 >= 10亿", test: (stock) => stock.metrics.avgAmountCny >= 1000000000, logic: "取最新交易日成交额 amount；比 50 亿更宽松，用于中等流动性股票池。", keywords: ["成交活跃", "流动性"] },
      { id: "turnover-high", label: "换手率 >= 1%", test: (stock) => stock.metrics.turnoverRate >= 1, logic: "取最新交易日 turnover_rate；确认股票当天有足够交易活跃度。", keywords: ["换手", "活跃"] },
      { id: "turnover-healthy", label: "换手 0.5%-8%", test: (stock) => stock.metrics.turnoverRate >= 0.5 && stock.metrics.turnoverRate <= 8, logic: "取最新换手率；排除太冷清和过度炒作的极端样本。", keywords: ["换手健康"] }
    ]
  },
  {
    group: "估值与质量",
    items: [
      { id: "pe-positive", label: "PE(TTM) > 0", test: (stock) => hasMetric(stock.metrics.pe) && stock.metrics.pe > 0, logic: "取最新行情 PE(TTM)；PE<=0 视为亏损或无有效盈利口径。", keywords: ["盈利", "pe为正"] },
      { id: "pe-low", label: "PE(TTM) <= 30", test: (stock) => hasMetric(stock.metrics.pe) && stock.metrics.pe > 0 && stock.metrics.pe <= 30, logic: "取最新行情 PE(TTM)；先排除亏损，再过滤不过热估值。", keywords: ["pe低", "估值低"] },
      { id: "pb-low", label: "PB <= 3", test: (stock) => hasMetric(stock.metrics.pb) && stock.metrics.pb > 0 && stock.metrics.pb <= 3, logic: "取最新行情 PB；适合资产较重或周期类公司估值对比。", keywords: ["pb低", "市净率"] },
      { id: "roe-high", label: "ROE >= 15%", test: (stock) => hasMetric(stock.metrics.roe) && stock.metrics.roe >= 15, logic: "取最新可用财报 ROE；衡量股东权益回报和盈利质量。", keywords: ["roe", "质量", "盈利能力"] },
      { id: "revenue-growth-positive", label: "营收增长 > 0", test: (stock) => hasMetric(stock.metrics.revenueGrowth) && stock.metrics.revenueGrowth > 0, logic: "取最新可用财报 revenue_growth；确认基本面仍在扩张。", keywords: ["营收增长", "成长"] },
      { id: "gross-margin-high", label: "毛利率 >= 30%", test: (stock) => hasMetric(stock.metrics.grossMargin) && stock.metrics.grossMargin >= 30, logic: "取最新可用财报 gross_margin；高毛利通常代表产品力或议价能力。", keywords: ["毛利率", "产品力"] },
      { id: "cashflow-good", label: "自由现金流率 >= 5%", test: (stock) => hasMetric(stock.metrics.fcfMargin) && stock.metrics.fcfMargin >= 5, logic: "取最新可用财报 fcf_margin；利润能转成现金，质量更高。", keywords: ["现金流", "自由现金流"] },
      { id: "debt-low", label: "资产负债率 <= 60%", test: (stock) => hasMetric(stock.metrics.debtRatio) && stock.metrics.debtRatio <= 60, logic: "取最新可用财报 debt_ratio/liability_to_asset；降低财务杠杆风险。", keywords: ["负债低", "财务安全"] }
    ]
  },
  {
    group: "技术与催化",
    items: [
      { id: "trend-strong", label: "站上20日线", test: (stock) => stock.metrics.ma20GapPct > 0, logic: "最新收盘价 > 最近 20 条日线收盘均值；短期趋势重新转强。", keywords: ["趋势", "均线", "站上", "技术强"] },
      { id: "trend-medium", label: "站上60日线", test: (stock) => stock.metrics.ma60GapPct > 0, logic: "最新收盘价 > 最近 60 条日线收盘均值；中期趋势过滤。", keywords: ["60日线", "中期趋势"] },
      { id: "near-52w-high", label: "接近52周高点", test: (stock) => stock.metrics.nearHigh52w, logic: "最新收盘价 >= 近 252 条日线最高价的 80%；保留相对强势股票。", keywords: ["新高", "强势"] },
      { id: "volume-confirm", label: "量能 >= 1.2倍", test: (stock) => stock.metrics.volumeRatio >= 1.2, logic: "最新成交量 > 最近 20 条日线均量的 1.2 倍；用量能确认价格信号。", keywords: ["放量", "成交量", "量能"] },
      { id: "catalyst-strong", label: "近30日有公告催化", test: (stock) => stock.metrics.catalystScore >= 75, logic: "查询近 30 日 filings_history/company_reports；有公告或业绩事件才通过。", keywords: ["催化", "订单", "业绩", "政策", "新品"] }
    ]
  },
  {
    group: "证据与风险",
    items: [
      { id: "data-fresh", label: "数据 fresh", test: (stock) => stock.freshnessStatus === "fresh", logic: "最新交易日等于 daily_bars 全库最大交易日；避免用过期行情筛选。", keywords: ["新鲜", "实时", "不过期", "fresh"] },
      { id: "evidence-high", label: "有公告证据", test: (stock) => stock.truthScore >= 80, logic: "查询 filings_history 是否有官方公告；后续基本面分析优先引用。", keywords: ["证据", "可信", "真实性", "可靠"] },
      { id: "rumor-low", label: "未证实 < 25%", test: (stock) => hasMetric(stock.metrics.unverifiedRatio) && stock.metrics.unverifiedRatio < 0.25, logic: "来自新闻/讨论源的未证实比例；当前无讨论源时只作为预留风控项。", keywords: ["少传闻", "未证实少", "真实性高"] }
    ]
  }
];

const healthSourceKinds = [
  {
    kind: "market",
    name: "行情/K 线",
    text: "盘中分析依赖最新价格、K 线、成交额、换手率和价差；过期则禁止输出买卖结论。"
  },
  {
    kind: "financial",
    name: "财务/估值",
    text: "估值依赖最新行情价格和可追溯财务口径，行情或财务过期时 PE/PB 同步降级。"
  },
  {
    kind: "filing",
    name: "公告/披露",
    text: "公告原文优先使用 CNINFO、SSE/SZSE、HKEXnews、SEC EDGAR 等可追溯来源。"
  },
  {
    kind: "news",
    name: "新闻/情绪",
    text: "新闻和情绪只作为辅助；未证实信息比例偏高时只允许观察，不升级交易动作。"
  }
];

const sourceKindLabels = {
  market: "行情",
  financial: "财务/估值",
  filing: "公告/披露",
  news: "新闻情绪"
};

const marketLabels = {
  A: "A 股",
  HK: "港股",
  US: "美股"
};

const providerDisplayLabels = {
  akshare: "AKShare",
  alpha_vantage: "Alpha Vantage",
  cninfo: "CNINFO 公告",
  cninfo_sse_szse: "A 股公告自动源",
  finnhub: "Finnhub",
  finnhub_market: "Finnhub 美股行情",
  finnhub_financial: "Finnhub 基本面",
  hkexnews: "HKEXnews 公告",
  mock: "本地数据",
  mock_hk_market: "港股行情供应商",
  mock_hk_financial: "港股财务供应商",
  mock_news_cn: "A 股新闻情绪",
  mock_news_hk: "港股新闻情绪",
  mock_news_us: "美股新闻情绪",
  sse: "上交所公告",
  szse: "深交所公告",
  baostock: "BaoStock 历史回刷",
  "baostock-financial": "BaoStock 季频财务",
  tushare: "Tushare Pro",
  tushare_market: "Tushare Pro 行情",
  tushare_financial: "Tushare Pro 财务指标",
  xueqiu: "雪球评论",
  "mock-adapter": "本地适配器",
  "mock adapter": "本地适配器",
  "structured mock": "结构化数据",
  "exchange mock": "交易所数据",
  "sentiment mock": "情绪数据",
  "data gate": "数据闸门"
};

const displayValueLabels = {
  active: "上市中",
  all: "全部",
  auto: "自动",
  balance_sheet: "资产负债表",
  cash_flow: "现金流量表",
  daily: "日线",
  daily_basic: "每日指标",
  delisted: "已退市",
  earliest: "最早优先",
  earnings: "每股收益",
  etf_profile: "ETF 资料",
  filing: "公告/披露",
  fina_indicator: "财务指标",
  financial: "财务/估值",
  global_quote: "最新报价",
  income: "利润表",
  latest: "最新优先",
  market: "行情",
  market_status: "市场状态",
  news: "新闻情绪",
  news_sentiment: "新闻情绪",
  overview: "公司概览",
  profile: "公司资料",
  quote: "报价",
  relevance: "相关性优先",
  source: "来源",
  top_gainers: "涨幅榜",
  top_losers: "跌幅榜",
  most_actively_traded: "成交活跃榜"
};

const fieldDisplayLabels = {
  adjusted_close: "复权收盘价",
  annualreports: "年度报告",
  asset_allocation: "资产配置",
  authors: "作者",
  change: "涨跌额",
  change_percent: "涨跌幅",
  close: "收盘价",
  company: "公司",
  currency: "币种",
  date: "日期",
  dividend_amount: "股息",
  error: "错误",
  high: "最高价",
  information: "说明",
  latest_trading_day: "最新交易日",
  low: "最低价",
  market: "市场",
  market_open: "开市时间",
  market_close: "收市时间",
  message: "消息",
  name: "名称",
  open: "开盘价",
  overall_sentiment_label: "整体情绪标签",
  overall_sentiment_score: "整体情绪分",
  previous_close: "前收盘价",
  prompt_version: "Prompt版本",
  price: "最新价",
  published_at: "发布时间",
  quarterlyreports: "季度报告",
  raw_ticker_sentiment: "原始标的情绪",
  section: "分组",
  sentiment_score: "情绪分",
  source: "来源",
  source_tier: "来源等级",
  amount_ratio_20d: "20日成交额倍数",
  bar_count: "样本K线数",
  change_1d: "1日涨跌幅",
  change_5d: "5日涨跌幅",
  change_20d: "20日涨跌幅",
  financial_details: "财务细项",
  latest_trade_date: "最新交易日",
  limit_down_days: "跌停天数",
  limit_up_days: "涨停天数",
  llm_error: "GLM错误",
  llm_id: "GLM输入ID",
  llm_reason: "GLM理由",
  sentiment_class: "情绪分类",
  fallback_reason: "降级原因",
  max_drawdown: "最大回撤",
  structured_financial_score: "财务结构分",
  text_length: "文本长度",
  turnover_rate: "换手率",
  volume_ratio_20d: "20日成交量倍数",
  stock_code: "股票代码",
  summary: "摘要",
  symbol: "股票代码",
  ticker: "标的",
  tickers: "标的",
  time_published: "发布时间",
  timestamp: "时间",
  timezone: "时区",
  title: "标题",
  total_rows: "总行数",
  type: "类型",
  url: "链接",
  volume: "成交量"
};

const fieldTokenLabels = {
  adjusted: "复权",
  amount: "金额",
  annual: "年度",
  assets: "资产",
  average: "平均",
  capitalization: "市值",
  cash: "现金",
  change: "涨跌",
  close: "收盘",
  code: "代码",
  company: "公司",
  currency: "币种",
  date: "日期",
  day: "日",
  debt: "债务",
  dividend: "股息",
  eps: "每股收益",
  exchange: "交易所",
  fiscal: "财务",
  flow: "现金流",
  from: "来源",
  gross: "毛",
  high: "最高",
  income: "利润",
  label: "标签",
  latest: "最新",
  low: "最低",
  market: "市场",
  name: "名称",
  net: "净",
  open: "开盘",
  operating: "经营",
  percent: "百分比",
  price: "价格",
  previous: "前一",
  profit: "利润",
  published: "发布",
  quarterly: "季度",
  report: "报告",
  revenue: "收入",
  score: "分",
  sector: "行业",
  sentiment: "情绪",
  share: "股份",
  source: "来源",
  stock: "股票",
  symbol: "代码",
  time: "时间",
  title: "标题",
  total: "总",
  trading: "交易",
  type: "类型",
  url: "链接",
  value: "值",
  volume: "成交量"
};

const traditionalToSimplifiedPairs = [
  ["騰", "腾"], ["訊", "讯"], ["報", "报"], ["購", "购"], ["證", "证"], ["券", "券"],
  ["變", "变"], ["動", "动"], ["發", "发"], ["額", "额"], ["資", "资"], ["產", "产"],
  ["業", "业"], ["實", "实"], ["體", "体"], ["線", "线"], ["盤", "盘"], ["價", "价"],
  ["張", "张"], ["戶", "户"], ["據", "据"], ["數", "数"], ["據", "据"], ["庫", "库"],
  ["間", "间"], ["時", "时"], ["開", "开"], ["關", "关"], ["國", "国"], ["際", "际"],
  ["華", "华"], ["電", "电"], ["腦", "脑"], ["聯", "联"], ["絡", "络"], ["網", "网"],
  ["優", "优"], ["點", "点"], ["買", "买"], ["賣", "卖"], ["萬", "万"], ["億", "亿"],
  ["與", "与"], ["專", "专"], ["項", "项"], ["總", "总"], ["續", "续"], ["經", "经"],
  ["濟", "济"], ["務", "务"], ["員", "员"], ["獲", "获"], ["營", "营"], ["銷", "销"],
  ["聞", "闻"], ["稱", "称"], ["為", "为"], ["後", "后"], ["會", "会"], ["顯", "显"],
  ["示", "示"], ["風", "风"], ["險", "险"], ["應", "应"], ["層", "层"], ["級", "级"],
  ["構", "构"], ["選", "选"], ["輪", "轮"], ["轉", "转"], ["復", "复"], ["盤", "盘"],
  ["該", "该"], ["條", "条"], ["單", "单"], ["雙", "双"], ["讀", "读"], ["寫", "写"],
  ["錄", "录"], ["檔", "档"], ["彙", "汇"], ["別", "别"], ["啟", "启"], ["欄", "栏"],
  ["標", "标"], ["題", "题"], ["圖", "图"], ["過", "过"], ["輸", "输"], ["入", "入"],
  ["輸", "输"], ["出", "出"], ["傳", "传"], ["並", "并"], ["憑", "凭"], ["審", "审"],
  ["計", "计"], ["訊", "讯"], ["證", "证"], ["監", "监"], ["屬", "属"], ["灣", "湾"],
  ["廣", "广"], ["東", "东"], ["滬", "沪"], ["深", "深"], ["港", "港"], ["臺", "台"],
  ["來", "来"], ["類", "类"], ["佈", "布"], ["佔", "占"], ["餘", "余"], ["內", "内"],
  ["參", "参"], ["壓", "压"], ["減", "减"], ["增", "增"], ["續", "续"], ["須", "须"],
  ["對", "对"], ["區", "区"], ["號", "号"], ["認", "认"], ["許", "许"], ["註", "注"],
  ["獨", "独"], ["權", "权"], ["償", "偿"], ["餘", "余"], ["貝", "贝"], ["頁", "页"],
  ["台", "台"], ["二零二六", "二零二六"], ["發行人", "发行人"], ["證券", "证券"]
];

const traditionalToSimplifiedMap = new Map(traditionalToSimplifiedPairs);

const fallbackDataSources = [
  { id: "cn-akshare-market", market: "A", label: "AKShare A股行情", provider: "akshare", source_kind: "market", source_kind_label: "行情", requires_key: false, credential_label: "无需 key", enabled: true, configured: true, active: true, credential_hint: "" },
  { id: "cn-baostock-history", market: "A", label: "BaoStock 历史日线/回刷", provider: "baostock", source_kind: "market", source_kind_label: "行情", requires_key: false, credential_label: "无需 key", enabled: true, configured: true, active: true, credential_hint: "" },
  { id: "cn-baostock-financial", market: "A", label: "BaoStock 季频财务/公司报告", provider: "baostock-financial", source_kind: "financial", source_kind_label: "财务/估值", requires_key: false, credential_label: "无需 key", enabled: true, configured: true, active: true, credential_hint: "" },
  { id: "cn-tushare-market", market: "A", label: "Tushare Pro A股行情", provider: "tushare", source_kind: "market", source_kind_label: "行情", requires_key: true, credential_label: "Tushare token", enabled: false, configured: false, active: false, credential_hint: "" },
  { id: "cn-tushare-financial", market: "A", label: "Tushare Pro 财务/估值", provider: "tushare", source_kind: "financial", source_kind_label: "财务/估值", requires_key: true, credential_label: "Tushare token", enabled: false, configured: false, active: false, credential_hint: "" },
  { id: "cn-exchange-filings", market: "A", label: "CNINFO / 交易所公告", provider: "cninfo_sse_szse", source_kind: "filing", source_kind_label: "公告/披露", requires_key: false, credential_label: "无需 key", enabled: true, configured: true, active: true, credential_hint: "" },
  { id: "cn-news-sentiment", market: "A", label: "A股新闻情绪", provider: "mock_news_cn", source_kind: "news", source_kind_label: "新闻情绪", requires_key: true, credential_label: "News API key", enabled: false, configured: false, active: false, credential_hint: "" },
  { id: "cn-xueqiu-community", market: "A", label: "雪球评论", provider: "xueqiu", source_kind: "news", source_kind_label: "新闻情绪", requires_key: false, credential_label: "Cookie / 浏览器会话", enabled: true, configured: true, active: true, credential_hint: "", reliability: { source_id: "cn-xueqiu-community", method: "community_posts", total: 1, successes: 0, failures: 1, success_rate: 0, failure_rate: 100, latest_at: "", latest_error: "雪球评论最近没有成功入库记录，可能被 Cookie/WAF/浏览器会话阻断", status: "warn", note: "社区源按最近是否有成功入库记录计算" } },
  { id: "hk-market-vendor", market: "HK", label: "港股行情供应商", provider: "mock_hk_market", source_kind: "market", source_kind_label: "行情", requires_key: true, credential_label: "Market API key", enabled: false, configured: false, active: false, credential_hint: "" },
  { id: "hk-financial-provider", market: "HK", label: "港股财务/估值", provider: "mock_hk_financial", source_kind: "financial", source_kind_label: "财务/估值", requires_key: true, credential_label: "Financial API key", enabled: false, configured: false, active: false, credential_hint: "" },
  { id: "hk-finnhub-market", market: "HK", label: "Finnhub 港股行情", provider: "finnhub", source_kind: "market", source_kind_label: "行情", requires_key: true, credential_label: "Finnhub key", enabled: false, configured: false, active: false, credential_hint: "" },
  { id: "hk-finnhub-financial", market: "HK", label: "Finnhub 港股基本面", provider: "finnhub", source_kind: "financial", source_kind_label: "财务/估值", requires_key: true, credential_label: "Finnhub key", enabled: false, configured: false, active: false, credential_hint: "" },
  { id: "hk-hkexnews-filings", market: "HK", label: "HKEXnews 公告", provider: "hkexnews", source_kind: "filing", source_kind_label: "公告/披露", requires_key: false, credential_label: "无需 key", enabled: true, configured: true, active: true, credential_hint: "" },
  { id: "hk-news-sentiment", market: "HK", label: "港股新闻情绪", provider: "mock_news_hk", source_kind: "news", source_kind_label: "新闻情绪", requires_key: true, credential_label: "News API key", enabled: false, configured: false, active: false, credential_hint: "" },
  { id: "us-alpha-vantage-market", market: "US", label: "Alpha Vantage 美股行情", provider: "alpha_vantage", source_kind: "market", source_kind_label: "行情", requires_key: true, credential_label: "Alpha Vantage key", enabled: true, configured: false, active: false, credential_hint: "" },
  { id: "us-alpha-vantage-financial", market: "US", label: "Alpha Vantage 基本面", provider: "alpha_vantage", source_kind: "financial", source_kind_label: "财务/估值", requires_key: true, credential_label: "Alpha Vantage key", enabled: true, configured: false, active: false, credential_hint: "" },
  { id: "us-finnhub-market", market: "US", label: "Finnhub 美股行情", provider: "finnhub", source_kind: "market", source_kind_label: "行情", requires_key: true, credential_label: "Finnhub key", enabled: false, configured: false, active: false, credential_hint: "" },
  { id: "us-finnhub-financial", market: "US", label: "Finnhub 基本面", provider: "finnhub", source_kind: "financial", source_kind_label: "财务/估值", requires_key: true, credential_label: "Finnhub key", enabled: false, configured: false, active: false, credential_hint: "" },
  { id: "us-sec-edgar-filings", market: "US", label: "SEC EDGAR 披露", provider: "sec_edgar", source_kind: "filing", source_kind_label: "公告/披露", requires_key: false, credential_label: "User-Agent", enabled: true, configured: true, active: true, credential_hint: "" },
  { id: "us-news-sentiment", market: "US", label: "美股新闻情绪", provider: "mock_news_us", source_kind: "news", source_kind_label: "新闻情绪", requires_key: true, credential_label: "News API key", enabled: false, configured: false, active: false, credential_hint: "" },
  { id: "us-alpha-vantage-news", market: "US", label: "Alpha Vantage 新闻情绪", provider: "alpha_vantage", source_kind: "news", source_kind_label: "新闻情绪", requires_key: true, credential_label: "Alpha Vantage key", enabled: true, configured: false, active: false, credential_hint: "" },
  { id: "us-finnhub-news", market: "US", label: "Finnhub 公司新闻", provider: "finnhub", source_kind: "news", source_kind_label: "新闻情绪", requires_key: true, credential_label: "Finnhub key", enabled: false, configured: false, active: false, credential_hint: "" }
];

const fxToCny = {
  CNY: 1,
  HKD: 0.92,
  USD: 7.2
};

let portfolioTrades = [
  { id: 1, symbol: "002594.SZ", side: "BUY", date: "2026-05-27", quantity: 300, price: 201.4, fee: 8 },
  { id: 2, symbol: "002594.SZ", side: "BUY", date: "2026-06-02", quantity: 200, price: 207.2, fee: 6 },
  { id: 3, symbol: "002594.SZ", side: "SELL", date: "2026-06-04", quantity: 100, price: 213.8, fee: 5 },
  { id: 4, symbol: "0700.HK", side: "BUY", date: "2026-05-29", quantity: 200, price: 378.4, fee: 12 },
  { id: 5, symbol: "NVDA", side: "BUY", date: "2026-05-30", quantity: 60, price: 111.2, fee: 1.2 },
  { id: 6, symbol: "NVDA", side: "SELL", date: "2026-06-04", quantity: 15, price: 121.8, fee: 1.1 }
];

const filtersById = new Map(filterCatalog.flatMap((group) => group.items.map((item) => [item.id, item])));
const STOCK_CARD_RENDER_LIMIT = 60;
const SKILL_HUB_FAVORITES_KEY = "keiko-skillhub-favorites";
const SKILL_HUB_HISTORY_KEY = "keiko-skillhub-history";
const IWC_QUERY_SEPARATOR = ",";
const iwencaiQueryTypes = {
  ALL: "all",
  NEWS: "news_filter,web",
  NOTICE: "announcement",
  REPORT: "report",
  INTERACT: "interact",
  COMMUNITY: "community",
  OPINION: "opinion",
  BAIKE: "baike",
  CHART: "chart"
};
const iwencaiRenderKeys = {
  ALL: "all",
  AI: "ai",
  MIX: "mix",
  NEWS: "news",
  NOTICE: "notice",
  REPORT: "report",
  INTERACT: "interact",
  OPINION: "opinion",
  BAIKE: "baike",
  CHART: "chart",
  COMMUNITY: "community"
};
const iwencaiMixedSearchOptions = [
  { label: "全部", type: "全部", value: iwencaiQueryTypes.ALL, renderKey: iwencaiRenderKeys.ALL },
  { label: "新闻", type: "新闻", value: iwencaiQueryTypes.NEWS, renderKey: iwencaiRenderKeys.NEWS },
  { label: "公告", type: "公告", value: iwencaiQueryTypes.NOTICE, renderKey: iwencaiRenderKeys.NOTICE },
  { label: "研报", type: "研报", value: iwencaiQueryTypes.REPORT, renderKey: iwencaiRenderKeys.REPORT },
  { label: "董秘问答", type: "董秘问答", value: iwencaiQueryTypes.INTERACT, renderKey: iwencaiRenderKeys.INTERACT }
];
const iwencaiStandaloneSearchOptions = [
  { label: "专家点评", type: "专家点评", value: iwencaiQueryTypes.OPINION, renderKey: iwencaiRenderKeys.OPINION },
  { label: "百科", type: "百科", value: iwencaiQueryTypes.BAIKE, renderKey: iwencaiRenderKeys.BAIKE },
  { label: "图表", type: "图表", value: iwencaiQueryTypes.CHART, renderKey: iwencaiRenderKeys.CHART }
];
const iwencaiAiSearchQueryTypes = [
  iwencaiQueryTypes.NEWS,
  iwencaiQueryTypes.NOTICE,
  iwencaiQueryTypes.REPORT,
  iwencaiQueryTypes.INTERACT
];
const iwencaiSelectableQueryTypes = [
  ...iwencaiMixedSearchOptions.map((item) => item.value),
  ...iwencaiStandaloneSearchOptions.map((item) => item.value)
];
const iwencaiChannelLabels = {
  all: "全部",
  news_filter: "新闻过滤",
  web: "网页",
  announcement: "公告",
  report: "研报",
  interact: "董秘问答",
  community: "社区",
  opinion: "专家点评",
  baike: "百科",
  chart: "图表"
};
const skillHubCategories = [
  { id: "all", label: "全部技能", hint: "全渠道" },
  { id: "news", label: "新闻搜索", hint: "突发/政策/事件" },
  { id: "notice", label: "公告研报", hint: "披露/研报" },
  { id: "interaction", label: "互动问答", hint: "董秘/投资者" },
  { id: "screen", label: "条件选股", hint: "因子筛选" },
  { id: "anomaly", label: "异动解释", hint: "归因复核" },
  { id: "backtest", label: "回测验证", hint: "策略复盘" }
];
const skillHubCatalog = [
  {
    id: "hot-news-ai",
    category: "news",
    title: "新闻搜索 + AI答案",
    query: "热门权益基金单日限购1000元，对A股情绪有何影响？",
    description: "按问财的搜索技能拆成网页聚合、新闻、公告、研报、互动问答，并保留 AI答案入口。",
    queryTypes: [iwencaiQueryTypes.NEWS, iwencaiQueryTypes.NOTICE, iwencaiQueryTypes.REPORT, iwencaiQueryTypes.INTERACT],
    tags: ["web_search_query", "AI答案", "情绪扩散"],
    route: { surface: "anomaly", prompt: "热门权益基金单日限购1000元，对A股情绪有何影响？", filters: ["amount-active", "volume-confirm", "evidence-high"], market: "A" }
  },
  {
    id: "st-removal-catalyst",
    category: "news",
    title: "ST摘帽异动搜索",
    query: "突发：4家ST公司下周一停牌摘帽，概念股明日有异动机会吗？",
    description: "先搜突发新闻和公告披露，再用本地异动解释判断是不是纯消息刺激。",
    queryTypes: [iwencaiQueryTypes.NEWS, iwencaiQueryTypes.NOTICE],
    tags: ["突发新闻", "停复牌", "摘帽"],
    route: { surface: "anomaly", prompt: "ST公司停牌摘帽后，概念股明日有异动机会吗？", filters: ["turnover-high", "volume-confirm", "catalyst-strong"], market: "A" }
  },
  {
    id: "semiconductor-ipo",
    category: "news",
    title: "产业事件概念股",
    query: "长鑫科技科创板IPO获批，相关概念股有短线机会吗？",
    description: "用新闻/研报交叉确认产业链事件，再把结果落到成交额、量能、催化强度过滤。",
    queryTypes: [iwencaiQueryTypes.NEWS, iwencaiQueryTypes.REPORT],
    tags: ["半导体", "IPO", "概念股"],
    route: { surface: "filter", prompt: "半导体产业事件催化，成交额活跃、放量、公告催化强", filters: ["amount-active", "volume-confirm", "catalyst-strong", "evidence-high"], market: "A" }
  },
  {
    id: "policy-new-energy-truck",
    category: "news",
    title: "政策新闻影响面",
    query: "11部门推新能源重卡应用，哪些概念股有望异动？",
    description: "把政策新闻拆成新闻、研报和互动问答三个入口，避免只看标题就下结论。",
    queryTypes: [iwencaiQueryTypes.NEWS, iwencaiQueryTypes.REPORT, iwencaiQueryTypes.INTERACT],
    tags: ["政策", "新能源重卡", "概念映射"],
    route: { surface: "anomaly", prompt: "新能源重卡政策发布后，哪些概念股可能出现异动？", filters: ["amount-active", "volume-confirm", "catalyst-strong"], market: "A" }
  },
  {
    id: "announcement-catalyst",
    category: "notice",
    title: "公告催化筛选",
    query: "近30日有重大公告催化、成交额高、量能确认的A股",
    description: "对标公告 skill：先限定 announcement，再走本地 filings/company_reports 证据闸门。",
    queryTypes: [iwencaiQueryTypes.NOTICE],
    tags: ["announcement", "交易所公告", "证据链"],
    route: { surface: "filter", prompt: "近30日有公告催化，成交额高，量能确认", filters: ["amount-high", "volume-confirm", "catalyst-strong", "evidence-high"], market: "A" }
  },
  {
    id: "report-quality-recheck",
    category: "notice",
    title: "研报 + 基本面复核",
    query: "研报上调且ROE高、PE不过热、有公告证据的股票",
    description: "用 report skill 做观点来源，再回到 ROE、PE、公告证据做硬约束。",
    queryTypes: [iwencaiQueryTypes.REPORT, iwencaiQueryTypes.NOTICE],
    tags: ["report", "ROE", "估值复核"],
    route: { surface: "filter", prompt: "研报上调，ROE高，PE不过热，有公告证据", filters: ["roe-high", "pe-positive", "pe-low", "evidence-high"], market: "all" }
  },
  {
    id: "investor-interaction",
    category: "interaction",
    title: "董秘问答追问热度",
    query: "董秘问答里订单、产能、重组被反复追问的公司",
    description: "把 interact 作为独立搜索渠道，适合发现投资者正在追问但尚未完全公告化的线索。",
    queryTypes: [iwencaiQueryTypes.INTERACT, iwencaiQueryTypes.NEWS],
    tags: ["interact", "投资者互动", "订单产能"],
    route: { surface: "anomaly", prompt: "董秘问答里订单、产能、重组被反复追问，如何判断短线异动？", filters: ["turnover-healthy", "catalyst-strong", "rumor-low"], market: "A" }
  },
  {
    id: "single-stock-news-sentiment",
    category: "notice",
    title: "单股新闻情绪复核",
    query: "比亚迪最近公告和新闻是否支持上涨？",
    description: "用新闻/公告/专家点评组合，点击后打开单股详情和本地情绪证据面板。",
    queryTypes: [iwencaiQueryTypes.NEWS, iwencaiQueryTypes.NOTICE, iwencaiQueryTypes.OPINION],
    tags: ["新闻情绪", "公告/财报", "专家点评"],
    route: { surface: "sentiment", symbol: "002594.SZ", prompt: "比亚迪最近公告和新闻是否支持上涨？", source: "sentiment" }
  },
  {
    id: "baike-chart-stock",
    category: "notice",
    title: "百科/图表补全",
    query: "NVIDIA AI芯片业务、估值变化和近期新闻图表",
    description: "对标百科和图表 aloneInfoSearch：补全背景、结构化数据和走势复核。",
    queryTypes: [iwencaiQueryTypes.NEWS, iwencaiQueryTypes.REPORT, iwencaiQueryTypes.BAIKE, iwencaiQueryTypes.CHART],
    tags: ["baike", "chart", "单股详情"],
    route: { surface: "detail", symbol: "NVDA", prompt: "NVIDIA AI芯片业务、估值变化和近期新闻图表", source: "detail" }
  },
  {
    id: "quality-momentum",
    category: "screen",
    title: "全渠道质量动量",
    query: "成交额高、站上20日线、ROE高且有公告证据",
    description: "选择 all 时自动展开新闻、公告、研报、董秘问答，并同步生成本地条件选股。",
    queryTypes: [iwencaiQueryTypes.ALL],
    tags: ["all", "质量", "动量"],
    route: { surface: "filter", prompt: "成交额高，站上20日线，ROE高，有公告证据", filters: ["amount-high", "trend-strong", "roe-high", "evidence-high"], market: "all" }
  },
  {
    id: "market-drop-explain",
    category: "anomaly",
    title: "大盘/板块跳水归因",
    query: "今天大盘跳水，新闻、专家点评和图表分别说明了什么？",
    description: "把新闻、专家点评和图表分开看，落到本地异动解释的三层拆解。",
    queryTypes: [iwencaiQueryTypes.NEWS, iwencaiQueryTypes.OPINION, iwencaiQueryTypes.CHART],
    tags: ["大盘跳水", "opinion", "chart"],
    route: { surface: "anomaly", prompt: "今天大盘跳水，新闻、专家点评和图表分别说明了什么？", filters: ["data-fresh", "volume-confirm", "rumor-low"], market: "all" }
  },
  {
    id: "catalyst-backtest",
    category: "backtest",
    title: "催化轮动回测",
    query: "公告催化强、新闻热度高的股票，过去一季轮动效果如何？",
    description: "先用新闻/公告/研报定义候选逻辑，再切到回测模块验证收益、回撤和情绪暴露。",
    queryTypes: [iwencaiQueryTypes.NEWS, iwencaiQueryTypes.NOTICE, iwencaiQueryTypes.REPORT],
    tags: ["回测", "催化轮动", "情绪暴露"],
    route: { surface: "backtest", prompt: "公告催化强、新闻热度高的股票，过去一季轮动效果如何？", filters: ["amount-active", "catalyst-strong", "volume-confirm"], market: "all", strategy: "catalyst_rotation" }
  }
];
let stocks = baseStocks.map((stock) => enrichStock(stock));
let screenerStocks = [];

let activeMarket = "all";
let activeIndustry = "";
let selectedSymbol = stocks[0].symbol;
let filterMode = "all";
let activeFilterIds = new Set();
let databaseScreenerActive = false;
let screenerRequestId = 0;
let favoriteSymbols = new Set(["002594.SZ", "0700.HK", "1810.HK"]);
let priceRefreshCount = 0;
let latestPriceRefreshAt = "未刷新";
let selectedHoldingSymbol = "002594.SZ";
let tradeDetailsOpen = false;
let selectedAnomalySymbol = "002594.SZ";
let activeTab = "skillhub";
let activeSkillCategory = "all";
let skillHubSearchText = "";
let skillHubFavoriteIds = new Set(readStoredSkillHubArray(SKILL_HUB_FAVORITES_KEY));
let skillHubHistory = readStoredSkillHubArray(SKILL_HUB_HISTORY_KEY);
let skillHubExecution = null;
let dataSources = [];
let sourceNotificationsOpen = false;
let aksharePayload = null;
let activeAkshareCategory = "stock";
let akshareExpanded = false;
let aksharePreviewPayload = null;
let aksharePreviewLoading = false;
let aksharePreviewError = "";
let alphaVantagePayload = null;
let activeAlphaVantageCategory = "market";
let alphaVantagePreviewPayload = null;
let alphaVantagePreviewLoading = false;
let alphaVantagePreviewError = "";
let sourceTestCatalog = null;
let selectedSourceTestId = "filing-sse";
let sourceTestKindFilter = "filing";
let sourceTestPayload = null;
let sourceTestLoading = false;
let sourceTestError = "";
let industryOptions = [];
let searchHistoryItems = [];
let stockSearchSuggestions = [];
let stockSearchOpen = false;
let stockSearchLoading = false;
let stockSearchError = "";
let stockSearchTimer = null;
let stockSearchRequestId = 0;
let highlightedStockSuggestion = -1;
let backtestPayload = null;
let backtestLoading = false;
let backtestError = "";
let backtestAutoRunQueued = false;
let dataJobPoller = null;
const stockDetailCache = new Map();
const stockDetailLoading = new Set();
const stockDetailErrors = new Map();
const stockDetailPeriods = new Map();
const stockInfoTabs = new Map();
const sentimentPayloadCache = new Map();
const sentimentPayloadLoading = new Set();
const sentimentPayloadErrors = new Map();
const sentimentExpandedTypes = new Map();
const communityClassFilters = new Map();
const sentimentRefreshing = new Set();
const sentimentRefreshStartedAt = new Map();
const sentimentRefreshErrors = new Map();
const sentimentRefreshResults = new Map();
const SENTIMENT_SNAPSHOT_POLL_MS = 5 * 60 * 1000;
let sentimentSnapshotPollTimer = null;
let sentimentSnapshotPollSymbol = "";
const stockDetailRefreshing = new Set();
const stockDetailRefreshStartedAt = new Map();
const stockDetailRefreshErrors = new Map();
const stockDetailRefreshSteps = new Map();
let refreshElapsedTimer = null;
const favoriteStockLoading = new Set();
const favoriteStockLoadFailed = new Set();
const favoriteToggleInFlight = new Set();
const stockCardDetailQueue = [];
const stockCardDetailQueuedSymbols = new Set();
let stockCardDetailActiveLoads = 0;
let stockCardDetailPumpQueued = false;
let sparklineDrawQueued = false;
let stockDetailChartDrawQueued = false;
let portfolioDrawQueued = false;
let positionDrawQueued = false;
let backtestDrawQueued = false;
let stockListRefreshQueued = false;
let selectStockRequestId = 0;
const maxStockCardDetailLoads = 2;
const stockKlineHoverState = new WeakMap();
const stockDetailPeriodOptions = [
  { id: "intraday", label: "分时" },
  { id: "daily", label: "日K" },
  { id: "weekly", label: "周K" },
  { id: "monthly", label: "月K" },
  { id: "quarterly", label: "季K" }
];
const stockInfoTabOptions = [
  { id: "filings", label: "公告" },
  { id: "news", label: "资讯" },
  { id: "discussions", label: "讨论" }
];
const sentimentTypeOptions = [
  {
    id: "filing_news",
    label: "公告/财报",
    scoreKey: "filing_news_score",
    weight: 0.4,
    sourceNote: "公告、财报、基本面和新闻情绪，偏可追溯证据。"
  },
  {
    id: "community",
    label: "社区舆论",
    scoreKey: "community_score",
    weight: 0.25,
    sourceNote: "股吧/社区讨论情绪，噪声较大但能观察热度和负面扩散。"
  },
  {
    id: "market",
    label: "交易行为",
    scoreKey: "market_score",
    weight: 0.35,
    sourceNote: "涨跌幅、量能、换手、回撤、涨跌停等交易型情绪。"
  }
];
const sentimentTypeById = new Map(sentimentTypeOptions.map((item) => [item.id, item]));
const apiState = {
  connected: false,
  accountId: "acct-admin",
  accounts: [],
  sharedCache: null,
  sourceSummary: null,
  portfolio: null,
  lastError: ""
};
const navSectionIds = ["skillhub", "filters", "health", "data-exploration", "daily", "anomalies", "backtests", "favorites", "holdings", "settings"];
const requestIdleTask = window.requestIdleCallback
  ? (callback) => window.requestIdleCallback(callback, { timeout: 600 })
  : (callback) => window.setTimeout(callback, 80);

function scheduleSparklineDraw() {
  if (sparklineDrawQueued) return;
  sparklineDrawQueued = true;
  requestAnimationFrame(() => {
    sparklineDrawQueued = false;
    drawAllSparklines();
  });
}

function scheduleStockDetailChartDraw() {
  if (stockDetailChartDrawQueued) return;
  stockDetailChartDrawQueued = true;
  requestAnimationFrame(() => {
    stockDetailChartDrawQueued = false;
    drawStockDetailCharts();
  });
}

function schedulePortfolioDraw() {
  if (portfolioDrawQueued) return;
  portfolioDrawQueued = true;
  requestAnimationFrame(() => {
    portfolioDrawQueued = false;
    if (activeTab === "holdings") drawPortfolioCurve();
  });
}

function schedulePositionDraw() {
  if (positionDrawQueued) return;
  positionDrawQueued = true;
  requestAnimationFrame(() => {
    positionDrawQueued = false;
    if (activeTab === "holdings") drawPositionKline();
  });
}

function scheduleBacktestDraw() {
  if (backtestDrawQueued) return;
  backtestDrawQueued = true;
  requestAnimationFrame(() => {
    backtestDrawQueued = false;
    if (activeTab === "backtests") drawBacktestCurve();
  });
}

function scheduleActiveTabDraws(tab = activeTab) {
  if (["filters", "daily", "favorites"].includes(tab)) scheduleSparklineDraw();
  if (tab === "holdings") {
    schedulePortfolioDraw();
    schedulePositionDraw();
  }
  if (tab === "backtests") scheduleBacktestDraw();
}

function scheduleStockListRefresh() {
  if (stockListRefreshQueued) return;
  stockListRefreshQueued = true;
  requestAnimationFrame(() => {
    stockListRefreshQueued = false;
    renderCandidates();
    renderFavoriteRows();
  });
}

const candidateGrid = document.querySelector("#candidateGrid");
const candidateCount = document.querySelector("#candidateCount");
const filterResultGrid = document.querySelector("#filterResultGrid");
const filterResultCount = document.querySelector("#filterResultCount");
const anomalyUniverseCount = document.querySelector("#anomalyUniverseCount");
const anomalyStockSearch = document.querySelector("#anomalyStockSearch");
const anomalyStockList = document.querySelector("#anomalyStockList");
const anomalyPrompt = document.querySelector("#anomalyPrompt");
const runAnomalyPrompt = document.querySelector("#runAnomalyPrompt");
const anomalyReport = document.querySelector("#anomalyReport");
const backtestForm = document.querySelector("#backtestForm");
const backtestStatus = document.querySelector("#backtestStatus");
const backtestResult = document.querySelector("#backtestResult");
const backtestStrategy = document.querySelector("#backtestStrategy");
const backtestMarket = document.querySelector("#backtestMarket");
const backtestStart = document.querySelector("#backtestStart");
const backtestEnd = document.querySelector("#backtestEnd");
const backtestPositions = document.querySelector("#backtestPositions");
const backtestRebalance = document.querySelector("#backtestRebalance");
const backtestFee = document.querySelector("#backtestFee");
const backtestSlippage = document.querySelector("#backtestSlippage");
const detailTitle = document.querySelector("#detailTitle");
const detailFavorite = document.querySelector("#detailFavorite");
const detailBody = document.querySelector("#detailBody");
const sentimentAside = document.querySelector("#sentimentAside");
const reflectionList = document.querySelector("#reflectionList");
const memoryList = document.querySelector("#memoryList");
const portfolioSummary = document.querySelector("#portfolioSummary");
const portfolioCurve = document.querySelector("#portfolioCurve");
const positionKline = document.querySelector("#positionKline");
const holdingRows = document.querySelector("#holdingRows");
const tradeRows = document.querySelector("#tradeRows");
const favoriteGrid = document.querySelector("#favoriteGrid");
const favoriteCount = document.querySelector("#favoriteCount");
const tradeDetails = document.querySelector("#tradeDetails");
const toggleTradeDetails = document.querySelector("#toggleTradeDetails");
const tradeForm = document.querySelector("#tradeForm");
const tradeSymbol = document.querySelector("#tradeSymbol");
const tradeSide = document.querySelector("#tradeSide");
const tradeDate = document.querySelector("#tradeDate");
const tradeQty = document.querySelector("#tradeQty");
const tradePrice = document.querySelector("#tradePrice");
const tradeFee = document.querySelector("#tradeFee");
const tradeFormStatus = document.querySelector("#tradeFormStatus");
const healthGrid = document.querySelector("#healthGrid");
const symbolInput = document.querySelector("#symbolInput");
const stockSearchList = document.querySelector("#stockSearchList");
const filterGroups = document.querySelector("#filterGroups");
const industryFilter = document.querySelector("#industryFilter");
const filterPrompt = document.querySelector("#filterPrompt");
const activeRules = document.querySelector("#activeRules");
const skillHubSearchForm = document.querySelector("#skillHubSearchForm");
const skillHubPrompt = document.querySelector("#skillHubPrompt");
const skillHubHotQueries = document.querySelector("#skillHubHotQueries");
const skillHubCategoryTabs = document.querySelector("#skillHubCategoryTabs");
const skillHubFavoriteCount = document.querySelector("#skillHubFavoriteCount");
const skillHubFavorites = document.querySelector("#skillHubFavorites");
const skillHubHistoryList = document.querySelector("#skillHubHistory");
const skillHubExecutionPanel = document.querySelector("#skillHubExecution");
const skillHubResultCount = document.querySelector("#skillHubResultCount");
const skillHubResults = document.querySelector("#skillHubResults");
const accountSelect = document.querySelector("#accountSelect");
const backendStatus = document.querySelector("#backendStatus");
const sharedCacheStatus = document.querySelector("#sharedCacheStatus");
const sourceNotificationButton = document.querySelector("#sourceNotificationButton");
const sourceNotificationCount = document.querySelector("#sourceNotificationCount");
const sourceNotificationPanel = document.querySelector("#sourceNotificationPanel");
const sourceNotificationSummary = document.querySelector("#sourceNotificationSummary");
const sourceNotificationList = document.querySelector("#sourceNotificationList");
const dataSourceGrid = document.querySelector("#dataSourceGrid");
const sourceSettingsStatus = document.querySelector("#sourceSettingsStatus");
const akshareStatus = document.querySelector("#akshareStatus");
const akshareToggle = document.querySelector("#akshareToggle");
const akshareBody = document.querySelector("#akshareBody");
const akshareCapabilityTabs = document.querySelector("#akshareCapabilityTabs");
const akshareCapabilityGrid = document.querySelector("#akshareCapabilityGrid");
const aksharePreview = document.querySelector("#aksharePreview");
const alphaVantageStatus = document.querySelector("#alphaVantageStatus");
const alphaVantageCapabilityTabs = document.querySelector("#alphaVantageCapabilityTabs");
const alphaVantageCapabilityGrid = document.querySelector("#alphaVantageCapabilityGrid");
const alphaVantagePreview = document.querySelector("#alphaVantagePreview");
const sourceTestStatus = document.querySelector("#sourceTestStatus");
const sourceTestSelect = document.querySelector("#sourceTestSelect");
const sourceTestList = document.querySelector("#sourceTestList");
const sourceTestForm = document.querySelector("#sourceTestForm");
const sourceTestSymbol = document.querySelector("#sourceTestSymbol");
const sourceTestParams = document.querySelector("#sourceTestParams");
const sourceTestResult = document.querySelector("#sourceTestResult");
const modalShell = document.querySelector("#detailModal");
const modalTitle = document.querySelector("#modalTitle");
const modalKicker = document.querySelector("#modalKicker");
const modalBody = document.querySelector("#modalBody");
const singleDrawer = document.querySelector("#singleDrawer");
const searchHistoryBindings = [
  { surface: "stock_analysis", input: () => symbolInput },
  { surface: "filter_prompt", input: () => filterPrompt },
  { surface: "data_source_test_symbol", input: () => sourceTestSymbol },
  { surface: "data_source_test_keyword", input: () => sourceTestParams?.querySelector('[data-source-test-param="keyword"]') },
  { surface: "anomaly_stock", input: () => anomalyStockSearch },
  { surface: "anomaly_prompt", input: () => anomalyPrompt },
  { surface: "skillhub_prompt", input: () => skillHubPrompt }
];

function enrichStock(stock) {
  const metrics = stock.metrics ?? metricProfiles[stock.symbol];
  const enriched = {
    ...stock,
    metrics,
    thesis: cleanAnalysisCopy(stock.thesis),
    reasons: (stock.reasons ?? []).map(cleanAnalysisCopy),
    risks: (stock.risks ?? []).map(cleanAnalysisCopy),
    reflection: (stock.reflection ?? []).map(cleanReflectionItem),
    memoryUpdatedAt: "2026-06-04 22:10",
    supplementCount: 0
  };
  enriched.evidence = stock.evidence.map((item, index) => enrichEvidence(enriched, item, index));
  enriched.memory = buildMemory(enriched);
  return enriched;
}

function cleanReflectionItem(item) {
  return {
    ...item,
    text: cleanAnalysisCopy(item.text)
  };
}

function cleanAnalysisCopy(value) {
  return String(value ?? "")
    .replace(/\s*Mock\b/g, "")
    .replace(/\bmock\s*/ig, "数据源")
    .replace(/本原型/g, "当前环境")
    .replace(/原型演示/g, "数据闸门")
    .replace(/真实版本/g, "当前版本")
    .replace(/\s+([，。；、])/g, "$1")
    .replace(/\s{2,}/g, " ")
    .trim();
}

function enrichEvidence(stock, item, index) {
  const authorityUrl = officialUrlFor(stock, item);
  const source = cleanAnalysisSource(stock, item.source);
  return {
    ...item,
    source,
    id: `${stock.symbol}-claim-${index + 1}`,
    url: authorityUrl,
    sourceRank: item.tier === "S" ? 100 : item.tier === "A" ? 85 : item.tier === "B" ? 65 : 35,
    process: [
      `实体匹配：${stock.symbol} / ${stock.name}，市场 ${stock.marketLabel}`,
      `来源等级：${item.tier}，按官方披露、公司材料、新闻、社媒顺序降权`,
      `字段抽取：发布时间、主体、金额或指标、事件类型、是否与历史记忆冲突`,
      `置信度计算：来源等级 45% + 字段完整度 25% + 跨源一致性 20% + 时效 10%`
    ],
    rawFields: {
      fetched_at: now.toISOString(),
      as_of: formatAsOf(stock.lagMinutes),
      provider: source,
      entity_match: `${stock.symbol}:${stock.name}`,
      checksum: `${stock.symbol.replace(".", "")}-${index + 1}-${Math.round(item.confidence * 1000)}`
    }
  };
}

function cleanAnalysisSource(stock, source) {
  const text = String(source ?? "").trim();
  if (!text) return sourceDescriptionForKind(stock, "filing");
  if (!/mock/i.test(text)) return text;
  const kind = sourceKindFromText(text);
  return firstActiveSourceLabel(stock, kind) || text.replace(/\s*mock\s*/ig, "").replace(/\s*Mock\s*/g, "").trim() || sourceKindLabels[kind] || "数据源";
}

function sourceKindFromText(text) {
  if (/公告|披露|HKEX|SEC|交易所/i.test(text)) return "filing";
  if (/财务|估值|基本面|IR/i.test(text)) return "financial";
  if (/新闻|情绪|社媒/i.test(text)) return "news";
  if (/行情|K线|价格|波动|风险/i.test(text)) return "market";
  return "filing";
}

function firstActiveSourceLabel(stock, kind) {
  return activeSourceLabelsForKind(kind, stock.market)[0] || "";
}

function officialUrlFor(stock, item) {
  if (item.tier === "C") return "";
  if (stock.market === "US") return "https://www.sec.gov/search-filings/edgar-application-programming-interfaces";
  if (stock.market === "HK") return "https://www.hkexnews.hk/index.htm";
  if (stock.symbol.endsWith(".SH")) return "https://www.sse.com.cn/disclosure/listedinfo/announcement/";
  return "https://www.szse.cn/disclosure/listed/notice/index.html";
}

function buildMemory(stock) {
  const metrics = stock.metrics;
  return {
    reusable: [
      {
        title: "实体与业务画像",
        text: `${stock.symbol} 归属 ${stock.marketLabel}，名称 ${stock.name}；业务画像、交易所代码、币种 ${stock.currency}、核心行业标签可复用，除非公司发生更名、拆分或主营业务重大变化。`
      },
      {
        title: "归一化财务基线",
        text: `最近一次完整分析已保存：ROE ${formatMetric(metrics.roe, 1, "%")}，收入增速 ${formatMetric(metrics.revenueGrowth, 1, "%")}，自由现金流率 ${formatMetric(metrics.fcfMargin, 1, "%")}，资产负债率 ${formatMetric(metrics.debtRatio, 1, "%")}。这些字段可作为二次分析基线，但遇到新财报必须重新读取原始财报。`
      },
      {
        title: "已验证 claim 索引",
        text: stock.evidence.map((item) => `${item.tier}级:${item.claim}`).join("；")
      }
    ],
    mustRefresh: [
      `行情、K线、成交额、换手率、买卖价差必须重新拉取原数据；当前缓存延迟 ${stock.lagMinutes} 分钟。`,
      `新公告、停复牌、减持、回购、业绩预告必须查官方披露，不能只复用旧记忆。`,
      `新闻情绪、未证实比例、社媒热度必须重新计算；旧情绪只保留为对比基线。`,
      `估值相关 PE/PB 需要用最新价格和最新财务口径重算，不能只读取“估值偏高/偏低”的文字结论。`
    ],
    delta: [
      `与上次记忆相比：价格变化 ${stock.change >= 0 ? "+" : ""}${stock.change.toFixed(1)}%，量能倍数 ${metrics.volumeRatio.toFixed(2)}。`,
      `当前未证实信息比例 ${(metrics.unverifiedRatio * 100).toFixed(0)}%，证据可信度 ${stock.truthScore}%。`
    ]
  };
}

function formatAsOf(lagMinutes) {
  const asOf = new Date(now.getTime() - lagMinutes * 60 * 1000);
  return asOf.toLocaleString("zh-CN", {
    hour12: false,
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function isIndexLikeStock(stock) {
  const symbol = String(stock?.symbol ?? "").toUpperCase();
  const name = String(stock?.name ?? "");
  const sector = String(stock?.sector ?? "");
  const industry = String(stock?.industry ?? "");
  if (name.includes("指数") || sector.includes("指数") || industry.includes("指数")) return true;
  return ["000001.SH", "000002.SH", "000003.SH", "399001.SZ", "399006.SZ", "399300.SZ"].includes(symbol);
}

function formatPrice(stock) {
  if (isIndexLikeStock(stock)) {
    const numeric = Number(stock.price);
    return Number.isFinite(numeric) ? numeric.toFixed(2) : "暂无";
  }
  return new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency: stock.currency,
    maximumFractionDigits: stock.currency === "JPY" ? 0 : 2
  }).format(stock.price);
}

function formatMoney(value, currency = "CNY") {
  return new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency,
    maximumFractionDigits: 2
  }).format(value);
}

function formatPct(value) {
  if (!Number.isFinite(value)) return "N/A";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

function hasMetric(value) {
  return typeof value === "number" && Number.isFinite(value);
}

function firstFiniteNumber(...values) {
  for (const value of values) {
    if (value === null || value === undefined || value === "") continue;
    const numeric = Number(value);
    if (Number.isFinite(numeric)) return numeric;
  }
  return null;
}

function formatMetric(value, digits = 1, suffix = "") {
  return hasMetric(value) ? `${value.toFixed(digits)}${suffix}` : "暂无";
}

function formatMetricInt(value, suffix = "") {
  return hasMetric(value) ? `${Math.round(value)}${suffix}` : "暂无";
}

function formatRatio(value) {
  return hasMetric(value) ? `${(value * 100).toFixed(0)}%` : "暂无";
}

function formatSentimentScore(value, digits = 1, type = "") {
  if (value === null || value === undefined || value === "") return "暂无";
  let numeric = Number(value);
  if (!Number.isFinite(numeric)) return "暂无";
  if (type === "community") {
    numeric = normalizeCommunityScore(numeric);
    digits = 1;
  }
  const sign = numeric > 0 ? "+" : "";
  return `${sign}${numeric.toFixed(digits)}`;
}

function normalizeCommunityScore(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return null;
  if (Math.abs(numeric) <= 2.000001) return numeric * 50;
  return numeric;
}

function sentimentLabelText(label) {
  return ({
    positive: "积极",
    mild_positive: "偏积极",
    neutral: "中性",
    mild_negative: "偏消极",
    negative: "消极"
  })[label] || "暂无";
}

function sentimentTone(value, label = "") {
  if (value === null || value === undefined || value === "") return "neutral";
  const numeric = Number(value);
  const labelText = String(label || "");
  if (labelText.includes("positive") || numeric >= 12) return "cn-up";
  if (labelText.includes("negative") || numeric <= -12) return "cn-down";
  return "neutral";
}

function sentimentToneForType(value, label = "", type = "") {
  if (type !== "community") return sentimentTone(value, label);
  if (value === null || value === undefined || value === "") return "neutral";
  const numeric = normalizeCommunityScore(Number(value));
  const labelText = String(label || "");
  if (labelText.includes("positive") || numeric >= 10) return "cn-up";
  if (labelText.includes("negative") || numeric <= -10) return "cn-down";
  return "neutral";
}

function sentimentTrackPercent(value, type = "") {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return 50;
  if (type === "community") {
    const normalized = normalizeCommunityScore(numeric);
    return Math.max(0, Math.min(100, ((normalized + 100) / 200) * 100));
  }
  return Math.max(0, Math.min(100, (numeric + 100) / 2));
}

function sentimentFactorScore(snapshot) {
  const numeric = Number(snapshot?.composite_score);
  if (!Number.isFinite(numeric)) return null;
  return Math.max(0, Math.min(100, Math.round((numeric + 100) / 2)));
}

function sentimentSourceCount(snapshot) {
  const counts = snapshot?.source_counts ?? {};
  return ["filing_news", "community", "market"].reduce((total, key) => total + Number(counts[key] || 0), 0);
}

function formatSentimentConfidence(value) {
  if (value === null || value === undefined || value === "") return "暂无";
  return formatDetailNumber(Number(value) * 100, 0, "%");
}

function sentimentPayloadKey(symbol, windowDays = 30) {
  return `${String(symbol || "").toUpperCase()}:${Number(windowDays) || 30}`;
}

function clearSentimentPayloadCache(symbol) {
  const prefix = `${String(symbol || "").toUpperCase()}:`;
  [...sentimentPayloadCache.keys()].forEach((key) => {
    if (key.startsWith(prefix)) sentimentPayloadCache.delete(key);
  });
  [...sentimentPayloadErrors.keys()].forEach((key) => {
    if (key.startsWith(prefix)) sentimentPayloadErrors.delete(key);
  });
}

function sentimentWindowDays(snapshot) {
  return Number(snapshot?.window_days) || 30;
}

function sentimentMeta(type) {
  return sentimentTypeById.get(type) || sentimentTypeOptions[0];
}

function sentimentTypeScore(snapshot, type) {
  const meta = sentimentMeta(type);
  return snapshot?.[meta.scoreKey];
}

function sentimentAvailableTypes(snapshot) {
  const counts = snapshot?.source_counts ?? {};
  const typeScores = snapshot?.raw?.type_scores ?? {};
  return sentimentTypeOptions.filter((item) => {
    const hasCount = Number(counts[item.id] || 0) > 0;
    const hasScore = Number.isFinite(Number(typeScores[item.id]?.score ?? snapshot?.[item.scoreKey]));
    return hasCount || hasScore;
  });
}

function sentimentEffectiveWeight(snapshot, type) {
  const available = sentimentAvailableTypes(snapshot);
  const total = available.reduce((sum, item) => sum + item.weight, 0);
  if (!total) return null;
  return sentimentMeta(type).weight / total;
}

function sentimentRecencyWeight(value, windowDays = 30) {
  const dateText = String(value || "").slice(0, 10);
  const parsed = dateText ? new Date(`${dateText}T00:00:00`) : null;
  if (!parsed || Number.isNaN(parsed.getTime())) return 0.55;
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const daysAgo = Math.max(0, Math.floor((today.getTime() - parsed.getTime()) / 86400000));
  return Math.max(0.35, 1 - daysAgo / Math.max(1, windowDays * 1.3));
}

function sentimentEvidenceWeight(item, windowDays = 30) {
  const confidence = Math.max(0.1, Number(item?.confidence) || 0);
  return confidence * sentimentRecencyWeight(item?.event_date || item?.analyzed_at, windowDays);
}

function sentimentEvidenceContribution(item, windowDays = 30) {
  const score = Number(item?.sentiment_score);
  if (!Number.isFinite(score)) return null;
  if (item?.sentiment_type === "community") return normalizeCommunityScore(score);
  return score * sentimentEvidenceWeight(item, windowDays);
}

const communityClassOrder = ["正面", "偏正面", "中性", "偏负面", "负面"];

function communityClassLabel(label) {
  return label === "中性" ? "中" : label;
}

function communityClassFromScore(value) {
  const numeric = normalizeCommunityScore(Number(value));
  if (numeric === null) return "中性";
  if (numeric >= 75) return "正面";
  if (numeric >= 25) return "偏正面";
  if (numeric <= -75) return "负面";
  if (numeric <= -25) return "偏负面";
  return "中性";
}

function communityClassFromItem(item) {
  const direct = String(item?.evidence?.sentiment_class || item?.category || "").trim();
  if (communityClassOrder.includes(direct)) return direct;
  return communityClassFromScore(item?.sentiment_score);
}

function communityClassCountsFromRows(rows = []) {
  const counts = Object.fromEntries(communityClassOrder.map((item) => [item, 0]));
  rows.forEach((row) => {
    const label = communityClassFromItem(row);
    counts[label] = Number(counts[label] || 0) + 1;
  });
  return counts;
}

function normalizedCommunityClassCounts(typeStats = {}, rows = []) {
  const raw = typeStats.class_counts && typeof typeStats.class_counts === "object"
    ? typeStats.class_counts
    : communityClassCountsFromRows(rows);
  return Object.fromEntries(communityClassOrder.map((item) => [item, Number(raw[item] || 0)]));
}

function communitySourceLabel(source) {
  const text = String(source || "").trim();
  if (!text) return "社区源";
  if (text === "xueqiu") return "雪球";
  return providerDisplayName(text);
}

function communitySourceStatsFromRows(rows = []) {
  const groups = new Map();
  rows.forEach((row) => {
    const source = String(row?.source || "community").trim() || "community";
    const current = groups.get(source) || { source, scoreSum: 0, scoreCount: 0, count: 0 };
    const score = normalizeCommunityScore(Number(row?.sentiment_score));
    current.count += 1;
    if (score !== null) {
      current.scoreSum += score;
      current.scoreCount += 1;
    }
    groups.set(source, current);
  });
  const sourceOrder = { xueqiu: 0 };
  return [...groups.values()]
    .map((item) => ({
      source: item.source,
      label: communitySourceLabel(item.source),
      score: item.scoreCount ? item.scoreSum / item.scoreCount : null,
      count: item.count
    }))
    .sort((a, b) => (sourceOrder[a.source] ?? 99) - (sourceOrder[b.source] ?? 99) || b.count - a.count || a.label.localeCompare(b.label, "zh-CN"));
}

function communitySourceStatsFromSnapshot(snapshot) {
  const rawSources = snapshot?.raw?.community_sources ?? snapshot?.raw?.community_scope?.sources ?? [];
  if (!Array.isArray(rawSources)) return [];
  const sourceOrder = { xueqiu: 0 };
  return rawSources
    .map((item) => ({
      source: String(item?.source || "community"),
      label: communitySourceLabel(item?.source),
      score: normalizeCommunityScore(Number(item?.score)),
      count: Number(item?.count || 0)
    }))
    .filter((item) => item.count > 0)
    .sort((a, b) => (sourceOrder[a.source] ?? 99) - (sourceOrder[b.source] ?? 99) || b.count - a.count || a.label.localeCompare(b.label, "zh-CN"));
}

function aggregateCommunitySourceStats(sources = []) {
  const rows = Array.isArray(sources) ? sources : [];
  let count = 0;
  let scoreWeight = 0;
  let scoreCount = 0;
  rows.forEach((item) => {
    const itemCount = Math.max(0, Math.round(Number(item?.count || 0)));
    const score = normalizeCommunityScore(Number(item?.score));
    count += itemCount;
    if (itemCount > 0 && score !== null) {
      scoreWeight += score * itemCount;
      scoreCount += itemCount;
    }
  });
  return {
    score: scoreCount > 0 ? scoreWeight / scoreCount : null,
    count: count > 0 ? count : null
  };
}

function communitySourceStatsForDetail(stock, detail) {
  const snapshot = detail?.information?.sentiment;
  const key = stock && snapshot ? sentimentPayloadKey(stock.symbol, sentimentWindowDays(snapshot)) : "";
  const payloadRows = key ? (sentimentPayloadCache.get(key)?.evidence?.community ?? []) : [];
  const rowStats = communitySourceStatsFromRows(payloadRows);
  return rowStats.length ? rowStats : communitySourceStatsFromSnapshot(snapshot);
}

function renderCommunitySourceBreakdown(stats = [], options = {}) {
  const rows = Array.isArray(stats) ? stats.filter((item) => Number(item.count || 0) > 0) : [];
  if (!rows.length) {
    return options.emptyText ? `<div class="community-source-empty">${escapeHTML(options.emptyText)}</div>` : "";
  }
  const className = options.className ? ` ${options.className}` : "";
  return `
    <div class="community-source-breakdown${className}">
      ${rows.map((item) => {
        const tone = sentimentToneForType(item.score, "", "community");
        return `
          <span>
            <em>${escapeHTML(item.label || communitySourceLabel(item.source))}</em>
            <strong class="${tone === "cn-up" || tone === "cn-down" ? tone : ""}">${formatSentimentScore(item.score, 1, "community")}/${Number(item.count || 0)}</strong>
          </span>
        `;
      }).join("")}
    </div>
  `;
}

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function uniqueSentimentTerms(item) {
  const terms = Array.isArray(item?.keywords) ? item.keywords : [];
  return [...new Set(terms.map((term) => String(term || "").trim()).filter((term) => term.length >= 2))]
    .sort((a, b) => b.length - a.length)
    .slice(0, 12);
}

function renderHighlightedSentimentText(text, terms, tone = "neutral") {
  const source = String(text || "暂无原文片段");
  const cleanTerms = [...new Set((terms || []).filter(Boolean))].sort((a, b) => b.length - a.length);
  if (!cleanTerms.length) return escapeHTML(source);
  const toneClass = tone === "cn-up" || tone === "cn-down" ? tone : "neutral";
  const pattern = new RegExp(`(${cleanTerms.map(escapeRegExp).join("|")})`, "gi");
  let output = "";
  let lastIndex = 0;
  source.replace(pattern, (match, _term, offset) => {
    output += escapeHTML(source.slice(lastIndex, offset));
    output += `<mark class="sentiment-highlight ${toneClass}">${escapeHTML(match)}</mark>`;
    lastIndex = offset + match.length;
    return match;
  });
  output += escapeHTML(source.slice(lastIndex));
  return output;
}

function formatCnyAmount(value) {
  if (value >= 100000000) return `${(value / 100000000).toFixed(1)}亿`;
  return `${(value / 10000).toFixed(0)}万`;
}

function stockBySymbol(symbol) {
  return stocks.find((stock) => stock.symbol === symbol);
}

function tradeSort(a, b) {
  return `${a.date}-${a.id}`.localeCompare(`${b.date}-${b.id}`);
}

function tradesForSymbol(symbol) {
  return portfolioTrades.filter((trade) => trade.symbol === symbol).sort(tradeSort);
}

function calculatePosition(symbol) {
  const stock = stockBySymbol(symbol);
  const trades = tradesForSymbol(symbol);
  let quantity = 0;
  let costBasis = 0;
  let realizedProfit = 0;
  let totalBuyCost = 0;

  trades.forEach((trade) => {
    const gross = trade.quantity * trade.price;
    if (trade.side === "BUY") {
      quantity += trade.quantity;
      costBasis += gross + trade.fee;
      totalBuyCost += gross + trade.fee;
      return;
    }

    const sellQuantity = Math.min(trade.quantity, quantity);
    const avgCost = quantity > 0 ? costBasis / quantity : 0;
    const realizedCost = avgCost * sellQuantity;
    const proceeds = sellQuantity * trade.price - trade.fee;
    realizedProfit += proceeds - realizedCost;
    quantity -= sellQuantity;
    costBasis -= realizedCost;
  });

  const currentPrice = stock?.price ?? 0;
  const marketValue = quantity * currentPrice;
  const unrealizedProfit = marketValue - costBasis;
  const totalProfit = realizedProfit + unrealizedProfit;
  const returnRate = totalBuyCost > 0 ? (totalProfit / totalBuyCost) * 100 : 0;
  const avgCost = quantity > 0 ? costBasis / quantity : 0;

  return {
    symbol,
    stock,
    trades,
    quantity,
    avgCost,
    costBasis,
    marketValue,
    realizedProfit,
    unrealizedProfit,
    totalProfit,
    totalBuyCost,
    returnRate,
    lastTrade: trades.at(-1)
  };
}

function openPositions() {
  return [...new Set(portfolioTrades.map((trade) => trade.symbol))]
    .map(calculatePosition)
    .filter((position) => position.quantity > 0 && position.stock);
}

function cnyValue(value, currency) {
  return value * (fxToCny[currency] ?? 1);
}

function portfolioTotals() {
  const positions = openPositions();
  const byCurrency = new Map();
  let marketValueCny = 0;
  let profitCny = 0;
  let buyCostCny = 0;

  positions.forEach((position) => {
    const currency = position.stock.currency;
    const current = byCurrency.get(currency) ?? { marketValue: 0, totalProfit: 0, totalBuyCost: 0 };
    current.marketValue += position.marketValue;
    current.totalProfit += position.totalProfit;
    current.totalBuyCost += position.totalBuyCost;
    byCurrency.set(currency, current);
    marketValueCny += cnyValue(position.marketValue, currency);
    profitCny += cnyValue(position.totalProfit, currency);
    buyCostCny += cnyValue(position.totalBuyCost, currency);
  });

  return {
    positions,
    byCurrency,
    marketValueCny,
    profitCny,
    buyCostCny,
    returnRate: buyCostCny > 0 ? (profitCny / buyCostCny) * 100 : 0
  };
}

function renderTradeTags(symbol, limit = 4) {
  const trades = tradesForSymbol(symbol).slice(-limit);
  if (!trades.length) return `<span class="trade-chip empty">无B/S</span>`;
  return trades.map((trade) => `
    <span class="trade-chip ${trade.side.toLowerCase()}" title="${trade.date} ${trade.quantity} @ ${trade.price}">
      ${trade.side === "BUY" ? "B" : "S"}
    </span>
  `).join("");
}

function isHolding(symbol) {
  return calculatePosition(symbol).quantity > 0;
}

function renderStockBadges(stock) {
  const favorite = favoriteSymbols.has(stock.symbol);
  const holding = isHolding(stock.symbol);
  return `
    <div class="card-badges">
      <button class="status-badge ${favorite ? "active" : ""}" data-favorite="${stock.symbol}" type="button" aria-label="${favorite ? "取消关注" : "关注"} ${stock.symbol}">
        <span class="badge-icon bookmark-icon"></span>
        <span>${favorite ? "已关注" : "关注"}</span>
      </button>
      ${holding ? `
        <span class="status-badge holding">
          <span class="badge-icon holding-icon"></span>
          <span>已持仓</span>
        </span>
      ` : ""}
    </div>
  `;
}

function statusText(status) {
  if (status === "fresh") return "fresh";
  if (status === "warn") return "需复核";
  if (status === "pass") return "pass";
  if (status === "fail") return "fail";
  return "stale";
}

function escapeHTML(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function readStoredSkillHubArray(key) {
  try {
    const value = JSON.parse(localStorage.getItem(key) || "[]");
    return Array.isArray(value) ? value.filter(Boolean) : [];
  } catch (error) {
    return [];
  }
}

function writeStoredSkillHubArray(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(Array.isArray(value) ? value : []));
  } catch (error) {
    // localStorage can be blocked in private contexts; the skill hub still works in memory.
  }
}

function iwencaiOptionFor(value, options = [...iwencaiMixedSearchOptions, ...iwencaiStandaloneSearchOptions]) {
  return options.find((item) => item.value === value);
}

function queryTypeParts(value) {
  return String(value || "")
    .split(IWC_QUERY_SEPARATOR)
    .map((item) => item.trim())
    .filter(Boolean);
}

function containsEveryQueryPart(activeParts, expectedParts) {
  return expectedParts.every((part) => activeParts.includes(part));
}

function normalizeIwencaiQueryTypes(input = []) {
  if (input === iwencaiQueryTypes.ALL || input === "") return [iwencaiQueryTypes.ALL];
  const values = Array.isArray(input) ? input : [input];
  const direct = [];
  const looseParts = [];

  values.forEach((value) => {
    const text = String(value ?? "").trim();
    if (!text) return;
    if (iwencaiSelectableQueryTypes.includes(text)) {
      direct.push(text);
      return;
    }
    queryTypeParts(text).forEach((part) => looseParts.push(part));
  });

  if (looseParts.length) {
    iwencaiSelectableQueryTypes.forEach((value) => {
      if (value === iwencaiQueryTypes.ALL) {
        if (looseParts.includes(value)) direct.push(value);
        return;
      }
      if (containsEveryQueryPart(looseParts, queryTypeParts(value))) direct.push(value);
    });
  }

  const normalized = iwencaiSelectableQueryTypes.filter((value) => direct.includes(value));
  if (!normalized.length || normalized.includes(iwencaiQueryTypes.ALL)) return [iwencaiQueryTypes.ALL];
  return normalized;
}

function mixedInfoQueryTypesFor(queryTypes) {
  if (queryTypes.includes(iwencaiQueryTypes.ALL)) {
    return iwencaiMixedSearchOptions
      .filter((item) => item.value !== iwencaiQueryTypes.ALL)
      .map((item) => item.value);
  }
  return iwencaiMixedSearchOptions
    .filter((item) => item.value !== iwencaiQueryTypes.ALL && queryTypes.includes(item.value))
    .map((item) => item.value);
}

function standaloneInfoQueryTypesFor(queryTypes) {
  if (queryTypes.includes(iwencaiQueryTypes.ALL)) return iwencaiStandaloneSearchOptions.map((item) => item.value);
  return iwencaiStandaloneSearchOptions
    .filter((item) => queryTypes.includes(item.value))
    .map((item) => item.value);
}

function aiQueryTypesFor(queryTypes) {
  if (queryTypes.includes(iwencaiQueryTypes.ALL)) return [...iwencaiAiSearchQueryTypes];
  return iwencaiAiSearchQueryTypes.filter((value) => queryTypes.includes(value));
}

function createIwencaiTabArr(mixInfoQueryType = [], aloneInfoQueryType = [], aiQueryType = []) {
  const tabArr = [];
  if (mixInfoQueryType.length) {
    if (mixInfoQueryType.length >= 2) {
      tabArr.push({
        label: "网页",
        action: "mixInfoSearch",
        queryType: mixInfoQueryType,
        renderKey: iwencaiRenderKeys.MIX
      });
    } else {
      const option = iwencaiOptionFor(mixInfoQueryType[0], iwencaiMixedSearchOptions);
      if (option) {
        tabArr.push({
          label: option.type,
          action: "mixInfoSearch",
          queryType: [option.value],
          renderKey: option.renderKey
        });
      }
    }
    if (aiQueryType.length) {
      tabArr.push({
        label: "AI答案",
        action: "aiAnswer",
        queryType: aiQueryType,
        renderKey: iwencaiRenderKeys.AI
      });
    }
    if (mixInfoQueryType.length >= 2) {
      mixInfoQueryType.forEach((value) => {
        const option = iwencaiOptionFor(value, iwencaiMixedSearchOptions);
        if (!option) return;
        tabArr.push({
          label: option.type,
          action: "mixInfoSearch",
          queryType: [option.value],
          renderKey: option.renderKey
        });
      });
    }
  }

  aloneInfoQueryType.forEach((value) => {
    const option = iwencaiOptionFor(value, iwencaiStandaloneSearchOptions);
    if (!option) return;
    tabArr.push({
      label: option.type,
      action: "aloneInfoSearch",
      queryType: option.value,
      renderKey: option.renderKey
    });
  });

  return tabArr;
}

function buildIwencaiSkillPlan(queryTypes = []) {
  const normalized = normalizeIwencaiQueryTypes(queryTypes);
  const mixInfoQueryType = mixedInfoQueryTypesFor(normalized);
  const aloneInfoQueryType = standaloneInfoQueryTypesFor(normalized);
  const aiQueryType = aiQueryTypesFor(normalized);
  const tabArr = createIwencaiTabArr(mixInfoQueryType, aloneInfoQueryType, aiQueryType);
  return {
    queryTypes: normalized,
    mixInfoQueryType,
    aloneInfoQueryType,
    aiQueryType,
    tabArr,
    hasAiSearch: aiQueryType.length > 0,
    aiSearchMessage: null
  };
}

function iwencaiChannelsForQueryTypes(queryTypes = []) {
  const normalized = normalizeIwencaiQueryTypes(queryTypes);
  const selected = normalized.includes(iwencaiQueryTypes.ALL)
    ? iwencaiMixedSearchOptions.filter((item) => item.value !== iwencaiQueryTypes.ALL).map((item) => item.value)
    : normalized;
  return [...new Set(selected.join(IWC_QUERY_SEPARATOR).split(IWC_QUERY_SEPARATOR).filter(Boolean))];
}

function iwencaiRagRequestParams(question, queryTypes = []) {
  return {
    app_id: "local-iwc-search-skill",
    question,
    query: question,
    channels: iwencaiChannelsForQueryTypes(queryTypes),
    qid: "local-preview",
    scroll_mode: "web",
    platform: "pc"
  };
}

function displayQueryType(value) {
  if (value === iwencaiQueryTypes.ALL) return "全部";
  const option = iwencaiOptionFor(value);
  if (option) return option.type;
  return queryTypeParts(value).map((part) => iwencaiChannelLabels[part] || part).join("+");
}

function displayIwencaiChannels(channels = []) {
  return channels.map((channel) => iwencaiChannelLabels[channel] || channel);
}

function skillHubCategoryLabel(category) {
  return skillHubCategories.find((item) => item.id === category)?.label || "技能";
}

function skillHubSkillById(id) {
  return skillHubCatalog.find((item) => item.id === id);
}

function skillHubCategoryCount(category) {
  if (category === "all") return skillHubCatalog.length;
  return skillHubCatalog.filter((skill) => skill.category === category).length;
}

function skillHubSearchBlob(skill) {
  const plan = buildIwencaiSkillPlan(skill.queryTypes);
  return [
    skill.title,
    skill.query,
    skill.description,
    skill.category,
    ...(skill.tags || []),
    ...plan.queryTypes.map(displayQueryType),
    ...plan.tabArr.map((tab) => `${tab.label} ${tab.action}`)
  ].join(" ").toLowerCase();
}

function filteredSkillHubCatalog() {
  const query = skillHubSearchText.trim().toLowerCase();
  return skillHubCatalog.filter((skill) => {
    const categoryMatch = activeSkillCategory === "all" || skill.category === activeSkillCategory;
    if (!categoryMatch) return false;
    if (!query) return true;
    return skillHubSearchBlob(skill).includes(query);
  });
}

function skillHubHotQueryItems() {
  return [
    "热门权益基金单日限购1000元，对A股情绪有何影响？",
    "突发：4家ST公司下周一停牌摘帽，概念股明日有异动机会吗？",
    "央行放开大额存单转让，金融科技股有短线机会吗？",
    "A股半导体巨头现重整+增持，短期会高开低走吗？",
    "长鑫科技科创板IPO获批，相关概念股有短线机会吗？",
    "11部门推新能源重卡应用，哪些概念股有望异动？"
  ];
}

function renderSkillHub() {
  if (!skillHubResults) return;
  const results = filteredSkillHubCatalog();
  if (skillHubResultCount) skillHubResultCount.textContent = `${results.length} 个`;
  if (skillHubCategoryTabs) {
    skillHubCategoryTabs.innerHTML = skillHubCategories.map((category) => `
      <button class="skillhub-tab ${activeSkillCategory === category.id ? "active" : ""}" data-skill-category="${escapeHTML(category.id)}" type="button">
        <span>${escapeHTML(category.label)}</span>
        <small>${escapeHTML(category.hint)} · ${skillHubCategoryCount(category.id)}</small>
      </button>
    `).join("");
  }
  if (skillHubHotQueries) {
    skillHubHotQueries.innerHTML = skillHubHotQueryItems().map((query) => `
      <button data-skill-hot-query="${escapeHTML(query)}" type="button">${escapeHTML(query)}</button>
    `).join("");
  }
  renderSkillHubShelves();
  renderSkillHubExecution();
  skillHubResults.innerHTML = results.length
    ? results.map(renderSkillHubCard).join("")
    : renderEmptySkillHubResults();
}

function renderEmptySkillHubResults() {
  const text = skillHubSearchText.trim();
  if (!text) return `<div class="empty-state">当前分类没有技能。</div>`;
  const inferred = buildIwencaiSkillPlan(inferIwencaiQueryTypes(text));
  return `
    <div class="empty-state skillhub-empty">
      <strong>没有完全匹配的内置技能</strong>
      <span>已按问法推断：${inferred.queryTypes.map(displayQueryType).join(" / ")}。点击下方按钮可以按自定义搜索技能解析。</span>
      <button class="mini-action" data-skill-custom-run type="button">解析这个问题</button>
    </div>
  `;
}

function renderSkillHubShelves() {
  if (skillHubFavoriteCount) skillHubFavoriteCount.textContent = `${skillHubFavoriteIds.size}`;
  if (skillHubFavorites) {
    const favorites = [...skillHubFavoriteIds].map(skillHubSkillById).filter(Boolean).slice(0, 8);
    skillHubFavorites.innerHTML = favorites.length
      ? favorites.map((skill) => renderSkillHubMiniButton(skill, "收藏")).join("")
      : `<div class="empty-state compact">还没有收藏技能。</div>`;
  }
  if (skillHubHistoryList) {
    const items = skillHubHistory.slice(0, 8);
    skillHubHistoryList.innerHTML = items.length
      ? items.map(renderSkillHubHistoryButton).join("")
      : `<div class="empty-state compact">使用技能后会记录在这里。</div>`;
  }
}

function renderSkillHubMiniButton(skill, meta) {
  return `
    <button data-skill-mini="${escapeHTML(skill.id)}" type="button">
      <strong>${escapeHTML(skill.title)}</strong>
      <small>${escapeHTML(meta)} · ${escapeHTML(skill.query)}</small>
    </button>
  `;
}

function renderSkillHubHistoryButton(entry) {
  const id = typeof entry === "string" ? entry : entry.id;
  const skill = skillHubSkillById(id);
  const title = skill?.title || entry.title || "自定义搜索";
  const query = skill?.query || entry.query || String(entry || "");
  const attrs = skill ? `data-skill-mini="${escapeHTML(skill.id)}"` : `data-skill-history-query="${escapeHTML(query)}"`;
  return `
    <button ${attrs} type="button">
      <strong>${escapeHTML(title)}</strong>
      <small>${escapeHTML(query)}</small>
    </button>
  `;
}

function renderSkillHubCard(skill) {
  const plan = buildIwencaiSkillPlan(skill.queryTypes);
  const favorite = skillHubFavoriteIds.has(skill.id);
  const channels = displayIwencaiChannels(iwencaiChannelsForQueryTypes(skill.queryTypes));
  return `
    <article class="skillhub-card" data-skill-card="${escapeHTML(skill.id)}">
      <div class="skillhub-card-head">
        <span class="skillhub-target">${escapeHTML(skillHubCategoryLabel(skill.category))}</span>
        <button class="skill-favorite-toggle ${favorite ? "is-favorite" : ""}" data-skill-favorite="${escapeHTML(skill.id)}" type="button" aria-label="${favorite ? "取消收藏" : "收藏"} ${escapeHTML(skill.title)}">${favorite ? "已收藏" : "收藏"}</button>
      </div>
      <div>
        <h4>${escapeHTML(skill.title)}</h4>
        <p class="skillhub-query">问法：${escapeHTML(skill.query)}</p>
      </div>
      <p>${escapeHTML(skill.description)}</p>
      <div class="skillhub-tags" aria-label="queryType">
        ${plan.queryTypes.map((type) => `<span>${escapeHTML(displayQueryType(type))}</span>`).join("")}
      </div>
      <div class="skillhub-channel-row" aria-label="channels">
        ${channels.map((channel) => `<span>${escapeHTML(channel)}</span>`).join("")}
      </div>
      <div class="skillhub-action-tabs" aria-label="技能页签">
        ${plan.tabArr.map((tab) => `
          <button data-skill-action-tab="${escapeHTML(skill.id)}" data-skill-action-render="${escapeHTML(tab.renderKey)}" type="button">
            ${escapeHTML(tab.label)}
          </button>
        `).join("")}
      </div>
      <div class="skillhub-route">${escapeHTML(localRouteLabel(skill.route))}</div>
      <div class="skillhub-card-actions">
        <button data-skill-preview="${escapeHTML(skill.id)}" type="button">解析</button>
        <button class="skill-use" data-skill-use="${escapeHTML(skill.id)}" type="button">执行技能</button>
      </div>
    </article>
  `;
}

function renderSkillHubExecution() {
  if (!skillHubExecutionPanel) return;
  const skill = skillHubExecution?.skill || skillHubSkillById(skillHubExecution?.skillId);
  if (!skill) {
    skillHubExecutionPanel.hidden = true;
    skillHubExecutionPanel.innerHTML = "";
    return;
  }
  const plan = buildIwencaiSkillPlan(skill.queryTypes);
  const selectedTab = plan.tabArr.find((tab) => tab.renderKey === skillHubExecution.tabRenderKey) || plan.tabArr[0];
  const queryTypes = Array.isArray(selectedTab?.queryType) ? selectedTab.queryType : [selectedTab?.queryType].filter(Boolean);
  const params = iwencaiRagRequestParams(skill.query, queryTypes.length ? queryTypes : skill.queryTypes);
  const route = skill.route || {};
  skillHubExecutionPanel.hidden = false;
  skillHubExecutionPanel.innerHTML = `
    <div class="skillhub-execution-head">
      <div>
        <p class="eyebrow">Resolved skill</p>
        <h4>${escapeHTML(skill.title)}</h4>
      </div>
      <span>${escapeHTML(selectedTab?.label || "技能")}</span>
    </div>
    <p class="skillhub-execution-query">${escapeHTML(skill.query)}</p>
    <div class="skillhub-action-tabs execution" aria-label="已解析页签">
      ${plan.tabArr.map((tab) => `
        <button class="${tab.renderKey === selectedTab?.renderKey ? "active" : ""}" data-skill-action-tab="${escapeHTML(skill.id)}" data-skill-action-render="${escapeHTML(tab.renderKey)}" type="button">
          ${escapeHTML(tab.label)}
        </button>
      `).join("")}
    </div>
    <div class="skillhub-execution-grid">
      <div>
        <span>queryType</span>
        <strong>${queryTypes.map(displayQueryType).join(" / ")}</strong>
      </div>
      <div>
        <span>channels</span>
        <strong>${displayIwencaiChannels(params.channels).join(" / ")}</strong>
      </div>
      <div>
        <span>action</span>
        <strong>${escapeHTML(selectedTab?.action || "mixInfoSearch")}</strong>
      </div>
      <div>
        <span>local route</span>
        <strong>${escapeHTML(localRouteLabel(route))}</strong>
      </div>
    </div>
    <div class="skillhub-request-line">
      <code>/gateway/comprehensive/rag/v1/stream/search</code>
      <span>question + channels + scroll_mode=${escapeHTML(params.scroll_mode)} + platform=${escapeHTML(params.platform)}</span>
    </div>
  `;
}

function localRouteLabel(route = {}) {
  if (route.surface === "filter") return "条件选股 /api/screeners/run";
  if (route.surface === "anomaly") return "异动解释 + 资讯复核";
  if (route.surface === "sentiment") return "单股详情 + 新闻情绪";
  if (route.surface === "detail") return "单股详情 + 披露/资讯";
  if (route.surface === "backtest") return "策略回测 /api/backtests/run";
  return "本地解析";
}

function inferIwencaiQueryTypes(text) {
  const value = String(text || "").toLowerCase();
  const types = [];
  if (/新闻|资讯|突发|消息|政策|影响|概念|异动|today|news/i.test(value)) types.push(iwencaiQueryTypes.NEWS);
  if (/公告|披露|停牌|复牌|增持|回购|重组|业绩|财报|ipo/i.test(value)) types.push(iwencaiQueryTypes.NOTICE);
  if (/研报|评级|目标价|机构|上调|下调|research|report/i.test(value)) types.push(iwencaiQueryTypes.REPORT);
  if (/董秘|互动|问答|投资者|调研|订单|产能/i.test(value)) types.push(iwencaiQueryTypes.INTERACT);
  if (/点评|专家|观点|opinion/i.test(value)) types.push(iwencaiQueryTypes.OPINION);
  if (/百科|是什么|背景|baike/i.test(value)) types.push(iwencaiQueryTypes.BAIKE);
  if (/图表|走势|曲线|chart|k线|k 线/i.test(value)) types.push(iwencaiQueryTypes.CHART);
  return types.length ? [...new Set(types)] : [iwencaiQueryTypes.ALL];
}

function inferSkillHubFilters(text) {
  const value = String(text || "").toLowerCase();
  const ids = [];
  filterCatalog.forEach((group) => {
    group.items.forEach((item) => {
      if (ids.length >= 5) return;
      const matched = (item.keywords || []).some((keyword) => value.includes(String(keyword).toLowerCase()));
      if (matched) ids.push(item.id);
    });
  });
  if (/公告|披露|催化|重组|增持|回购/i.test(value)) ids.push("catalyst-strong", "evidence-high");
  if (/放量|量能|成交|活跃/i.test(value)) ids.push("amount-active", "volume-confirm");
  if (/趋势|均线|站上|强势/i.test(value)) ids.push("trend-strong");
  return [...new Set(ids)].filter((id) => filtersById.has(id)).slice(0, 5);
}

function inferSkillHubMarket(text) {
  const value = String(text || "").toLowerCase();
  if (/港股|hk|恒生|南向/i.test(value)) return "HK";
  if (/美股|us|nasdaq|nvidia|apple|sec/i.test(value)) return "US";
  if (/a股|a 股|沪深|科创|创业板|北向/i.test(value)) return "A";
  return "all";
}

function customSkillFromPrompt(text) {
  return {
    id: "custom-query",
    category: "news",
    title: "自定义搜索技能",
    query: text,
    description: "按输入问法自动推断 queryType、channels 和本地执行路线。",
    queryTypes: inferIwencaiQueryTypes(text),
    tags: ["lenovo", "自定义", "queryType"],
    route: {
      surface: "anomaly",
      prompt: text,
      filters: inferSkillHubFilters(text),
      market: inferSkillHubMarket(text)
    }
  };
}

function rememberSkillHubUse(skill) {
  const entry = {
    id: skill.id,
    title: skill.title,
    query: skill.query,
    at: Date.now()
  };
  skillHubHistory = [
    entry,
    ...skillHubHistory.filter((item) => {
      const id = typeof item === "string" ? item : item.id;
      const query = typeof item === "string" ? item : item.query;
      return id !== entry.id && query !== entry.query;
    })
  ].slice(0, 10);
  writeStoredSkillHubArray(SKILL_HUB_HISTORY_KEY, skillHubHistory);
}

function toggleSkillHubFavorite(id) {
  if (!skillHubSkillById(id)) return;
  if (skillHubFavoriteIds.has(id)) skillHubFavoriteIds.delete(id);
  else skillHubFavoriteIds.add(id);
  writeStoredSkillHubArray(SKILL_HUB_FAVORITES_KEY, [...skillHubFavoriteIds]);
  renderSkillHub();
}

function executeSkillHubSkillById(id, renderKey = "", shouldRoute = true) {
  const skill = skillHubSkillById(id);
  if (!skill) return;
  executeSkillHubSkill(skill, renderKey, shouldRoute);
}

function executeSkillHubSkill(skill, renderKey = "", shouldRoute = true) {
  const plan = buildIwencaiSkillPlan(skill.queryTypes);
  const selectedTab = plan.tabArr.find((tab) => tab.renderKey === renderKey)
    || plan.tabArr.find((tab) => tab.renderKey === iwencaiRenderKeys.AI)
    || plan.tabArr[0];
  skillHubExecution = {
    skillId: skill.id,
    skill: skill.id === "custom-query" ? skill : null,
    tabRenderKey: selectedTab?.renderKey || "",
    tabAction: selectedTab?.action || "",
    executedAt: Date.now()
  };
  if (skillHubPrompt) skillHubPrompt.value = skill.query;
  skillHubSearchText = skill.id === "custom-query" ? skill.query : skillHubSearchText;
  rememberSkillHubUse(skill);
  renderSkillHub();
  if (shouldRoute) runSkillHubLocalRoute(skill);
}

function applySkillHubRouteFilters(route = {}, prompt = "") {
  const nextMarket = route.market || "all";
  activeMarket = nextMarket;
  activeIndustry = "";
  document.querySelectorAll(".segment").forEach((item) => item.classList.toggle("active", item.dataset.market === nextMarket));
  if (industryFilter) industryFilter.value = "";
  const validFilters = (route.filters || []).filter((id) => filtersById.has(id));
  if (validFilters.length) activeFilterIds = new Set(validFilters);
  if (filterPrompt) filterPrompt.value = route.prompt || prompt || "";
  renderFilterGroups();
  syncFilterModeButtons();
  renderActiveRules();
}

function runSkillHubLocalRoute(skill) {
  const route = skill.route || {};
  if (route.filters || route.market || route.surface === "filter") {
    applySkillHubRouteFilters(route, skill.query);
  }
  if (route.surface === "filter") {
    setActiveTab("filters");
    void (async () => {
      await loadIndustryOptions();
      await runDatabaseScreener();
    })();
    return;
  }
  if (route.surface === "anomaly") {
    if (anomalyPrompt) anomalyPrompt.value = route.prompt || skill.query;
    setActiveTab("anomalies");
    void runDatabaseScreener();
    renderPromptAnomalyReport();
    return;
  }
  if (route.surface === "sentiment" || route.surface === "detail") {
    if (route.symbol) {
      selectedSymbol = route.symbol.toUpperCase();
      setActiveTab("filters");
      void selectStock(route.symbol, true);
      if (route.surface === "sentiment" && apiState.connected) {
        window.setTimeout(() => refreshCurrentSentiment(false), 350);
      }
    }
    return;
  }
  if (route.surface === "backtest") {
    if (backtestStrategy && route.strategy) backtestStrategy.value = route.strategy;
    if (backtestMarket && route.market) backtestMarket.value = route.market;
    setActiveTab("backtests");
    void runBacktest();
  }
}

function handleSkillHubSearchSubmit(event) {
  event?.preventDefault();
  const text = skillHubPrompt?.value.trim() || "";
  skillHubSearchText = text;
  if (text) void saveSearchHistory("skillhub_prompt", text);
  const matches = filteredSkillHubCatalog();
  if (!matches.length && text) {
    executeSkillHubSkill(customSkillFromPrompt(text), "", false);
    return;
  }
  renderSkillHub();
}

function handleSkillHubAction(event) {
  const favoriteButton = event.target.closest("[data-skill-favorite]");
  const useButton = event.target.closest("[data-skill-use]");
  const previewButton = event.target.closest("[data-skill-preview]");
  const actionTab = event.target.closest("[data-skill-action-tab]");
  const miniButton = event.target.closest("[data-skill-mini]");
  const historyQueryButton = event.target.closest("[data-skill-history-query]");
  const customRun = event.target.closest("[data-skill-custom-run]");

  if (favoriteButton) {
    event.preventDefault();
    toggleSkillHubFavorite(favoriteButton.dataset.skillFavorite);
    return;
  }
  if (useButton) {
    event.preventDefault();
    executeSkillHubSkillById(useButton.dataset.skillUse, "", true);
    return;
  }
  if (previewButton) {
    event.preventDefault();
    executeSkillHubSkillById(previewButton.dataset.skillPreview, "", false);
    return;
  }
  if (actionTab) {
    event.preventDefault();
    const id = actionTab.dataset.skillActionTab;
    if (skillHubExecution?.skill?.id === id) executeSkillHubSkill(skillHubExecution.skill, actionTab.dataset.skillActionRender, false);
    else executeSkillHubSkillById(id, actionTab.dataset.skillActionRender, false);
    return;
  }
  if (miniButton) {
    event.preventDefault();
    executeSkillHubSkillById(miniButton.dataset.skillMini, "", true);
    return;
  }
  if (historyQueryButton) {
    event.preventDefault();
    const query = historyQueryButton.dataset.skillHistoryQuery;
    if (skillHubPrompt) skillHubPrompt.value = query;
    skillHubSearchText = query;
    executeSkillHubSkill(customSkillFromPrompt(query), "", false);
    return;
  }
  if (customRun) {
    event.preventDefault();
    const text = skillHubPrompt?.value.trim() || skillHubSearchText.trim();
    if (text) executeSkillHubSkill(customSkillFromPrompt(text), "", false);
  }
}

function refreshStartedAtFor(kind) {
  return kind === "sentiment" ? sentimentRefreshStartedAt : stockDetailRefreshStartedAt;
}

function formatRefreshElapsed(startedAt) {
  const timestamp = Number(startedAt);
  if (!Number.isFinite(timestamp) || timestamp <= 0) return "00:00";
  const totalSeconds = Math.max(0, Math.floor((Date.now() - timestamp) / 1000));
  const seconds = totalSeconds % 60;
  const minutes = Math.floor(totalSeconds / 60) % 60;
  const hours = Math.floor(totalSeconds / 3600);
  const pad = (value) => String(value).padStart(2, "0");
  if (hours) return `${hours}:${pad(minutes)}:${pad(seconds)}`;
  return `${pad(minutes)}:${pad(seconds)}`;
}

function refreshElapsedText(kind, symbol) {
  return `用时 ${formatRefreshElapsed(refreshStartedAtFor(kind).get(symbol))}`;
}

function renderRefreshElapsed(kind, symbol) {
  return `
    <span
      class="refresh-elapsed"
      data-refresh-elapsed-kind="${escapeHTML(kind)}"
      data-refresh-elapsed-symbol="${escapeHTML(symbol)}"
    >${escapeHTML(refreshElapsedText(kind, symbol))}</span>
  `;
}

function updateRefreshElapsedElements() {
  document.querySelectorAll("[data-refresh-elapsed-kind][data-refresh-elapsed-symbol]").forEach((item) => {
    item.textContent = refreshElapsedText(item.dataset.refreshElapsedKind, item.dataset.refreshElapsedSymbol);
  });
  stopRefreshElapsedTimerIfIdle();
}

function ensureRefreshElapsedTimer() {
  updateRefreshElapsedElements();
  if (refreshElapsedTimer) return;
  refreshElapsedTimer = window.setInterval(updateRefreshElapsedElements, 1000);
}

function stopRefreshElapsedTimerIfIdle() {
  if (stockDetailRefreshing.size || sentimentRefreshing.size || !refreshElapsedTimer) return;
  window.clearInterval(refreshElapsedTimer);
  refreshElapsedTimer = null;
}

function normalizeFieldKey(key) {
  return String(key ?? "")
    .trim()
    .replace(/([a-z0-9])([A-Z])/g, "$1_$2")
    .replace(/[\s.-]+/g, "_")
    .replace(/_+/g, "_")
    .toLowerCase();
}

function toSimplifiedChinese(value) {
  let text = String(value ?? "");
  for (const [from, to] of traditionalToSimplifiedPairs.filter(([from]) => from.length > 1)) {
    text = text.replaceAll(from, to);
  }
  return [...text].map((char) => traditionalToSimplifiedMap.get(char) ?? char).join("");
}

function providerDisplayName(provider) {
  const key = normalizeFieldKey(provider);
  return providerDisplayLabels[key] || providerDisplayLabels[String(provider ?? "").trim().toLowerCase()] || toSimplifiedChinese(provider ?? "");
}

function displayColumnLabel(column) {
  const raw = String(column ?? "");
  const key = normalizeFieldKey(raw);
  if (fieldDisplayLabels[key]) return fieldDisplayLabels[key];
  if (/[\u4e00-\u9fff]/.test(raw)) return toSimplifiedChinese(raw);
  const words = key.split("_").filter(Boolean);
  if (!words.length) return "";
  const translated = words.map((word) => fieldTokenLabels[word] || word.toUpperCase());
  return translated.join("");
}

function displayCellValue(value, column = "") {
  if (value === null || value === undefined) return "";
  if (typeof value === "boolean") return value ? "是" : "否";
  if (typeof value === "number") return String(value);
  if (typeof value === "object") return toSimplifiedChinese(JSON.stringify(value));

  const raw = String(value);
  if (raw.startsWith("http://") || raw.startsWith("https://")) return raw;
  const simplified = toSimplifiedChinese(raw);
  const key = normalizeFieldKey(simplified);
  const columnKey = normalizeFieldKey(column);
  if (columnKey === "source" || columnKey === "provider") return providerDisplayName(simplified);
  return displayValueLabels[key] || providerDisplayLabels[key] || simplified;
}

function displayText(value) {
  return displayCellValue(value);
}

async function apiRequest(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {})
    }
  });
  if (!response.ok) {
    const text = await response.text();
    let detail = text;
    try {
      const payload = text ? JSON.parse(text) : null;
      const value = payload?.detail ?? payload;
      detail = typeof value === "string"
        ? value
        : (value?.message ?? value?.note ?? JSON.stringify(value));
    } catch (error) {
      detail = text;
    }
    throw new Error(detail || `${response.status} ${response.statusText}`);
  }
  return response.json();
}

function stopSentimentSnapshotPoll() {
  if (sentimentSnapshotPollTimer) {
    clearInterval(sentimentSnapshotPollTimer);
    sentimentSnapshotPollTimer = null;
  }
  sentimentSnapshotPollSymbol = "";
}

function scheduleSentimentSnapshotPoll(symbol) {
  stopSentimentSnapshotPoll();
  if (!symbol || !apiState.connected || singleDrawer.hidden) return;
  sentimentSnapshotPollSymbol = symbol;
  sentimentSnapshotPollTimer = window.setInterval(() => {
    void pollSentimentSnapshot(sentimentSnapshotPollSymbol);
  }, SENTIMENT_SNAPSHOT_POLL_MS);
}

async function pollSentimentSnapshot(symbol) {
  if (!symbol || !apiState.connected || singleDrawer.hidden) return;
  if (selectedSymbol !== symbol) return;
  if (sentimentRefreshing.has(symbol)) return;
  const stock = stockBySymbol(symbol);
  if (!stock) return;
  const detail = stockDetailCache.get(symbol);
  if (!detail) return;

  const windowDays = sentimentWindowDays(detail?.information?.sentiment);
  const previousGeneratedAt = detail?.information?.sentiment?.generated_at || "";

  try {
    const params = new URLSearchParams({
      days: String(windowDays || 30),
      evidence_limit: "1"
    });
    const payload = await apiRequest(`/api/sentiment/stocks/${encodeURIComponent(symbol)}?${params.toString()}`);
    const snapshot = payload?.snapshot;
    if (!snapshot) return;
    if ((snapshot.generated_at || "") === previousGeneratedAt) return;

    detail.information = detail.information || {};
    detail.information.sentiment = snapshot;
    stockDetailCache.set(symbol, detail);
    clearSentimentPayloadCache(symbol);
    renderSentimentAside(stock, detail);
  } catch (_error) {
    // Background poll stays silent; manual refresh still surfaces errors.
  }
}

async function loadSentimentPayload(symbol, windowDays = 30, options = {}) {
  const key = sentimentPayloadKey(symbol, windowDays);
  if (sentimentPayloadCache.has(key) || sentimentPayloadLoading.has(key)) return;
  sentimentPayloadLoading.add(key);
  sentimentPayloadErrors.delete(key);
  renderSentimentAside(selectedStock(), stockDetailCache.get(symbol));
  try {
    const params = new URLSearchParams({
      days: String(windowDays || 30),
      evidence_limit: "120"
    });
    const payload = await apiRequest(`/api/sentiment/stocks/${encodeURIComponent(symbol)}?${params.toString()}`);
    sentimentPayloadCache.set(key, payload);
  } catch (error) {
    sentimentPayloadErrors.set(key, error.message);
  } finally {
    sentimentPayloadLoading.delete(key);
    renderSentimentAside(selectedStock(), stockDetailCache.get(symbol));
    scheduleStockListRefresh();
    if (options.renderDetails && selectedSymbol === symbol && !singleDrawer.hidden) {
      const current = stockBySymbol(symbol);
      if (current) renderDetails(current);
    }
  }
}

function ensureSentimentPayloadForDetail(stock, detail) {
  const snapshot = detail?.information?.sentiment;
  if (!stock || !snapshot || !apiState.connected) return;
  const windowDays = sentimentWindowDays(snapshot);
  const key = sentimentPayloadKey(stock.symbol, windowDays);
  if (sentimentPayloadCache.has(key) || sentimentPayloadLoading.has(key) || sentimentPayloadErrors.has(key)) return;
  void loadSentimentPayload(stock.symbol, windowDays, { renderDetails: true });
}

async function refreshCurrentSentiment(useLlm = true) {
  const stock = selectedStock();
  if (!stock || !apiState.connected) return;
  if (sentimentRefreshing.has(stock.symbol)) return;
  const detail = stockDetailCache.get(stock.symbol);
  const windowDays = sentimentWindowDays(detail?.information?.sentiment);
  sentimentRefreshing.add(stock.symbol);
  sentimentRefreshStartedAt.set(stock.symbol, Date.now());
  sentimentRefreshErrors.delete(stock.symbol);
  sentimentRefreshResults.delete(stock.symbol);
  ensureRefreshElapsedTimer();
  renderSentimentAside(stock, detail);
  try {
    updateBackendStatus(`刷新 ${stock.symbol} 情绪中`);
    const result = await apiRequest("/api/sentiment/refresh", {
      method: "POST",
      body: JSON.stringify({
        symbols: [stock.symbol],
        days: windowDays,
        use_llm: useLlm !== false,
        crawl_community: true,
        community_limit: 120,
        evidence_limit: 120
      })
    });
    sentimentRefreshResults.set(stock.symbol, result);
    clearSentimentPayloadCache(stock.symbol);
    stockDetailCache.delete(stock.symbol);
    stockDetailErrors.delete(stock.symbol);
    await loadStockDetail(stock.symbol, stock.market);
    const refreshed = stockBySymbol(stock.symbol) ?? stock;
    renderDetails(refreshed);
    scheduleStockListRefresh();
    updateBackendStatus(`${stock.symbol} 情绪已刷新`);
  } catch (error) {
    sentimentRefreshErrors.set(stock.symbol, error.message);
    apiState.lastError = `${stock.symbol} 情绪刷新失败：${error.message}`;
    updateBackendStatus(apiState.lastError);
    renderSentimentAside(stock, stockDetailCache.get(stock.symbol));
  } finally {
    sentimentRefreshing.delete(stock.symbol);
    sentimentRefreshStartedAt.delete(stock.symbol);
    stopRefreshElapsedTimerIfIdle();
    renderSentimentAside(stockBySymbol(stock.symbol) ?? stock, stockDetailCache.get(stock.symbol));
  }
}

function toggleSentimentEvidence(type) {
  const stock = selectedStock();
  if (!stock) return;
  const detail = stockDetailCache.get(stock.symbol);
  const snapshot = detail?.information?.sentiment;
  const current = sentimentExpandedTypes.get(stock.symbol);
  if (current === type) {
    sentimentExpandedTypes.delete(stock.symbol);
    renderSentimentAside(stock, detail);
    return;
  }
  sentimentExpandedTypes.set(stock.symbol, type);
  renderSentimentAside(stock, detail);
  if (snapshot) {
    void loadSentimentPayload(stock.symbol, sentimentWindowDays(snapshot));
  }
}

function toggleCommunityClassFilter(filterClass) {
  const stock = selectedStock();
  if (!stock) return;
  const normalized = communityClassOrder.includes(filterClass) ? filterClass : "";
  const current = communityClassFilters.get(stock.symbol) || "";
  if (!normalized || current === normalized) communityClassFilters.delete(stock.symbol);
  else communityClassFilters.set(stock.symbol, normalized);
  const detail = stockDetailCache.get(stock.symbol);
  renderSentimentAside(stock, detail);
}

async function saveSearchHistory(surface, query, metadata = {}) {
  const clean = String(query ?? "").trim();
  if (!clean || !apiState.connected) return;
  try {
    await apiRequest("/api/search-history", {
      method: "POST",
      body: JSON.stringify({
        account_id: apiState.accountId,
        surface,
        query: clean,
        metadata
      })
    });
    await loadSearchHistory();
  } catch (error) {
    apiState.lastError = `搜索历史保存失败：${error.message}`;
    updateBackendStatus(apiState.lastError);
  }
}

async function loadSearchHistory() {
  if (!apiState.connected) {
    searchHistoryItems = [];
    renderSearchHistories();
    return;
  }
  try {
    const params = new URLSearchParams({ account_id: apiState.accountId, limit: "80" });
    const payload = await apiRequest(`/api/search-history?${params.toString()}`);
    searchHistoryItems = Array.isArray(payload.items) ? payload.items : [];
  } catch (error) {
    searchHistoryItems = [];
  }
  renderSearchHistories();
}

function renderSearchHistories() {
  searchHistoryBindings.forEach((binding) => {
    const input = binding.input();
    if (!input) return;
    const row = ensureSearchHistoryRow(input, binding.surface);
    if (!row) return;
    const items = searchHistoryItems
      .filter((item) => item.surface === binding.surface)
      .slice(0, 6);
    row.hidden = !items.length;
    row.innerHTML = items.length
      ? `
        <span>历史</span>
        ${items.map((item) => `
          <button type="button" data-history-surface="${escapeHTML(binding.surface)}" data-history-value="${escapeHTML(item.query)}">
            ${escapeHTML(item.query)}
          </button>
        `).join("")}
      `
      : "";
  });
}

function ensureSearchHistoryRow(input, surface) {
  const searchBox = input.closest(".search-box");
  const anchor = searchBox ?? input.closest("label") ?? input;
  let row = document.querySelector(`[data-search-history-row="${CSS.escape(surface)}"]`);
  if (!row || !document.body.contains(row)) {
    row = document.createElement("div");
    row.className = "search-history-row";
    row.dataset.searchHistoryRow = surface;
  }
  if (searchBox || anchor.tagName === "LABEL") {
    if (row.parentElement !== anchor) anchor.append(row);
  } else if (row.previousElementSibling !== anchor) {
    anchor.insertAdjacentElement("afterend", row);
  }
  return row;
}

function applySearchHistoryValue(surface, value) {
  const binding = searchHistoryBindings.find((item) => item.surface === surface);
  const input = binding?.input();
  if (input) input.value = value;
  if (surface === "stock_analysis") {
    hideStockSearchSuggestions();
    selectStock(value);
  }
  else if (surface === "filter_prompt") applyNaturalLanguageFilter();
  else if (surface === "anomaly_stock") renderAnomalyStockList();
  else if (surface === "anomaly_prompt") renderPromptAnomalyReport();
}

function normalizeBackendTrade(trade) {
  return {
    id: trade.id,
    symbol: trade.symbol,
    side: trade.side,
    date: trade.date,
    quantity: Number(trade.quantity),
    price: Number(trade.price),
    fee: Number(trade.fee ?? 0)
  };
}

function updateBackendStatus(message = "") {
  if (!backendStatus || !sharedCacheStatus) return;
  const statusText = message || (apiState.connected ? "数据 API connected" : "本地 fallback");
  backendStatus.textContent = statusText.length > 28 ? `${statusText.slice(0, 27)}…` : statusText;
  backendStatus.className = `status-chip ${apiState.connected ? "fresh" : "warn"}`;
  backendStatus.title = message || apiState.lastError || "前端可在后端关闭时继续使用本地缓存。";

  if (apiState.sharedCache) {
    sharedCacheStatus.textContent = `共享分析 ${apiState.sharedCache.stock_analysis_runs} 条`;
    sharedCacheStatus.title = "股票分析、异动分析和记忆是跨账户共享资产。";
  } else {
    sharedCacheStatus.textContent = "共享分析 local";
    sharedCacheStatus.title = "当前使用前端本地共享分析缓存。";
  }
}

function normalizeApiStock(stock) {
  return {
    ...stock,
    metrics: stock.metrics ?? metricProfiles[stock.symbol],
    evidence: stock.evidence ?? [],
    reflection: stock.reflection ?? []
  };
}

function mergeApiStocks(apiStocks) {
  const enriched = (Array.isArray(apiStocks) ? apiStocks : [])
    .map(normalizeApiStock)
    .map((stock) => enrichStock(stock));
  enriched.forEach((item) => {
    const index = stocks.findIndex((existing) => existing.symbol === item.symbol);
    if (index >= 0) stocks[index] = item;
    else stocks.push(item);
  });
  return enriched;
}

function scheduleStockSearchSuggestions() {
  window.clearTimeout(stockSearchTimer);
  const query = symbolInput.value.trim();
  if (!query) {
    hideStockSearchSuggestions();
    return;
  }
  stockSearchTimer = window.setTimeout(() => {
    void loadStockSearchSuggestions(query);
  }, 120);
}

async function loadStockSearchSuggestions(query = symbolInput.value.trim()) {
  const clean = String(query ?? "").trim();
  const requestId = ++stockSearchRequestId;
  if (!clean) {
    hideStockSearchSuggestions();
    return;
  }

  stockSearchOpen = true;
  stockSearchLoading = true;
  stockSearchError = "";
  highlightedStockSuggestion = -1;
  renderStockSearchSuggestions();

  try {
    let suggestions = [];
    if (apiState.connected) {
      const params = new URLSearchParams({
        q: clean,
        market: activeMarket,
        account_id: apiState.accountId,
        record: "false",
        limit: "8"
      });
      const payload = await apiRequest(`/api/stocks/search?${params.toString()}`);
      suggestions = mergeApiStocks(payload.stocks).slice(0, 8);
    } else {
      suggestions = localStockSuggestions(clean).slice(0, 8);
    }
    if (requestId !== stockSearchRequestId) return;
    stockSearchSuggestions = suggestions;
  } catch (error) {
    if (requestId !== stockSearchRequestId) return;
    stockSearchSuggestions = [];
    stockSearchError = error.message;
  } finally {
    if (requestId === stockSearchRequestId) {
      stockSearchLoading = false;
      renderStockSearchSuggestions();
    }
  }
}

function localStockSuggestions(query) {
  const normalized = String(query ?? "").trim().toLowerCase().replace(/\s+/g, "");
  if (!normalized) return [];
  const aliasSymbol = stockSearchAliasSymbol(normalized);
  const matches = stocks.filter((stock) => {
    const symbol = stock.symbol.toLowerCase();
    const code = symbol.split(".")[0];
    const name = stock.name.toLowerCase();
    return stock.symbol === aliasSymbol
      || symbol.includes(normalized)
      || code.includes(normalized)
      || name.includes(normalized);
  });
  return matches.sort((a, b) => stockSuggestionRank(a, normalized, aliasSymbol) - stockSuggestionRank(b, normalized, aliasSymbol));
}

function stockSearchAliasSymbol(normalized) {
  if (["hd", "hdz", "hdzz"].includes(normalized)) return "688114.SH";
  return "";
}

function stockSuggestionRank(stock, normalized, aliasSymbol = "") {
  const symbol = stock.symbol.toLowerCase();
  const code = symbol.split(".")[0];
  const name = stock.name.toLowerCase();
  if (aliasSymbol && stock.symbol === aliasSymbol) return 0;
  if ([symbol, code, name].includes(normalized)) return 1;
  if (symbol.startsWith(normalized) || code.startsWith(normalized)) return 2;
  if (name.startsWith(normalized)) return 3;
  return 8;
}

function renderStockSearchSuggestions() {
  if (!stockSearchList || !symbolInput) return;
  const query = symbolInput.value.trim();
  const shouldShow = stockSearchOpen && query;
  stockSearchList.hidden = !shouldShow;
  symbolInput.setAttribute("aria-expanded", shouldShow ? "true" : "false");
  if (!shouldShow) {
    stockSearchList.innerHTML = "";
    return;
  }
  if (stockSearchLoading) {
    stockSearchList.innerHTML = `
      <div class="stock-suggestion-head">股票</div>
      <div class="stock-suggestion-empty">正在搜索...</div>
    `;
    return;
  }
  if (stockSearchError) {
    stockSearchList.innerHTML = `
      <div class="stock-suggestion-head">股票</div>
      <div class="stock-suggestion-empty">搜索失败：${escapeHTML(stockSearchError)}</div>
    `;
    return;
  }
  if (!stockSearchSuggestions.length) {
    stockSearchList.innerHTML = `
      <div class="stock-suggestion-head">股票</div>
      <div class="stock-suggestion-empty">没有匹配股票。</div>
    `;
    return;
  }
  stockSearchList.innerHTML = `
    <div class="stock-suggestion-head">股票</div>
    ${stockSearchSuggestions.map((stock, index) => `
      <button
        id="stock-search-option-${index}"
        class="stock-suggestion ${index === highlightedStockSuggestion ? "active" : ""}"
        data-stock-suggestion="${escapeHTML(stock.symbol)}"
        type="button"
        role="option"
        aria-selected="${index === highlightedStockSuggestion ? "true" : "false"}"
      >
        <strong>${escapeHTML(stock.name)}</strong>
        <em>${escapeHTML(stock.symbol)}</em>
        <small>${escapeHTML(stock.marketLabel ?? stock.market)} · ${escapeHTML(stock.industry ?? stock.currency ?? "")}</small>
      </button>
    `).join("")}
  `;
}

function hideStockSearchSuggestions() {
  window.clearTimeout(stockSearchTimer);
  stockSearchOpen = false;
  stockSearchLoading = false;
  stockSearchError = "";
  highlightedStockSuggestion = -1;
  renderStockSearchSuggestions();
}

function chooseStockSearchSuggestion(symbol) {
  const stock = stockBySymbol(symbol) || stockSearchSuggestions.find((item) => item.symbol === symbol);
  if (!stock) return;
  symbolInput.value = stock.name;
  hideStockSearchSuggestions();
  void saveSearchHistory("stock_analysis", stock.symbol);
  selectStock(stock.symbol);
}

function submitStockSearch() {
  const raw = symbolInput.value.trim();
  const exact = stockByQuery(raw);
  const suggestion = highlightedStockSuggestion >= 0
    ? stockSearchSuggestions[highlightedStockSuggestion]
    : (!exact ? stockSearchSuggestions[0] : null);
  if (suggestion) {
    chooseStockSearchSuggestion(suggestion.symbol);
    return;
  }
  hideStockSearchSuggestions();
  void saveSearchHistory("stock_analysis", raw);
  selectStock(raw);
}

function populateAccountSelect() {
  if (!accountSelect || !apiState.accounts.length) return;
  accountSelect.innerHTML = apiState.accounts.map((account) => `
    <option value="${account.id}" ${account.id === apiState.accountId ? "selected" : ""}>${account.name}</option>
  `).join("");
}

async function loadIndustryOptions() {
  if (!industryFilter) return;
  if (!apiState.connected) {
    industryOptions = localIndustryOptions();
    renderIndustryFilter();
    return;
  }
  try {
    const params = new URLSearchParams({ market: activeMarket });
    const payload = await apiRequest(`/api/screeners/industries?${params.toString()}`);
    industryOptions = Array.isArray(payload.industries) ? payload.industries : [];
  } catch (error) {
    industryOptions = localIndustryOptions();
  }
  if (activeIndustry && !industryOptions.some((item) => item.industry === activeIndustry)) {
    activeIndustry = "";
  }
  renderIndustryFilter();
}

function localIndustryOptions() {
  const counts = new Map();
  stocks
    .filter((stock) => activeMarket === "all" || stock.market === activeMarket)
    .forEach((stock) => {
      [stock.industry, stock.sector].forEach((value) => {
        const industry = String(value ?? "").trim();
        if (!industry) return;
        counts.set(industry, (counts.get(industry) ?? 0) + 1);
      });
    });
  return [...counts.entries()]
    .map(([industry, count]) => ({ industry, count }))
    .sort((a, b) => b.count - a.count || a.industry.localeCompare(b.industry, "zh-CN"));
}

function renderIndustryFilter() {
  if (!industryFilter) return;
  industryFilter.innerHTML = `
    <option value="">全部行业/板块</option>
    ${industryOptions.map((item) => `
      <option value="${escapeHTML(item.industry)}" ${item.industry === activeIndustry ? "selected" : ""}>
        ${escapeHTML(item.industry)}（${Number(item.count ?? 0)}）
      </option>
    `).join("")}
  `;
}

async function loadStocksFromApi() {
  if (!apiState.connected) return;
  const params = new URLSearchParams({
    account_id: apiState.accountId,
    record: "false",
    limit: String(STOCK_CARD_RENDER_LIMIT)
  });
  const data = await apiRequest(`/api/stocks/search?${params.toString()}`);
  if (!Array.isArray(data.stocks) || !data.stocks.length) return;
  stocks = data.stocks.map(normalizeApiStock).map((stock) => enrichStock(stock));
  screenerStocks = [];
  databaseScreenerActive = false;
  if (!stockBySymbol(selectedSymbol)) selectedSymbol = stocks[0].symbol;
  if (!stockBySymbol(selectedAnomalySymbol)) selectedAnomalySymbol = stocks[0].symbol;
}

function applyDataSourcePayload(payload) {
  dataSources = Array.isArray(payload?.sources) ? payload.sources : fallbackDataSources;
  apiState.sourceSummary = payload?.summary ?? null;
  renderDataSources();
  renderSourceNotifications();
  renderHealth();
  renderSourceTests();
}

async function loadAkshareCapabilities() {
  if (!apiState.connected) {
    aksharePayload = null;
    aksharePreviewPayload = null;
    aksharePreviewError = "";
    renderAkshareExplorer();
    return;
  }
  try {
    aksharePayload = await apiRequest("/api/akshare/capabilities");
    const groups = aksharePayload.groups ?? [];
    if (!groups.some((group) => group.id === activeAkshareCategory)) {
      activeAkshareCategory = groups[0]?.id ?? "stock";
    }
    aksharePreviewError = "";
  } catch (error) {
    aksharePayload = null;
    aksharePreviewPayload = null;
    aksharePreviewError = `AKShare 能力清单加载失败：${error.message}`;
  }
  renderAkshareExplorer();
}

async function loadAlphaVantageCapabilities() {
  if (!apiState.connected) {
    alphaVantagePayload = null;
    alphaVantagePreviewPayload = null;
    alphaVantagePreviewError = "";
    renderAlphaVantageExplorer();
    return;
  }
  try {
    const params = new URLSearchParams({ account_id: apiState.accountId });
    alphaVantagePayload = await apiRequest(`/api/alpha-vantage/capabilities?${params.toString()}`);
    const groups = alphaVantagePayload.groups ?? [];
    if (!groups.some((group) => group.id === activeAlphaVantageCategory)) {
      activeAlphaVantageCategory = groups[0]?.id ?? "market";
    }
    alphaVantagePreviewError = "";
  } catch (error) {
    alphaVantagePayload = null;
    alphaVantagePreviewPayload = null;
    alphaVantagePreviewError = `Alpha Vantage 能力清单加载失败：${error.message}`;
  }
  renderAlphaVantageExplorer();
}

async function loadSourceTestCatalog() {
  if (!apiState.connected) {
    sourceTestCatalog = null;
    sourceTestPayload = null;
    sourceTestError = "";
    renderSourceTests();
    return;
  }
  try {
    const params = new URLSearchParams({ account_id: apiState.accountId });
    sourceTestCatalog = await apiRequest(`/api/data-source-tests/catalog?${params.toString()}`);
    const tests = sourceTestCatalog.tests ?? [];
    if (!tests.some((item) => item.id === selectedSourceTestId)) {
      selectedSourceTestId = tests[0]?.id ?? "";
    }
    sourceTestError = "";
  } catch (error) {
    sourceTestCatalog = null;
    sourceTestPayload = null;
    sourceTestError = `数据源测试清单加载失败：${error.message}`;
  }
  renderSourceTests();
  renderHealth();
}

async function loadAccountFromApi(accountId = apiState.accountId) {
  try {
    const data = await apiRequest(`/api/bootstrap?account_id=${encodeURIComponent(accountId)}`);
    apiState.connected = true;
    apiState.accountId = data.account.id;
    apiState.accounts = data.accounts;
    apiState.sharedCache = data.shared_cache;
    apiState.sourceSummary = data.data_sources?.summary ?? null;
    apiState.portfolio = data.portfolio;
    apiState.lastError = "";
    applyDataSourcePayload(data.data_sources);
    await loadAkshareCapabilities();
    await loadAlphaVantageCapabilities();
    await loadSourceTestCatalog();
    await loadStocksFromApi();
    await loadIndustryOptions();
    await loadSearchHistory();
    favoriteSymbols = new Set(data.favorites);
    portfolioTrades = data.trades.map(normalizeBackendTrade);
    selectedHoldingSymbol = openPositions()[0]?.symbol ?? "";
    populateAccountSelect();
    updateBackendStatus(`已连接 ${data.account.name}`);
    populateTradeForm();
    renderCandidates();
    renderDetails(selectedStock() ?? stocks[0]);
    renderWatchlist();
    renderStockAnomalyReport(selectedAnomalySymbol);
    maybeAutoRunBacktest();
  } catch (error) {
    apiState.connected = false;
    apiState.sharedCache = null;
    apiState.sourceSummary = null;
    apiState.portfolio = null;
    screenerStocks = [];
    databaseScreenerActive = false;
    apiState.lastError = `数据 API 未连接：${error.message}`;
    applyDataSourcePayload({ sources: fallbackDataSources });
    await loadAkshareCapabilities();
    await loadAlphaVantageCapabilities();
    await loadSourceTestCatalog();
    await loadIndustryOptions();
    updateBackendStatus(apiState.lastError);
    maybeAutoRunBacktest();
  }
}

async function persistFavorite(symbol, favorite) {
  if (!apiState.connected) {
    apiState.lastError = "数据 API 未连接，关注列表无法保存";
    updateBackendStatus(apiState.lastError);
    return false;
  }
  try {
    const data = await apiRequest(`/api/accounts/${encodeURIComponent(apiState.accountId)}/favorites/${encodeURIComponent(symbol)}`, {
      method: "PUT",
      body: JSON.stringify({ favorite })
    });
    favoriteSymbols = new Set(data.favorites);
    return true;
  } catch (error) {
    apiState.lastError = `关注列表同步失败：${error.message}`;
    updateBackendStatus(apiState.lastError);
    return false;
  }
}

async function persistTrade(trade) {
  if (!apiState.connected) return trade;
  const data = await apiRequest(`/api/accounts/${encodeURIComponent(apiState.accountId)}/trades`, {
    method: "POST",
    body: JSON.stringify({
      symbol: trade.symbol,
      side: trade.side,
      date: trade.date,
      quantity: trade.quantity,
      price: trade.price,
      fee: trade.fee
    })
  });
  if (data.portfolio) apiState.portfolio = data.portfolio;
  return normalizeBackendTrade(data.trade);
}

function backendPortfolio() {
  return apiState.connected && apiState.portfolio ? apiState.portfolio : null;
}

function backendPositionFor(symbol) {
  return backendPortfolio()?.positions.find((position) => position.symbol === symbol);
}

function syncStocksFromBackendPortfolio(portfolio) {
  if (!portfolio?.positions) return;
  portfolio.positions.forEach((position) => {
    const stock = stockBySymbol(position.symbol);
    if (!stock) return;
    const nextPrice = Number(position.current_price);
    if (!Number.isFinite(nextPrice) || nextPrice <= 0) return;
    stock.price = nextPrice;
    stock.lagMinutes = 0;
    stock.freshnessStatus = "fresh";
    stock.spark = [...stock.spark.slice(1), nextPrice];
  });
}

function filteredStocks() {
  const source = apiState.connected && databaseScreenerActive ? screenerStocks : stocks;
  const marketList = activeMarket === "all" ? source : source.filter((stock) => stock.market === activeMarket);
  const industryList = activeIndustry ? marketList.filter(stockMatchesActiveIndustry) : marketList;
  if (apiState.connected && databaseScreenerActive) return industryList;
  const activeRulesList = [...activeFilterIds].map((id) => filtersById.get(id)).filter(Boolean);
  if (!activeRulesList.length) return industryList;
  return industryList.filter((stock) => {
    const results = activeRulesList.map((rule) => rule.test(stock));
    return filterMode === "all" ? results.every(Boolean) : results.some(Boolean);
  });
}

function stockMatchesActiveIndustry(stock) {
  const target = compactFilterLabel(activeIndustry);
  if (!target) return true;
  return [stock.industry, stock.sector].some((value) => compactFilterLabel(value) === target);
}

function compactFilterLabel(value) {
  return String(value ?? "").trim().replace(/\s+/g, "").toLowerCase();
}

function renderFilterGroups() {
  filterGroups.innerHTML = filterCatalog.map((group) => `
    <section class="filter-group">
      <h4>${escapeHTML(group.group)}</h4>
      <div class="filter-options">
        ${group.items.map((item) => `
          <div class="check-row">
            <input id="filter-${escapeHTML(item.id)}" type="checkbox" data-filter-id="${escapeHTML(item.id)}" ${activeFilterIds.has(item.id) ? "checked" : ""} />
            <div class="check-copy">
              <div class="check-title">
                <label for="filter-${escapeHTML(item.id)}"><strong>${escapeHTML(item.label)}</strong></label>
                <button class="rule-help" type="button" aria-label="查看 ${escapeHTML(item.label)} 的解释" aria-describedby="filter-help-${escapeHTML(item.id)}">?</button>
                <span id="filter-help-${escapeHTML(item.id)}" class="rule-tooltip" role="tooltip">${escapeHTML(item.logic ?? "")}</span>
              </div>
            </div>
          </div>
        `).join("")}
      </div>
    </section>
  `).join("");
  renderActiveRules();
}

function renderActiveRules() {
  const rules = [...activeFilterIds].map((id) => filtersById.get(id)).filter(Boolean);
  const promptText = filterPrompt.value.trim();
  const rulePills = rules.map((rule) => `<span class="rule-pill">${rule.label}</span>`);
  if (activeIndustry) rulePills.unshift(`<span class="rule-pill">行业：${escapeHTML(activeIndustry)}</span>`);
  if (promptText) rulePills.push(`<span class="rule-pill">自然语言：${escapeHTML(promptText)}</span>`);
  activeRules.innerHTML = rulePills.length
    ? rulePills.join("")
    : `<span class="rule-pill muted">未启用过滤</span>`;
}

async function applyNaturalLanguageFilter() {
  const rawText = filterPrompt.value.trim();
  const text = rawText.toLowerCase();
  if (text) {
    void saveSearchHistory("filter_prompt", filterPrompt.value);
    if (text.includes("宽松") || text.includes("任一") || text.includes("或者")) {
      filterMode = "any";
      syncFilterModeButtons();
    }
    const matchedIndustry = industryFromPrompt(rawText);
    if (matchedIndustry) {
      activeIndustry = matchedIndustry;
      if (industryFilter) industryFilter.value = matchedIndustry;
      filterPrompt.value = "";
    }
  }
  renderActiveRules();
  await runDatabaseScreener();
}

function industryFromPrompt(value) {
  const clean = String(value ?? "").trim().replace(/^行业\s*(?:=|是|为|:|：)\s*/, "");
  if (!clean) return "";
  const exact = industryOptions.find((item) => item.industry === clean);
  if (exact) return exact.industry;
  const compact = clean.replace(/\s+/g, "").toLowerCase();
  const fuzzy = industryOptions.find((item) => item.industry.replace(/\s+/g, "").toLowerCase() === compact);
  if (fuzzy) return fuzzy.industry;
  const contained = industryOptions.find((item) => {
    const industry = item.industry.replace(/\s+/g, "").toLowerCase();
    return compact.length >= 2 && (compact.includes(industry) || industry.includes(compact));
  });
  return contained?.industry ?? "";
}

async function runDatabaseScreener() {
  if (!apiState.connected) {
    screenerStocks = [];
    databaseScreenerActive = false;
    renderCandidates();
    return;
  }
  const requestId = ++screenerRequestId;
  renderScreenerLoading();
  try {
    updateBackendStatus("数据库筛选中");
    const payload = await apiRequest("/api/screeners/run", {
      method: "POST",
      body: JSON.stringify({
        market: activeMarket,
        industry: activeIndustry,
        filter_ids: [...activeFilterIds],
        mode: filterMode,
        natural_query: filterPrompt.value.trim(),
        account_id: apiState.accountId
      })
    });
    if (requestId !== screenerRequestId) return;
    const apiStocks = Array.isArray(payload.stocks) ? payload.stocks : [];
    screenerStocks = mergeApiStocks(apiStocks);
    databaseScreenerActive = true;
    if (screenerStocks.length && !screenerStocks.some((stock) => stock.symbol === selectedSymbol)) {
      selectedSymbol = screenerStocks[0].symbol;
    }
    renderCandidates();
    renderWatchlist();
    renderStockAnomalyReport(selectedAnomalySymbol);
    const warehouse = payload.warehouse ?? {};
    updateBackendStatus(`数据库筛选完成：${payload.count ?? stocks.length} 只，历史日线 ${warehouse.daily_bars ?? 0} 条`);
  } catch (error) {
    if (requestId !== screenerRequestId) return;
    apiState.lastError = `数据库筛选失败：${error.message}`;
    updateBackendStatus(apiState.lastError);
    screenerStocks = [];
    databaseScreenerActive = false;
    renderCandidates();
  }
}

function renderScreenerLoading() {
  const message = `<div class="empty-state">正在筛选完整股票池，请稍候...</div>`;
  if (candidateCount) candidateCount.textContent = "筛选中";
  if (filterResultCount) filterResultCount.textContent = "筛选中";
  if (candidateGrid) candidateGrid.innerHTML = message;
  if (filterResultGrid) filterResultGrid.innerHTML = message;
}

function renderCandidates() {
  const list = filteredStocks();
  candidateCount.textContent = `${list.length} 只`;
  if (candidateGrid) candidateGrid.innerHTML = renderStockCardList(list);
  if (filterResultCount) filterResultCount.textContent = `${list.length} 只`;
  if (filterResultGrid) filterResultGrid.innerHTML = renderStockCardList(list);
  scheduleSparklineDraw();
  renderAnomalyStockList();
}

function renderStockCardList(list) {
  if (!list.length) return `<div class="empty-state">当前过滤组合没有匹配股票。</div>`;
  const visible = list.slice(0, STOCK_CARD_RENDER_LIMIT);
  const remainder = list.length - visible.length;
  return `
    ${visible.map(renderStockCard).join("")}
    ${remainder > 0 ? `
      <div class="empty-state result-limit-note">
        已显示前 ${visible.length} 只，共 ${list.length} 只。继续增加条件或行业筛选可以缩小结果。
      </div>
    ` : ""}
  `;
}

function anomalyUniverse() {
  const bySymbol = new Map();
  filteredStocks().forEach((stock) => bySymbol.set(stock.symbol, stock));
  [...favoriteSymbols].map(stockBySymbol).filter(Boolean).forEach((stock) => bySymbol.set(stock.symbol, stock));
  openPositions().forEach((position) => bySymbol.set(position.symbol, position.stock));
  return [...bySymbol.values()];
}

function renderAnomalyStockList() {
  const query = anomalyStockSearch?.value.trim().toLowerCase() ?? "";
  const universe = anomalyUniverse();
  const filtered = universe.filter((stock) => {
    if (!query) return true;
    return stock.symbol.toLowerCase().includes(query) || stock.name.toLowerCase().includes(query);
  });
  anomalyUniverseCount.textContent = `${universe.length} 只`;
  anomalyStockList.innerHTML = filtered.length ? filtered.map((stock) => `
    <button class="anomaly-stock-button ${stock.symbol === selectedAnomalySymbol ? "active" : ""}" data-anomaly-symbol="${stock.symbol}" type="button">
      <span>
        <strong>${stock.symbol}</strong>
        <small>${stock.name} · ${stock.marketLabel}</small>
      </span>
      <em class="${stock.change >= 0 ? "up" : "down"}">${stock.change >= 0 ? "+" : ""}${stock.change.toFixed(1)}%</em>
    </button>
  `).join("") : `<div class="empty-state compact">没有匹配股票。</div>`;
}

function renderStockAnomalyReport(symbol) {
  const stock = stockBySymbol(symbol);
  if (!stock) return;
  selectedAnomalySymbol = stock.symbol;
  const direction = stock.change >= 0 ? "上行异动" : "下行异动";
  const severity = Math.min(95, Math.round(Math.abs(stock.change) * 12 + stock.metrics.volumeRatio * 18 + stock.metrics.newsCount72h * 0.6));
  const topFactor = Object.entries(stock.factors).sort((a, b) => b[1] - a[1])[0];
  const weakFactor = Object.entries(stock.factors).sort((a, b) => a[1] - b[1])[0];
  const causes = stock.change >= 0
    ? [
        `${topFactor[0]}评分 ${topFactor[1]}，说明资金更愿意交易该方向的正向叙事。`,
        `量能 ${stock.metrics.volumeRatio.toFixed(2)} 倍，成交确认强于普通波动。`,
        `72小时新闻 ${stock.metrics.newsCount72h} 条，情绪分 ${stock.metrics.sentimentScore}。`
      ]
    : [
        `${weakFactor[0]}评分 ${weakFactor[1]}，当前短板可能被市场放大。`,
        `60日最大回撤 ${stock.metrics.maxDrawdown60d}%，波动风险处在需要复核区间。`,
        `未证实比例 ${(stock.metrics.unverifiedRatio * 100).toFixed(0)}%，需要防止传闻引发误判。`
      ];

  anomalyReport.innerHTML = `
    <div class="report-head">
      <div>
        <p class="eyebrow">Stock anomaly · Data API</p>
        <h4>${stock.symbol} · ${stock.name}</h4>
      </div>
      <span class="anomaly-score">${severity}</span>
    </div>
    <p class="thesis">${direction}：当前变化 ${stock.change >= 0 ? "+" : ""}${stock.change.toFixed(1)}%，核心判断是“价格变化 + 量能 + 证据质量”共同触发异动复核。</p>
    <div class="anomaly-metrics">
      <div><span>成交额</span><strong>${formatCnyAmount(stock.metrics.avgAmountCny)}</strong></div>
      <div><span>量能</span><strong>${stock.metrics.volumeRatio.toFixed(2)}x</strong></div>
      <div><span>新闻热度</span><strong>${stock.metrics.newsCount72h}</strong></div>
      <div><span>未证实</span><strong>${(stock.metrics.unverifiedRatio * 100).toFixed(0)}%</strong></div>
    </div>
    <section class="report-section">
      <h4>可能原因</h4>
      <ul>${causes.map((item) => `<li>${item}</li>`).join("")}</ul>
    </section>
    <section class="report-section">
      <h4>证据和限制</h4>
      <ul>
        <li>证据可信度 ${stock.truthScore}%，数据状态 ${statusText(stock.freshnessStatus)}。</li>
        <li>本报告使用当前接入的数据源快照；盘中结论需要拉取最新盘口、逐笔、公告和新闻源。</li>
        <li>若数据过期或未证实比例过高，只能作为异动提醒，不能直接升级为买卖结论。</li>
      </ul>
    </section>
    <div class="inline-actions">
      <button class="mini-action" data-anomaly-open-stock="${stock.symbol}" type="button">查看单股分析</button>
      <button class="mini-action" data-refresh-source="market" type="button">刷新行情</button>
    </div>
  `;
  renderAnomalyStockList();
}

function renderPromptAnomalyReport() {
  const text = anomalyPrompt.value.trim();
  if (!text) return;
  void saveSearchHistory("anomaly_prompt", text);
  const normalized = text.toLowerCase();
  const isSector = text.includes("板块") || text.includes("电力") || text.includes("新能源") || text.includes("银行");
  const isMarket = text.includes("大盘") || text.includes("指数") || text.includes("市场");
  const title = isSector ? "板块异动解释" : isMarket ? "大盘异动解释" : "主题异动解释";
  const subject = text.includes("电力") ? "电力板块" : isMarket ? "大盘" : text;
  const negative = text.includes("跳水") || text.includes("下跌") || text.includes("杀跌") || normalized.includes("crash");
  const direction = negative ? "下行异动" : "波动异动";
  const related = anomalyUniverse()
    .filter((stock) => {
      if (text.includes("电力")) return ["600519.SH", "002594.SZ"].includes(stock.symbol) === false;
      if (isMarket) return true;
      return stock.name.includes(text) || text.includes(stock.name) || text.includes(stock.symbol);
    })
    .slice(0, 4);

  anomalyReport.innerHTML = `
    <div class="report-head">
      <div>
        <p class="eyebrow">Question anomaly · Data API</p>
        <h4>${title}</h4>
      </div>
      <span class="anomaly-score">${negative ? 78 : 62}</span>
    </div>
    <p class="thesis">${subject}出现${direction}时，优先拆成三层：指数/板块同步性、资金流和消息面真实性。本报告是数据推理模板，实时结论取决于当前数据源新鲜度。</p>
    <section class="report-section">
      <h4>可能解释路径</h4>
      <ul>
        <li>先看是否是系统性风险：若多数行业同步走弱，个股原因权重要下降。</li>
        <li>再看板块内部扩散：龙头、补涨、题材股是否同时放量下跌。</li>
        <li>最后查消息真实性：政策传闻、业绩预期、商品价格、利率汇率变化都要回到官方或高等级来源。</li>
      </ul>
    </section>
    <section class="report-section">
      <h4>需要拉取的实时数据</h4>
      <ul>
        <li>指数分时、板块涨跌分布、成交额排名、北向/南向或主力资金。</li>
        <li>板块核心股票的盘口价差、放量倍数、跌破均线情况。</li>
        <li>过去 24 小时公告、监管新闻、行业政策和高可信媒体报道。</li>
      </ul>
    </section>
    <section class="report-section">
      <h4>相关股票池</h4>
      <div class="related-stock-row">
        ${related.length ? related.map((stock) => `<button class="mini-action" data-anomaly-symbol="${stock.symbol}" type="button">${stock.symbol} ${stock.name}</button>`).join("") : "暂无匹配股票，建议先扩大股票池。"}
      </div>
    </section>
  `;
}

function backtestConfigFromForm() {
  return {
    strategy: backtestStrategy?.value ?? "quality_momentum",
    market: backtestMarket?.value ?? "all",
    start_date: backtestStart?.value || "2026-03-02",
    end_date: backtestEnd?.value || "2026-06-05",
    max_positions: Number(backtestPositions?.value || 3),
    initial_cash: 1000000,
    fee_bps: Number(backtestFee?.value || 8),
    slippage_bps: Number(backtestSlippage?.value || 5),
    rebalance: backtestRebalance?.value ?? "monthly"
  };
}

async function handleBacktestSubmit(event) {
  event?.preventDefault();
  await runBacktest(backtestConfigFromForm());
}

async function runBacktest(config = backtestConfigFromForm()) {
  backtestLoading = true;
  backtestError = "";
  renderBacktestResult();
  try {
    backtestPayload = apiState.connected
      ? await apiRequest("/api/backtests/run", { method: "POST", body: JSON.stringify(config) })
      : localBacktestPayload(config);
  } catch (error) {
    backtestPayload = null;
    backtestError = `回测失败：${error.message}`;
  } finally {
    backtestLoading = false;
    renderBacktestResult();
  }
}

function maybeAutoRunBacktest() {
  if (activeTab !== "backtests" || backtestPayload || backtestLoading || backtestError || backtestAutoRunQueued) return;
  if (!apiState.connected && !apiState.lastError) return;
  backtestAutoRunQueued = true;
  requestIdleTask(async () => {
    backtestAutoRunQueued = false;
    if (activeTab !== "backtests" || backtestPayload || backtestLoading || backtestError) return;
    await runBacktest();
  });
}

function renderBacktestResult() {
  if (!backtestResult) return;
  if (backtestStatus) {
    backtestStatus.textContent = backtestLoading ? "运行中" : backtestPayload ? "已生成报告" : "研究回测";
  }
  if (backtestLoading) {
    backtestResult.innerHTML = `<div class="empty-state compact">正在运行回测...</div>`;
    return;
  }
  if (backtestError) {
    backtestResult.innerHTML = `<div class="empty-state compact">${escapeHTML(backtestError)}</div>`;
    return;
  }
  if (!backtestPayload) {
    backtestResult.innerHTML = `<div class="empty-state compact">选择策略和参数后运行回测。这里会展示收益曲线、回撤、换手、调仓记录、归因和研究限制。</div>`;
    return;
  }

  const summary = backtestPayload.summary ?? {};
  const strategy = backtestPayload.strategy ?? {};
  const attribution = backtestPayload.attribution ?? {};
  const logs = backtestPayload.rebalance_log ?? [];
  const notes = backtestPayload.research_notes ?? [];
  backtestResult.innerHTML = `
    <div class="thesis">
      <strong>${escapeHTML(strategy.label ?? "回测策略")}</strong>
      <p>${escapeHTML(strategy.thesis ?? "用于验证策略假设的研究回测。")}</p>
    </div>
    <div class="backtest-summary-grid">
      ${renderBacktestCard("总收益", formatPct(Number(summary.total_return ?? 0)), Number(summary.total_return ?? 0))}
      ${renderBacktestCard("年化收益", formatPct(Number(summary.annualized_return ?? 0)), Number(summary.annualized_return ?? 0))}
      ${renderBacktestCard("基准收益", formatPct(Number(summary.benchmark_return ?? 0)), Number(summary.benchmark_return ?? 0))}
      ${renderBacktestCard("最大回撤", formatPct(Number(summary.max_drawdown ?? 0)), Number(summary.max_drawdown ?? 0), true)}
      ${renderBacktestCard("波动率", `${Number(summary.volatility ?? 0).toFixed(2)}%`, 0)}
      ${renderBacktestCard("Sharpe", Number(summary.sharpe ?? 0).toFixed(2), Number(summary.sharpe ?? 0))}
      ${renderBacktestCard("胜率", `${Number(summary.win_rate ?? 0).toFixed(2)}%`, Number(summary.win_rate ?? 0))}
      ${renderBacktestCard("换手事件", String(summary.turnover_events ?? 0), 0)}
    </div>
    <div class="backtest-layout">
      <section class="backtest-panel">
        <div class="curve-head">
          <div>
            <p class="eyebrow">Equity curve</p>
            <h4>收益曲线与基准</h4>
          </div>
          <span class="confidence">${escapeHTML(cleanAnalysisCopy(backtestPayload.mode ?? "local"))}</span>
        </div>
        <canvas id="backtestCurve" class="backtest-chart" width="1200" height="320"></canvas>
      </section>
      <section class="backtest-panel">
        <h4>归因摘要</h4>
        <div class="source-meta">
          <span class="status-chip verified">主驱动：${escapeHTML(attribution.main_driver ?? "N/A")}</span>
          <span class="status-chip ${Number(attribution.annualized_excess_vs_benchmark ?? 0) >= 0 ? "fresh" : "warn"}">年化超额 ${formatPct(Number(attribution.annualized_excess_vs_benchmark ?? 0))}</span>
        </div>
        <div class="backtest-log">
          ${renderAttributionList("贡献靠前", attribution.leaders ?? [])}
          ${renderAttributionList("贡献靠后", attribution.laggards ?? [])}
        </div>
      </section>
    </div>
    ${renderBacktestSentimentPanels(backtestPayload.sentiment_panels)}
    <section class="backtest-panel">
      <h4>调仓记录</h4>
      <div class="backtest-log">
        ${logs.length ? logs.map(renderBacktestLog).join("") : `<div class="empty-state compact">当前参数没有产生调仓记录。</div>`}
      </div>
    </section>
    <section class="backtest-panel">
      <h4>研究限制</h4>
      <ul class="backtest-note-list">${notes.map((note) => `<li>${escapeHTML(note)}</li>`).join("")}</ul>
    </section>
  `;
  scheduleBacktestDraw();
}

function renderBacktestCard(label, value, numberValue, invert = false) {
  const positive = invert ? numberValue >= -8 : numberValue >= 0;
  const className = positive ? "profit" : "loss";
  return `
    <article class="backtest-card">
      <span>${label}</span>
      <strong class="${className}">${value}</strong>
    </article>
  `;
}

function renderAttributionList(title, rows) {
  return `
    <article class="backtest-log-item">
      <strong>${title}</strong>
      <div class="backtest-holding-row">
        ${rows.length ? rows.map((row) => `<span>${escapeHTML(row.symbol)} · ${Number(row.score ?? 0).toFixed(1)}</span>`).join("") : "<span>N/A</span>"}
      </div>
    </article>
  `;
}

function renderBacktestLog(item) {
  return `
    <article class="backtest-log-item">
      <strong>${escapeHTML(item.date)}</strong>
      <p class="confidence">${escapeHTML(item.reason ?? "")}</p>
      <div class="backtest-holding-row">
        ${(item.holdings ?? []).map((holding) => `<span>${escapeHTML(holding.symbol)} · ${(Number(holding.weight ?? 0) * 100).toFixed(0)}%</span>`).join("")}
      </div>
    </article>
  `;
}

function renderBacktestSentimentPanels(panels = {}) {
  const dailyRows = panels?.daily_kline?.rows ?? [];
  const realtimeRows = panels?.realtime?.rows ?? [];
  const notes = panels?.notes ?? [];
  return `
    <div class="backtest-sentiment-layout">
      <section class="backtest-panel backtest-sentiment-panel">
        <div class="curve-head">
          <div>
            <p class="eyebrow">Guba sentiment</p>
            <h4>股吧日情绪 × K线</h4>
          </div>
          <span class="confidence">${Number(dailyRows.length || 0)} 条日汇总</span>
        </div>
        <div class="backtest-sentiment-list">
          ${dailyRows.length ? dailyRows.map(renderBacktestSentimentDailyRow).join("") : `<div class="empty-state compact">暂无社区情绪日汇总。</div>`}
        </div>
      </section>
      <section class="backtest-panel backtest-sentiment-panel">
        <div class="curve-head">
          <div>
            <p class="eyebrow">Realtime pulse</p>
            <h4>实时变化</h4>
          </div>
          <span class="confidence">${Number(realtimeRows.length || 0)} 只标的</span>
        </div>
        <div class="backtest-realtime-list">
          ${realtimeRows.length ? realtimeRows.map(renderBacktestRealtimeRow).join("") : `<div class="empty-state compact">暂无实时情绪快照。</div>`}
        </div>
        ${notes.length ? `<div class="backtest-sentiment-notes">${notes.map((note) => `<span>${escapeHTML(note)}</span>`).join("")}</div>` : ""}
      </section>
    </div>
  `;
}

function renderBacktestSentimentDailyRow(row) {
  const score = Number(row.sentiment_score);
  const change = Number(row.change_pct);
  const tone = sentimentToneForType(score, row.sentiment_label, "community");
  const changeClass = Number.isFinite(change) && change >= 0 ? "profit" : "loss";
  const total = Math.max(Number(row.analyzed_count || 0), 1);
  const positiveWidth = Math.max(0, Math.min(100, Number(row.positive_count || 0) / total * 100));
  const neutralWidth = Math.max(0, Math.min(100, Number(row.neutral_count || 0) / total * 100));
  const negativeWidth = Math.max(0, Math.min(100, Number(row.negative_count || 0) / total * 100));
  const keywords = (row.keyword_counts ?? []).slice(0, 4);
  const klineDate = row.kline_trade_date && row.kline_trade_date !== row.trade_date ? ` · K ${row.kline_trade_date}` : "";
  return `
    <article class="backtest-sentiment-row">
      <div class="backtest-sentiment-main">
        <div>
          <strong>${escapeHTML(row.symbol)} ${escapeHTML(row.name || "")}</strong>
          <span>${escapeHTML(row.trade_date || "")}${escapeHTML(klineDate)} · ${Number(row.analyzed_count || 0)} 条</span>
        </div>
        <div class="backtest-sentiment-values">
          <b class="${tone}">${formatSentimentScore(score, 0, "community")}</b>
          <b class="${changeClass}">${formatPct(change)}</b>
        </div>
      </div>
      <div class="backtest-sentiment-bars" aria-hidden="true">
        <span class="cn-up" style="width:${positiveWidth.toFixed(1)}%"></span>
        <span class="neutral" style="width:${neutralWidth.toFixed(1)}%"></span>
        <span class="cn-down" style="width:${negativeWidth.toFixed(1)}%"></span>
      </div>
      <div class="backtest-sentiment-meta">
        <span>正 ${Number(row.positive_count || 0)}</span>
        <span>中 ${Number(row.neutral_count || 0)}</span>
        <span>负 ${Number(row.negative_count || 0)}</span>
        <span>收盘 ${formatDetailNumber(row.close, 2)}</span>
        <span>额 ${formatBacktestAmount(row.amount)}</span>
      </div>
      ${row.conclusion ? `<p>${escapeHTML(row.conclusion)}</p>` : ""}
      ${keywords.length ? `<div class="backtest-sentiment-keywords">${keywords.map((item) => `<mark>${escapeHTML(item.keyword)} ${Number(item.count || 0)}</mark>`).join("")}</div>` : ""}
    </article>
  `;
}

function renderBacktestRealtimeRow(row) {
  const score = Number(row.community_score ?? row.composite_score);
  const change = Number(row.latest_change_pct);
  const tone = sentimentToneForType(score, row.sentiment_label, row.community_score != null ? "community" : "");
  const changeClass = Number.isFinite(change) && change >= 0 ? "profit" : "loss";
  return `
    <article class="backtest-realtime-row">
      <div>
        <strong>${escapeHTML(row.symbol)} ${escapeHTML(row.name || "")}</strong>
        <span>${escapeHTML(row.latest_trade_date || "暂无K线")} · ${escapeHTML(row.kline_provider || "daily_bars")}</span>
      </div>
      <div class="backtest-realtime-metrics">
        <span class="${changeClass}">${formatPct(change)}</span>
        <span class="${tone}">${formatSentimentScore(score, row.community_score != null ? 0 : 1, row.community_score != null ? "community" : "")}</span>
        <span>帖 ${Number(row.community_posts_today || 0)}</span>
        <span>析 ${Number(row.daily_analyzed_count || 0)}</span>
      </div>
      ${row.daily_conclusion ? `<p>${escapeHTML(row.daily_conclusion)}</p>` : ""}
      <div class="backtest-sentiment-meta">
        <span>K线 ${escapeHTML(row.kline_fetched_at || "暂无")}</span>
        <span>情绪 ${escapeHTML(row.latest_sentiment_at || "暂无")}</span>
      </div>
    </article>
  `;
}

function formatBacktestAmount(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "暂无";
  if (Math.abs(numeric) >= 100000000) return `${(numeric / 100000000).toFixed(1)}亿`;
  if (Math.abs(numeric) >= 10000) return `${(numeric / 10000).toFixed(1)}万`;
  return numeric.toFixed(0);
}

function drawBacktestCurve() {
  const canvas = document.querySelector("#backtestCurve");
  if (!canvas || !backtestPayload?.equity_curve?.length) return;
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  const points = backtestPayload.equity_curve;
  const values = points.flatMap((point) => [Number(point.value), Number(point.benchmark)]);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = Math.max(max - min, 1);
  const padX = 46;
  const padY = 34;
  const plotWidth = width - padX * 2;
  const plotHeight = height - padY * 2;
  const xFor = (index) => padX + (index / Math.max(points.length - 1, 1)) * plotWidth;
  const yFor = (value) => height - padY - ((value - min) / span) * plotHeight;

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#fbfcfd";
  ctx.fillRect(0, 0, width, height);
  ctx.strokeStyle = "#dbe2e7";
  ctx.lineWidth = 1;
  ctx.beginPath();
  [0, 0.5, 1].forEach((ratio) => {
    const y = padY + plotHeight * ratio;
    ctx.moveTo(padX, y);
    ctx.lineTo(width - padX, y);
  });
  ctx.stroke();
  drawBacktestLine(ctx, points, xFor, yFor, "value", "#16815f", 4);
  drawBacktestLine(ctx, points, xFor, yFor, "benchmark", "#2364aa", 3);
  ctx.fillStyle = "#172026";
  ctx.font = "900 20px system-ui";
  ctx.fillText("策略", padX, 26);
  ctx.fillStyle = "#2364aa";
  ctx.fillText("基准", padX + 68, 26);
}

function drawBacktestLine(ctx, points, xFor, yFor, key, color, width) {
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.beginPath();
  points.forEach((point, index) => {
    const x = xFor(index);
    const y = yFor(Number(point[key]));
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
}

function localBacktestPayload(config) {
  const universe = stocks
    .filter((stock) => config.market === "all" || stock.market === config.market)
    .sort((a, b) => b.score - a.score)
    .slice(0, Math.max(1, config.max_positions));
  const length = Math.max(...universe.map((stock) => stock.spark.length), 1);
  let value = config.initial_cash;
  let benchmark = config.initial_cash;
  let peak = value;
  const curve = [];
  const returns = [];
  for (let index = 0; index < length; index += 1) {
    if (index > 0) {
      const dayReturn = universe.reduce((sum, stock) => {
        const current = stock.spark[index] ?? stock.price;
        const previous = stock.spark[index - 1] ?? current;
        return sum + (current / previous - 1);
      }, 0) / Math.max(universe.length, 1);
      const benchmarkReturn = stocks.reduce((sum, stock) => {
        const current = stock.spark[index] ?? stock.price;
        const previous = stock.spark[index - 1] ?? current;
        return sum + (current / previous - 1);
      }, 0) / Math.max(stocks.length, 1);
      value *= 1 + dayReturn;
      benchmark *= 1 + benchmarkReturn;
      peak = Math.max(peak, value);
      returns.push(dayReturn);
    }
    curve.push({
      date: `D-${length - index - 1}`,
      value: roundMoney(value),
      benchmark: roundMoney(benchmark),
      drawdown: peak ? Number(((value / peak - 1) * 100).toFixed(2)) : 0
    });
  }
  const totalReturn = (value / config.initial_cash - 1) * 100;
  const benchmarkReturn = (benchmark / config.initial_cash - 1) * 100;
  const winRate = returns.length ? returns.filter((item) => item > 0).length / returns.length * 100 : 0;
  return {
    mode: "local-research-backtest",
    run_id: `local-${Date.now()}`,
    config,
    strategy: { label: strategyLabel(config.strategy), thesis: "本地 fallback 使用页面内股票曲线，只用于确认回测报告交互。" },
    summary: {
      total_return: Number(totalReturn.toFixed(2)),
      annualized_return: Number((totalReturn * 252 / Math.max(returns.length, 1)).toFixed(2)),
      benchmark_return: Number(benchmarkReturn.toFixed(2)),
      max_drawdown: Math.min(...curve.map((point) => point.drawdown)),
      volatility: 0,
      sharpe: 0,
      win_rate: Number(winRate.toFixed(2)),
      turnover_events: 0,
      trading_days: length
    },
    equity_curve: curve,
    rebalance_log: [{ date: config.start_date, reason: "本地 fallback 按综合评分选择样本。", holdings: universe.map((stock) => ({ symbol: stock.symbol, weight: 1 / Math.max(universe.length, 1) })) }],
    attribution: {
      leaders: universe.slice(0, 3).map((stock) => ({ symbol: stock.symbol, score: stock.score })),
      laggards: universe.slice(-3).map((stock) => ({ symbol: stock.symbol, score: stock.score })),
      annualized_excess_vs_benchmark: Number((totalReturn - benchmarkReturn).toFixed(2)),
      main_driver: strategyLabel(config.strategy)
    },
    research_notes: [
      "当前为本地 fallback 回测，不代表真实历史收益。",
      "正式版本必须使用复权行情、完整交易日历、真实调仓价、滑点和手续费。",
      "样本量太小，不能用当前结果判断策略有效性。"
    ]
  };
}

function strategyLabel(strategy) {
  if (strategy === "catalyst_rotation") return "催化轮动";
  if (strategy === "defensive_quality") return "防守质量";
  if (strategy === "low_rumor") return "低传闻高证据";
  return "质量 + 动量";
}

function roundMoney(value) {
  return Number(value.toFixed(2));
}

function stockCardMarketMetrics(stock) {
  const detail = stockDetailCache.get(stock.symbol);
  const summary = detail?.summary ?? {};
  const dailyBars = detail?.market_data?.periods?.daily?.bars ?? [];
  const latestBar = dailyBars.at(-1) ?? {};
  const amount = firstFiniteNumber(latestBar.amount, summary.amount, stock.metrics?.avgAmountCny);
  const turnover = firstFiniteNumber(latestBar.turnover_rate, summary.turnover_rate, stock.metrics?.turnoverRate);
  const pe = firstFiniteNumber(latestBar.pe_ttm, summary.pe_ttm, stock.metrics?.pe);
  const volume = firstFiniteNumber(latestBar.volume, summary.volume);
  return [
    ["成交量", volume === null ? "暂无" : formatShareVolume(volume)],
    ["成交额", amount === null ? "暂无" : formatLargeMoney(amount, stock.currency)],
    ["换手率", turnover === null ? "暂无" : formatDetailNumber(turnover, 2, "%")],
    ["PE", pe === null ? "暂无" : formatPeTtm(pe)]
  ];
}

function stockCardCommunitySummary(stock) {
  const detail = stockDetailCache.get(stock.symbol);
  const snapshot = detail?.information?.sentiment;
  const sourceCounts = snapshot?.source_counts ?? snapshot?.raw?.source_counts ?? {};
  const snapshotCount = firstFiniteNumber(sourceCounts.community);
  const discussionCount = Array.isArray(detail?.information?.discussions) ? detail.information.discussions.length : null;
  const key = snapshot ? sentimentPayloadKey(stock.symbol, sentimentWindowDays(snapshot)) : "";
  const payloadRows = key ? (sentimentPayloadCache.get(key)?.evidence?.community ?? []) : [];
  const payloadSources = communitySourceStatsFromRows(payloadRows);
  const sources = payloadSources.length ? payloadSources : communitySourceStatsFromSnapshot(snapshot);
  const sourceAggregate = aggregateCommunitySourceStats(sources);
  const aggregateCount = firstFiniteNumber(sourceAggregate.count);
  const commentCount = aggregateCount ?? snapshotCount ?? discussionCount;
  const communityScore = firstFiniteNumber(sourceAggregate.score, snapshot?.community_score);
  const tone = sentimentToneForType(communityScore, "", "community");
  return {
    score: formatSentimentScore(communityScore, 0, "community"),
    count: commentCount === null ? "暂无" : String(Math.max(0, Math.round(commentCount))),
    toneClass: tone === "cn-up" || tone === "cn-down" ? tone : ""
  };
}

function renderStockCard(stock) {
  const changeClass = stock.change >= 0 ? "up" : "down";
  const sign = stock.change >= 0 ? "+" : "";
  const marketMetrics = stockCardMarketMetrics(stock);
  const community = stockCardCommunitySummary(stock);
  return `
    <article class="stock-card ${stock.symbol === selectedSymbol ? "selected" : ""}" data-symbol="${stock.symbol}">
      <div class="card-head">
        <div>
          <p class="symbol">${stock.symbol}</p>
          <p class="company">${stock.name} · ${stock.marketLabel}</p>
        </div>
        <div class="card-actions">
          ${renderStockBadges(stock)}
        </div>
      </div>
      <div class="price-row">
        <span class="price">${formatPrice(stock)}</span>
        <strong class="change ${changeClass}">${sign}${stock.change.toFixed(1)}%</strong>
      </div>
      <canvas
        class="sparkline"
        width="440"
        height="128"
        data-stock-thumb="${escapeHTML(stock.symbol)}"
        data-thumb-market="${escapeHTML(stock.market)}"
        data-spark="${stock.spark.join(",")}"
      ></canvas>
      <div class="card-market-metrics">
        ${marketMetrics.map(([label, value]) => `
          <span>
            <em>${label}</em>
            <strong>${value}</strong>
          </span>
        `).join("")}
      </div>
      <div class="card-sentiment-line">
        <span>股吧情绪面</span>
        <strong class="card-community-total ${community.toneClass}">${community.score}/${community.count}</strong>
      </div>
      <button class="ghost-action" data-analyze="${stock.symbol}" type="button">查看分析</button>
    </article>
  `;
}

function renderFactor(stock, name, value) {
  const snapshot = name === "情绪" ? stockDetailCache.get(stock.symbol)?.information?.sentiment : null;
  const liveScore = sentimentFactorScore(snapshot);
  const displayValue = liveScore ?? value;
  return `
    <div class="factor-row">
      <span>${name}</span>
      <div class="bar"><span style="width: ${displayValue}%"></span></div>
      <strong>${displayValue}</strong>
    </div>
  `;
}

function drawAllSparklines() {
  const canvases = [...document.querySelectorAll(".active-panel .sparkline")]
    .filter((canvas) => canvas.getClientRects().length > 0);
  canvases.forEach((canvas) => {
    const detail = stockDetailCache.get(canvas.dataset.stockThumb);
    const bars = detail?.market_data?.periods?.daily?.bars ?? [];
    if (bars.length >= 2) {
      drawKlineThumbnail(canvas, bars);
    } else {
      const points = canvas.dataset.spark.split(",").map(Number);
      drawKlineThumbnail(canvas, sparkPointsToBars(points));
    }
  });
  queueStockCardDetailLoads(canvases);
}

function drawSparkline(canvas, points) {
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  const min = Math.min(...points);
  const max = Math.max(...points);
  const span = Math.max(max - min, 1);

  ctx.clearRect(0, 0, width, height);
  ctx.lineWidth = 4;
  ctx.strokeStyle = points.at(-1) >= points[0] ? "#16815f" : "#b43c43";
  ctx.beginPath();
  points.forEach((point, index) => {
    const x = (index / (points.length - 1)) * (width - 28) + 14;
    const y = height - 18 - ((point - min) / span) * (height - 36);
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  ctx.fillStyle = "rgba(35, 100, 170, 0.1)";
  ctx.lineTo(width - 14, height - 16);
  ctx.lineTo(14, height - 16);
  ctx.closePath();
  ctx.fill();
}

function sparkPointsToBars(points) {
  return points.filter(Number.isFinite).map((close, index, values) => {
    const open = index === 0 ? close : values[index - 1];
    const spread = Math.max(Math.abs(close - open), Math.max(Math.abs(close), 1) * 0.006);
    return {
      open,
      high: Math.max(open, close) + spread * 0.35,
      low: Math.min(open, close) - spread * 0.35,
      close,
      volume: 1 + index
    };
  });
}

function queueStockCardDetailLoads(canvases = [...document.querySelectorAll(".active-panel [data-stock-thumb]")]) {
  if (!apiState.connected) return;
  const symbols = new Map();
  canvases.forEach((canvas) => {
    const symbol = canvas.dataset.stockThumb;
    if (!symbol || symbols.has(symbol)) return;
    if (stockDetailCache.has(symbol) || stockDetailLoading.has(symbol) || stockDetailErrors.has(symbol)) return;
    if (stockCardDetailQueuedSymbols.has(symbol)) return;
    symbols.set(symbol, canvas.dataset.thumbMarket || "all");
  });
  [...symbols.entries()].slice(0, 8).forEach(([symbol, market]) => {
    stockCardDetailQueuedSymbols.add(symbol);
    stockCardDetailQueue.push({ symbol, market });
  });
  scheduleStockCardDetailPump();
}

function scheduleStockCardDetailPump() {
  if (stockCardDetailPumpQueued) return;
  stockCardDetailPumpQueued = true;
  requestIdleTask(() => {
    stockCardDetailPumpQueued = false;
    pumpStockCardDetailQueue();
  });
}

function pumpStockCardDetailQueue() {
  if (!apiState.connected) return;
  while (stockCardDetailActiveLoads < maxStockCardDetailLoads && stockCardDetailQueue.length) {
    const item = stockCardDetailQueue.shift();
    stockCardDetailQueuedSymbols.delete(item.symbol);
    if (stockDetailCache.has(item.symbol) || stockDetailLoading.has(item.symbol) || stockDetailErrors.has(item.symbol)) continue;
    stockCardDetailActiveLoads += 1;
    stockDetailLoading.add(item.symbol);
    void loadStockDetail(item.symbol, item.market).finally(() => {
      stockCardDetailActiveLoads = Math.max(0, stockCardDetailActiveLoads - 1);
      scheduleStockCardDetailPump();
    });
  }
}

function drawKlineThumbnail(canvas, bars) {
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  const visible = bars
    .filter((bar) => Number.isFinite(Number(bar.close)))
    .slice(-48)
    .map((bar) => ({
      open: Number.isFinite(Number(bar.open)) ? Number(bar.open) : Number(bar.close),
      high: Number.isFinite(Number(bar.high)) ? Number(bar.high) : Number(bar.close),
      low: Number.isFinite(Number(bar.low)) ? Number(bar.low) : Number(bar.close),
      close: Number(bar.close),
      volume: Number.isFinite(Number(bar.volume)) ? Number(bar.volume) : 0
    }));
  if (visible.length < 2) {
    drawSparkline(canvas, canvas.dataset.spark.split(",").map(Number));
    return;
  }

  const padX = 14;
  const priceTop = 12;
  const priceHeight = 78;
  const volumeTop = 98;
  const volumeHeight = 18;
  const plotWidth = width - padX * 2;
  const step = plotWidth / visible.length;
  const candleWidth = Math.max(2, Math.min(8, step * 0.58));
  const min = Math.min(...visible.map((bar) => bar.low));
  const max = Math.max(...visible.map((bar) => bar.high));
  const span = Math.max(max - min, 0.01);
  const maxVolume = Math.max(...visible.map((bar) => bar.volume), 1);
  const xFor = (index) => padX + step * index + step / 2;
  const yFor = (value) => priceTop + priceHeight - ((value - min) / span) * priceHeight;

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#fbfcfd";
  ctx.fillRect(0, 0, width, height);
  ctx.strokeStyle = "#edf1f4";
  ctx.lineWidth = 1;
  ctx.beginPath();
  [0, 0.5, 1].forEach((ratio) => {
    const y = priceTop + priceHeight * ratio;
    ctx.moveTo(padX, y);
    ctx.lineTo(width - padX, y);
  });
  ctx.stroke();

  visible.forEach((bar, index) => {
    const x = xFor(index);
    const up = bar.close >= bar.open;
    const color = up ? "#e23b22" : "#059447";
    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.lineWidth = 1.6;
    ctx.beginPath();
    ctx.moveTo(x, yFor(bar.high));
    ctx.lineTo(x, yFor(bar.low));
    ctx.stroke();
    const top = yFor(Math.max(bar.open, bar.close));
    const bottom = yFor(Math.min(bar.open, bar.close));
    ctx.fillRect(x - candleWidth / 2, top, candleWidth, Math.max(bottom - top, 2));

    const volumeHeightNow = (bar.volume / maxVolume) * volumeHeight;
    ctx.globalAlpha = 0.78;
    ctx.fillRect(x - candleWidth / 2, volumeTop + volumeHeight - volumeHeightNow, candleWidth, Math.max(volumeHeightNow, 1));
    ctx.globalAlpha = 1;
  });

  const ma5 = movingAverage(visible.map((bar) => bar.close), 5);
  drawIndicatorLine(ctx, ma5, xFor, yFor, "#1677d2", 2);
}

function selectedStock() {
  return stocks.find((item) => item.symbol === selectedSymbol);
}

function stockByQuery(query) {
  const raw = String(query ?? "").trim();
  const normalized = raw.toLowerCase();
  const upper = raw.toUpperCase();
  if (!raw) return null;
  return stocks.find((item) => (
    item.symbol.toUpperCase() === upper
    || item.name.toLowerCase() === normalized
    || item.name.toLowerCase().includes(normalized)
  ));
}

async function selectStock(symbol, shouldOpenDrawer = true) {
  const requestId = ++selectStockRequestId;
  const raw = String(symbol ?? "").trim();
  const normalized = raw.toUpperCase();
  let stock = stockByQuery(raw);

  if (shouldOpenDrawer) {
    openSingleDrawer();
    renderDrawerLoading(stock ? `${stock.symbol} · ${stock.name}` : (raw || "股票"));
  }

  if (!stock && raw && apiState.connected) {
    try {
      const params = new URLSearchParams({
        q: raw,
        market: activeMarket,
        account_id: apiState.accountId
      });
      const payload = await apiRequest(`/api/stocks/search?${params.toString()}`);
      const apiStocks = Array.isArray(payload.stocks) ? payload.stocks : [];
      mergeApiStocks(apiStocks);
      stock = apiStocks.length ? stockByQuery(apiStocks[0].symbol) : null;
      void loadSearchHistory();
    } catch (error) {
      apiState.lastError = `股票搜索失败：${error.message}`;
      updateBackendStatus(apiState.lastError);
    }
  }
  if (requestId !== selectStockRequestId) return;
  selectedSymbol = stock ? stock.symbol : normalized;
  scheduleStockListRefresh();
  if (!stock) {
    renderUnknown(normalized);
    return;
  }
  if (shouldOpenDrawer) {
    requestAnimationFrame(() => {
      if (requestId === selectStockRequestId && selectedSymbol === stock.symbol) renderDetails(stock);
    });
  } else {
    renderDetails(stock);
  }
}

function openSingleDrawer() {
  singleDrawer.hidden = false;
  document.body.classList.add("drawer-open");
}

function closeSingleDrawer() {
  singleDrawer.hidden = true;
  document.body.classList.remove("drawer-open");
  stopSentimentSnapshotPoll();
}

function renderDrawerLoading(label = "股票") {
  detailTitle.textContent = label;
  if (detailFavorite) detailFavorite.hidden = true;
  detailBody.innerHTML = `
    <section class="stock-detail-panel">
      <div class="stock-detail-empty">
        <strong>正在打开个股详情</strong>
        <span>优先展示页面，K 线和财务数据随后从 SQLite 补齐。</span>
      </div>
    </section>
  `;
  reflectionList.innerHTML = `<div class="empty-state compact">正在准备反思记录。</div>`;
  memoryList.innerHTML = `<div class="empty-state compact">正在读取分析记忆。</div>`;
  if (sentimentAside) {
    sentimentAside.innerHTML = `
      <div class="sentiment-panel sentiment-panel-side empty">
        <div class="stock-detail-empty">
          <strong>正在读取情绪面</strong>
          <span>等待个股详情返回后展示公告/财报、社区舆论和交易行为三类证据。</span>
        </div>
      </div>
    `;
  }
}

function renderDetails(stock) {
  const shouldLoadDetail = shouldLoadStockDetail(stock.symbol);
  if (shouldLoadDetail) {
    stockDetailLoading.add(stock.symbol);
    void loadStockDetail(stock.symbol, stock.market);
  }
  const detailPayload = stockDetailCache.get(stock.symbol);
  ensureSentimentPayloadForDetail(stock, detailPayload);
  detailTitle.textContent = `${stock.symbol} · ${stock.name}`;
  renderDrawerFavoriteButton(stock);
  detailBody.innerHTML = `
    ${renderStockDetailPanel(stock)}
    ${renderPositionPanel(stock)}
    <p class="thesis">${stock.thesis}</p>
    <div class="uncertainty-list">
      ${renderUncertainty(stock)}
    </div>
    <div class="factor-detail-grid">
      ${Object.entries(stock.factors).map(([name, value]) => renderFactorTile(stock, name, value, detailPayload)).join("")}
    </div>
    <div class="evidence-list">
      ${stock.evidence.map((item, index) => renderEvidence(item, index)).join("")}
    </div>
    <div class="supplement-box" id="supplementBox">
      <div class="section-title compact">
        <div>
          <p class="eyebrow">Supplement</p>
          <h3>补充证据</h3>
        </div>
      </div>
      <div class="supplement-grid">
        <textarea id="supplementText" rows="4" placeholder="粘贴你在其他平台找到的公告、新闻摘要、数据字段或链接"></textarea>
        <input id="supplementUrl" type="url" placeholder="https://..." />
        <button id="addEvidence" class="primary-action" type="button">加入分析</button>
      </div>
    </div>
  `;
  reflectionList.innerHTML = stock.reflection.map(renderReflection).join("");
  renderMemory(stock);
  renderSentimentAside(stock, detailPayload);
  scheduleSentimentSnapshotPoll(stock.symbol);
  scheduleStockDetailChartDraw();
}

function renderDrawerFavoriteButton(stock) {
  if (!detailFavorite) return;
  const favorite = favoriteSymbols.has(stock.symbol);
  detailFavorite.hidden = false;
  detailFavorite.dataset.drawerFavorite = stock.symbol;
  detailFavorite.className = `status-badge drawer-favorite-button ${favorite ? "active" : ""}`;
  detailFavorite.setAttribute("aria-label", `${favorite ? "取消关注" : "关注"} ${stock.symbol}`);
  detailFavorite.innerHTML = `
    <span class="badge-icon bookmark-icon"></span>
    <span>${favorite ? "已关注" : "关注"}</span>
  `;
}

function renderPositionPanel(stock) {
  const position = calculatePosition(stock.symbol);
  const hasPosition = position.quantity > 0;
  return `
    <section class="position-panel ${hasPosition ? "" : "empty-position"}">
      <div class="position-head">
        <div>
          <p class="eyebrow">My position</p>
          <h4>${hasPosition ? "已有持仓" : "未持仓"}</h4>
        </div>
        <div class="trade-tags">${renderTradeTags(stock.symbol, 6)}</div>
      </div>
      <div class="position-metrics">
        <div><span>数量</span><strong>${position.quantity}</strong></div>
        <div><span>成本</span><strong>${hasPosition ? formatMoney(position.avgCost, stock.currency) : "N/A"}</strong></div>
        <div><span>当前价</span><strong>${formatMoney(stock.price, stock.currency)}</strong></div>
        <div><span>盈利金额</span><strong class="${position.totalProfit >= 0 ? "profit" : "loss"}">${formatMoney(position.totalProfit, stock.currency)}</strong></div>
        <div><span>收益率</span><strong class="${position.returnRate >= 0 ? "profit" : "loss"}">${formatPct(position.returnRate)}</strong></div>
      </div>
    </section>
  `;
}

function shouldLoadStockDetail(symbol) {
  return apiState.connected
    && symbol
    && !stockDetailCache.has(symbol)
    && !stockDetailLoading.has(symbol)
    && !stockDetailErrors.has(symbol)
    && !stockDetailRefreshing.has(symbol);
}

async function loadStockDetail(symbol, market = "all") {
  try {
    const params = new URLSearchParams({
      market: market || "all",
      limit: "520"
    });
    const payload = await apiRequest(`/api/stocks/${encodeURIComponent(symbol)}/detail?${params.toString()}`);
    stockDetailCache.set(symbol, payload);
    stockDetailErrors.delete(symbol);
    if (!stockDetailPeriods.has(symbol)) {
      stockDetailPeriods.set(symbol, preferredStockDetailPeriod(payload));
    }
  } catch (error) {
    stockDetailErrors.set(symbol, error.message);
  } finally {
    stockDetailLoading.delete(symbol);
    scheduleSparklineDraw();
    const current = stockBySymbol(symbol);
    if (current && selectedSymbol === symbol && !singleDrawer.hidden) {
      renderDetails(current);
    }
    if (current) scheduleStockListRefresh();
  }
}

function preferredStockDetailPeriod(payload) {
  const periods = payload?.market_data?.periods ?? {};
  const available = stockDetailPeriodOptions.find((item) => (periods[item.id]?.bars ?? []).length);
  return available?.id ?? "daily";
}

function activeStockDetailPeriod(symbol, payload) {
  const requested = stockDetailPeriods.get(symbol);
  const periods = payload?.market_data?.periods ?? {};
  if (requested && (periods[requested]?.bars ?? []).length) return requested;
  const fallback = preferredStockDetailPeriod(payload);
  stockDetailPeriods.set(symbol, fallback);
  return fallback;
}

function renderStockRefreshBanner(stock, message) {
  const symbol = stock?.symbol ?? "";
  return `
    <div class="stock-refresh-banner" role="status" aria-live="polite">
      <div class="refresh-banner-head">
        <strong>正在刷新数据</strong>
        ${renderRefreshElapsed("stock", symbol)}
      </div>
      <span>${escapeHTML(message || "正在刷新行情、K线、季度财务、公司报告、公告和资讯源。")}</span>
      <div class="refresh-progress" aria-hidden="true"><span></span></div>
    </div>
  `;
}

function renderStockDetailPanel(stock) {
  const detail = stockDetailCache.get(stock.symbol);
  const loading = stockDetailLoading.has(stock.symbol);
  const error = stockDetailErrors.get(stock.symbol);
  const refreshing = stockDetailRefreshing.has(stock.symbol);
  const refreshError = stockDetailRefreshErrors.get(stock.symbol);
  const refreshStep = stockDetailRefreshSteps.get(stock.symbol);

  if (!apiState.connected) {
    return `
      <section class="stock-detail-panel empty">
        <div class="stock-detail-empty">
          <strong>数据库行情详情未连接</strong>
          <span>启动后端后，这里会从 SQLite 的 daily_bars 和 financial_metrics_history 拉取 K 线、成交额和季度财务。</span>
        </div>
      </section>
    `;
  }

  if (refreshing && !detail) {
    return `
      <section class="stock-detail-panel refresh-state">
        ${renderStockRefreshBanner(stock, refreshStep)}
      </section>
    `;
  }

  if (loading && !detail) {
    return `
      <section class="stock-detail-panel">
        <div class="stock-detail-empty">
          <strong>正在读取数据库 K 线</strong>
          <span>从 daily_bars 聚合日K、周K、月K、季K，并读取季度财务。</span>
        </div>
      </section>
    `;
  }

  if (error && !detail) {
    return `
      <section class="stock-detail-panel empty">
        <div class="stock-detail-empty warn">
          <strong>行情详情加载失败</strong>
          <span>${escapeHTML(error)}</span>
        </div>
      </section>
    `;
  }

  if (!detail) {
    return "";
  }

  const symbol = typeof detail.symbol === "object" && detail.symbol !== null ? detail.symbol : {};
  const summary = detail.summary ?? {};
  const isIndexQuote = isIndexLikeStock({ ...stock, ...symbol });
  const period = activeStockDetailPeriod(stock.symbol, detail);
  const periodPayload = detail.market_data?.periods?.[period] ?? {};
  const bars = periodPayload.bars ?? [];
  const technicalRange = estimateSupportResistance(bars, summary);
  const changePct = Number(summary.change_pct ?? 0);
  const changeClass = changePct >= 0 ? "cn-up" : "cn-down";
  const periodButtons = stockDetailPeriodOptions.map((item) => {
    const rows = detail.market_data?.periods?.[item.id]?.rows ?? 0;
    return `
      <button class="kline-period ${item.id === period ? "active" : ""}" data-detail-period="${item.id}" type="button" ${rows ? "" : "disabled"}>
        ${item.label}
      </button>
    `;
  }).join("");
  const latestBar = latestDisplayBar(bars, summary);
  const displayName = symbol.name ?? stock.name;
  const displaySymbol = symbol.symbol ?? stock.symbol;
  const adjustLabel = formatAdjustLabel(detail.market_data?.preferred_adjust);

  return `
    <section class="stock-detail-panel terminal-detail-panel">
      <div class="stock-terminal-head">
        <div class="stock-terminal-identity">
          <strong>${escapeHTML(displayName)}</strong>
          <span>${escapeHTML(formatStockCodeForTerminal(displaySymbol))}</span>
          ${renderTerminalLevels(technicalRange)}
        </div>
        <div class="stock-terminal-price ${changeClass}">
          <strong>${formatTerminalPrice(summary.price, summary.currency, isIndexQuote)}</strong>
          <span>${formatSignedNumber(summary.change, 2)} ${formatSignedNumber(summary.change_pct, 2, "%")}</span>
        </div>
        <div class="stock-terminal-controls">
          <div class="kline-periods terminal-periods">${periodButtons}</div>
          <button class="kline-adjust-select" type="button" disabled>${escapeHTML(adjustLabel)}</button>
        </div>
      </div>
      ${refreshError ? `<div class="stock-refresh-error">${escapeHTML(refreshError)}</div>` : ""}
      ${refreshing ? renderStockRefreshBanner(stock, refreshStep || "正在刷新行情、K线、财务、公告和资讯数据。") : ""}
      <div class="stock-terminal-source-row">
        <span>${escapeHTML(summary.latest_trade_date ?? latestBar.date ?? "暂无交易日")}</span>
        <span>${escapeHTML(symbol.exchange ?? stock.marketLabel ?? stock.market)} · ${escapeHTML(symbol.industry ?? "行业未分类")}</span>
        <span>${escapeHTML(detail.market_data?.latest_provider ?? "daily_bars")}</span>
        <button class="mini-action stock-refresh-action" data-refresh-source="detail" type="button" ${refreshing ? "disabled" : ""} aria-label="刷新当前股票数据">
          ${refreshing ? "刷新中" : "刷新"}
        </button>
      </div>
      <div class="stock-kline-block terminal-chart-block">
        ${bars.length ? `
          <canvas class="stock-kline-canvas terminal-kline-canvas" width="920" height="420" data-stock-kline="${escapeHTML(stock.symbol)}" data-period="${escapeHTML(period)}" aria-label="K线图"></canvas>
        ` : `
          <div class="stock-detail-empty">
            <strong>暂无 K 线数据</strong>
            <span>当前股票在 daily_bars 中没有可展示的行情行。</span>
          </div>
        `}
      </div>
      ${renderStockCommunitySourcePanel(stock, detail)}
      <div class="stock-quote-grid terminal-quote-grid">
        ${renderQuoteMetric("昨收", formatDetailNumber(summary.pre_close, 2))}
        ${renderQuoteMetric("成交额", formatLargeMoney(summary.amount, summary.currency))}
        ${renderQuoteMetric("换手", formatDetailNumber(summary.turnover_rate, 2, "%"))}
        ${renderQuoteMetric("PE(TTM)", formatPeTtm(summary.pe_ttm), Number.isFinite(Number(summary.pe_ttm)) && Number(summary.pe_ttm) <= 0 ? "loss" : "")}
        ${renderQuoteMetric("PB", formatPositiveDetailNumber(summary.pb, 2))}
        ${renderQuoteMetric("PS(TTM)", formatPositiveDetailNumber(summary.ps_ttm, 2))}
        ${renderQuoteMetric("52周最高", formatDetailNumber(summary.high_52w, 2))}
        ${renderQuoteMetric("52周最低", formatDetailNumber(summary.low_52w, 2))}
        ${renderQuoteMetric("总股本", formatShareVolume(summary.total_share))}
        ${renderQuoteMetric("总市值", formatLargeMoney(summary.market_cap, summary.currency))}
        ${renderQuoteMetric("流通值", formatLargeMoney(summary.float_market_cap, summary.currency))}
        ${renderQuoteMetric("财报期", summary.latest_financial_period ? escapeHTML(summary.latest_financial_period) : "暂无")}
      </div>
      <div class="stock-terminal-chart-meta">
        <span>${escapeHTML(periodPayload.label ?? "K线")}</span>
        <span>${bars.length} 条</span>
      </div>
      ${renderFinancialQuarterPanel(detail)}
      ${renderStockInformationPanel(stock, detail)}
    </section>
  `;
}

function renderStockCommunitySourcePanel(stock, detail) {
  const snapshot = detail?.information?.sentiment;
  if (!snapshot) return "";
  const key = sentimentPayloadKey(stock.symbol, sentimentWindowDays(snapshot));
  const loading = sentimentPayloadLoading.has(key);
  const error = sentimentPayloadErrors.get(key);
  const stats = communitySourceStatsForDetail(stock, detail);
  if (!stats.length && !loading && !error) return "";
  return `
    <div class="stock-community-source-panel">
      <div>
        <strong>社区来源</strong>
        <span>按数据源统计均分/条数</span>
      </div>
      ${stats.length
        ? renderCommunitySourceBreakdown(stats, { className: "stock-community-source-breakdown" })
        : `<div class="community-source-empty">${escapeHTML(loading ? "正在读取社区来源统计" : error || "暂无社区来源统计")}</div>`}
    </div>
  `;
}

function renderTerminalLevels(range) {
  return `
    <div class="stock-terminal-levels">
      <span class="support">支撑位: ${formatTechnicalLevel(range.support)}</span>
      <span class="resistance">压力位: ${formatTechnicalLevel(range.resistance)}</span>
    </div>
  `;
}

function estimateSupportResistance(bars, summary = {}) {
  const numericBars = (bars || [])
    .map((bar) => ({
      high: Number(bar.high),
      low: Number(bar.low),
      close: Number(bar.close),
      volume: Number.isFinite(Number(bar.volume)) ? Number(bar.volume) : 0
    }))
    .filter((bar) => Number.isFinite(bar.high) && Number.isFinite(bar.low) && Number.isFinite(bar.close));
  const recent = numericBars.slice(-120);
  const summaryLow = Number(summary.low_52w ?? summary.low);
  const summaryHigh = Number(summary.high_52w ?? summary.high);
  const latest = recent.at(-1);
  const previous = recent.at(-2) ?? latest;
  const current = Number.isFinite(Number(summary.price)) ? Number(summary.price) : Number(latest?.close);
  if (!recent.length || !Number.isFinite(current)) {
    return {
      support: Number.isFinite(summaryLow) ? summaryLow : null,
      resistance: Number.isFinite(summaryHigh) ? summaryHigh : null
    };
  }

  const tolerance = supportResistanceTolerance(recent, current);
  const candidates = [];
  const addCandidate = (level, type, kind, bonus = 0) => {
    const numeric = Number(level);
    if (!Number.isFinite(numeric) || numeric <= 0) return;
    if (type === "support" && numeric > current + tolerance) return;
    if (type === "resistance" && numeric < current - tolerance) return;
    candidates.push({ level: numeric, type, kind, bonus });
  };

  for (let index = 2; index < recent.length - 2; index += 1) {
    const slice = recent.slice(index - 2, index + 3);
    const bar = recent[index];
    if (bar.low === Math.min(...slice.map((item) => item.low))) {
      addCandidate(bar.low, "support", "swing", 2.4);
    }
    if (bar.high === Math.max(...slice.map((item) => item.high))) {
      addCandidate(bar.high, "resistance", "swing", 2.4);
    }
  }

  if (previous) {
    const pivot = (previous.high + previous.low + previous.close) / 3;
    addCandidate((pivot * 2) - previous.high, "support", "pivot-s1", 2.1);
    addCandidate(pivot - (previous.high - previous.low), "support", "pivot-s2", 1.3);
    addCandidate((pivot * 2) - previous.low, "resistance", "pivot-r1", 2.1);
    addCandidate(pivot + (previous.high - previous.low), "resistance", "pivot-r2", 1.3);
  }

  [5, 10, 20, 30, 60].forEach((windowSize) => {
    const value = movingAverage(recent.map((bar) => bar.close), windowSize).at(-1);
    if (!Number.isFinite(Number(value))) return;
    addCandidate(value, Number(value) <= current ? "support" : "resistance", `ma${windowSize}`, 1.5);
  });

  addCandidate(Math.min(...recent.slice(-60).map((bar) => bar.low)), "support", "range-low", 0.4);
  addCandidate(Math.max(...recent.slice(-60).map((bar) => bar.high)), "resistance", "range-high", 0.4);
  addCandidate(summaryLow, "support", "summary-low", 0.2);
  addCandidate(summaryHigh, "resistance", "summary-high", 0.2);

  return {
    support: pickSupportResistanceLevel(candidates, recent, current, tolerance, "support")
      ?? (Number.isFinite(summaryLow) ? summaryLow : Math.min(...recent.map((bar) => bar.low))),
    resistance: pickSupportResistanceLevel(candidates, recent, current, tolerance, "resistance")
      ?? (Number.isFinite(summaryHigh) ? summaryHigh : Math.max(...recent.map((bar) => bar.high)))
  };
}

function supportResistanceTolerance(bars, current) {
  const ranges = bars.slice(-20).map((bar) => Math.max(bar.high - bar.low, 0)).filter(Number.isFinite);
  const avgRange = ranges.length ? ranges.reduce((sum, value) => sum + value, 0) / ranges.length : current * 0.02;
  return Math.max(current * 0.006, avgRange * 0.28, 0.01);
}

function pickSupportResistanceLevel(candidates, bars, current, tolerance, type) {
  const sideCandidates = candidates.filter((item) => item.type === type);
  if (!sideCandidates.length) return null;
  const averageVolume = Math.max(
    bars.reduce((sum, bar) => sum + Number(bar.volume || 0), 0) / Math.max(bars.length, 1),
    1
  );
  const scored = sideCandidates.map((item) => {
    const reactionBars = bars
      .map((bar, index) => ({ bar, index }))
      .filter(({ bar }) => {
        const anchor = type === "support" ? Math.min(bar.low, bar.close) : Math.max(bar.high, bar.close);
        return Math.abs(anchor - item.level) <= tolerance;
      });
    const touches = reactionBars.length;
    const recentTouch = reactionBars.at(-1);
    const volumeBoost = reactionBars.length
      ? reactionBars.reduce((sum, entry) => sum + Number(entry.bar.volume || 0), 0) / reactionBars.length / averageVolume
      : 0;
    const recencyBoost = recentTouch ? recentTouch.index / Math.max(bars.length - 1, 1) : 0;
    const distancePct = Math.abs(item.level - current) / Math.max(Math.abs(current), 0.01);
    const nearCurrentBoost = Math.max(0, 2.2 - distancePct * 14);
    const score = item.bonus + touches * 1.8 + Math.min(volumeBoost, 2.4) + recencyBoost + nearCurrentBoost;
    return { ...item, score, touches, distancePct };
  });
  scored.sort((a, b) => b.score - a.score || a.distancePct - b.distancePct);
  return scored[0]?.level ?? null;
}

function latestDisplayBar(bars, summary = {}) {
  const latest = bars.at(-1) ?? {};
  return {
    ...latest,
    date: latest.date ?? summary.latest_trade_date,
    open: latest.open ?? summary.open,
    high: latest.high ?? summary.high,
    low: latest.low ?? summary.low,
    close: latest.close ?? summary.price
  };
}

function formatStockCodeForTerminal(symbol) {
  const text = String(symbol || "");
  return text.includes(".") ? text.split(".")[0] : text;
}

function formatTechnicalLevel(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric.toFixed(3) : "暂无";
}

function formatAdjustLabel(value) {
  const text = String(value || "").toLowerCase();
  if (["qfq", "forward", "front", "前复权"].includes(text)) return "前复权";
  if (["hfq", "backward", "后复权"].includes(text)) return "后复权";
  if (["none", "raw", "不复权", "未复权"].includes(text)) return "不复权";
  return value ? String(value) : "前复权";
}

function formatTerminalPrice(value, currency = "CNY", isIndex = false) {
  if (value === null || value === undefined || value === "") return "暂无";
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "暂无";
  if (isIndex || currency === "CNY") return numeric.toFixed(2);
  return formatMoney(numeric, currency);
}

function renderQuoteMetric(label, value, valueClass = "") {
  return `
    <div class="quote-metric">
      <span>${escapeHTML(label)}</span>
      <strong class="${valueClass}">${value}</strong>
    </div>
  `;
}

function renderSentimentAside(stock, detail) {
  if (!sentimentAside) return;
  sentimentAside.innerHTML = renderSentimentPanel(detail, {
    stock,
    interactive: true,
    surface: "side"
  });
}

function renderSentimentRefreshBanner(stock) {
  const symbol = stock?.symbol ?? "";
  return `
    <div class="sentiment-refresh-banner" role="status" aria-live="polite">
      <div class="refresh-banner-head">
        <strong>正在刷新情绪</strong>
        ${renderRefreshElapsed("sentiment", symbol)}
      </div>
      <span>启动社区爬虫，并重新分析社区舆论和交易行为（公告/财报不在本轮 LLM 分析）。</span>
      <div class="refresh-progress" aria-hidden="true"><span></span></div>
    </div>
  `;
}

function renderSentimentPanel(detail, options = {}) {
  const snapshot = detail?.information?.sentiment;
  const stock = options.stock ?? selectedStock();
  const interactive = Boolean(options.interactive);
  const sideClass = options.surface === "side" ? "sentiment-panel-side" : "";
  const refreshing = stock ? sentimentRefreshing.has(stock.symbol) : false;
  const refreshError = stock ? sentimentRefreshErrors.get(stock.symbol) : "";
  const refreshResult = stock ? sentimentRefreshResults.get(stock.symbol) : null;
  if (!snapshot) {
    return `
      <div class="sentiment-panel ${sideClass} empty">
        <div class="stock-detail-empty">
          <strong>暂无情绪快照</strong>
          <span>当前股票还没有写入 sentiment_snapshots。关注列表里的股票会在每天 8:00–24:00 期间每 30 分钟自动刷新；也可以手动启动 GLM 情绪分析。</span>
          ${interactive && stock && apiState.connected ? `
            <button class="mini-action sentiment-refresh-action" data-sentiment-refresh="llm" type="button" ${refreshing ? "disabled" : ""}>
              ${refreshing ? "刷新中" : "刷新"}
            </button>
          ` : ""}
        </div>
        ${refreshing ? renderSentimentRefreshBanner(stock) : ""}
        ${refreshError ? `<div class="stock-refresh-error">${escapeHTML(refreshError)}</div>` : ""}
        ${refreshResult ? renderSentimentRefreshResult(refreshResult) : ""}
      </div>
    `;
  }
  const composite = Number(snapshot.composite_score);
  const tone = sentimentTone(composite, snapshot.sentiment_label);
  const factorScore = sentimentFactorScore(snapshot);
  const counts = snapshot.source_counts ?? {};
  const sourceTotal = sentimentSourceCount(snapshot);
  const expandedType = stock ? sentimentExpandedTypes.get(stock.symbol) : "";
  return `
    <div class="sentiment-panel ${sideClass}">
      <div class="sentiment-head">
        <div>
          <strong>情绪面</strong>
          <span>${escapeHTML(snapshot.as_of || "暂无日期")} · ${snapshot.window_days || 30} 天窗口 · ${sourceTotal} 条证据</span>
        </div>
        <div class="sentiment-head-actions">
          <span class="sentiment-label ${tone}">${sentimentLabelText(snapshot.sentiment_label)}</span>
          ${interactive ? `
            <button class="mini-action sentiment-refresh-action" data-sentiment-refresh="llm" type="button" ${refreshing ? "disabled" : ""}>
              ${refreshing ? "刷新中" : "刷新"}
            </button>
          ` : ""}
        </div>
      </div>
      ${renderSentimentSnapshotStatus(snapshot, refreshResult)}
      ${refreshing ? renderSentimentRefreshBanner(stock) : ""}
      ${refreshError ? `<div class="stock-refresh-error">${escapeHTML(refreshError)}</div>` : ""}
      ${refreshResult ? renderSentimentRefreshResult(refreshResult) : ""}
      <div class="sentiment-summary-grid">
        <div class="sentiment-score-card ${tone}">
          <span>综合情绪</span>
          <strong>${formatSentimentScore(composite)}</strong>
          <em>因子换算 ${factorScore ?? "暂无"}</em>
        </div>
        <div class="sentiment-score-card">
          <span>置信度</span>
          <strong>${formatSentimentConfidence(snapshot.confidence)}</strong>
          <em>证据充分度</em>
        </div>
      </div>
      <div class="sentiment-breakdown">
        ${sentimentTypeOptions.map((item) => {
          const active = expandedType === item.id;
          return `
            ${renderSentimentBreakdownRow(item, snapshot[item.scoreKey], counts[item.id] || 0, { interactive, active })}
            ${active ? renderSentimentEvidencePanel(stock, detail, item.id) : ""}
          `;
        }).join("")}
      </div>
      ${renderSentimentMethodCard(snapshot)}
    </div>
  `;
}

function renderSentimentBreakdownRow(item, value, count, options = {}) {
  const tone = sentimentToneForType(value, "", item.id);
  const normalized = sentimentTrackPercent(value, item.id);
  const activeClass = options.active ? "active" : "";
  const tag = options.interactive ? "button" : "div";
  const attrs = options.interactive
    ? `type="button" data-sentiment-type="${escapeHTML(item.id)}" aria-expanded="${options.active ? "true" : "false"}"`
    : "";
  return `
    <${tag} class="sentiment-breakdown-row ${tone} ${activeClass}" ${attrs}>
      <div class="sentiment-breakdown-meta">
        <span>${escapeHTML(item.label)}</span>
        <strong>${formatSentimentScore(value, 1, item.id)}</strong>
        <em>${Number(count || 0)} 条${options.interactive ? (options.active ? " · 收起" : " · 展开") : ""}</em>
      </div>
      <div class="sentiment-track" aria-hidden="true">
        <span style="width: ${normalized.toFixed(1)}%"></span>
      </div>
    </${tag}>
  `;
}

function renderSentimentMethodCard(snapshot) {
  const available = sentimentAvailableTypes(snapshot);
  const weightText = sentimentTypeOptions
    .map((item) => `${item.label} ${(item.weight * 100).toFixed(0)}%`)
    .join(" · ");
  const activeText = available.length
    ? available.map((item) => `${item.label} ${(Number(sentimentEffectiveWeight(snapshot, item.id)) * 100).toFixed(0)}%`).join(" · ")
    : "暂无有效证据";
  return `
    <div class="sentiment-method-card">
      <strong>计算口径</strong>
      <p>公告/交易按置信度与时间衰减加权；社区只统计今天评论，LLM 返回 sentiment_score（-100～100）与 sentiment_class（正面/偏正面/中性/偏负面/负面），均分取算术平均。</p>
      <p>基础权重：${escapeHTML(weightText)}。本次有效权重：${escapeHTML(activeText)}。</p>
      <p>标签阈值：≥35 积极，12 到 35 偏积极，-12 到 12 中性，-35 到 -12 偏消极，≤-35 消极。</p>
    </div>
  `;
}

function renderSentimentRefreshResult(result) {
  const counts = result?.counts ?? {};
  const errors = Array.isArray(result?.errors) ? result.errors : [];
  const performance = result?.performance ?? {};
  const usage = result?.usage ?? {};
  const llm = performance.llm ?? {};
  const inventory = usage.inventory ?? {};
  const communityInv = inventory.community ?? {};
  const filingInv = inventory.filing_news ?? {};
  const slowest = [...(performance.steps ?? [])].sort((a, b) => Number(b.duration_ms || 0) - Number(a.duration_ms || 0))[0];
  const llmLabel = llm.provider === "glm" ? "GLM" : displayText(llm.provider || "LLM");
  const crawled = Number(counts.community_posts_crawled ?? counts.community_posts ?? 0);
  const todayAnalyzed = Number(counts.community_posts_today ?? counts.community_evidence ?? 0);
  const llmItems = Number(usage.totals?.items ?? llm.items ?? 0);
  const llmRequests = Number(usage.llm_requests ?? llm.requests ?? 0);
  const llmDuration = Number(usage.duration_ms ?? llm.duration_ms ?? 0);
  const cacheHits = Number(usage.totals?.cache_hits ?? usage.cache_hits ?? llm.cache_hits ?? 0);
  const llmBreakdown = [
    Number(communityInv.total) ? `社区 ${Number(communityInv.total)}` : "",
    Number(filingInv.total) ? `公告 ${Number(filingInv.total)}` : "",
    Number(usage.daily_conclusion_requests) ? `日汇总 ${Number(usage.daily_conclusion_requests)}` : "",
  ].filter(Boolean).join(" · ");
  return `
    <div class="sentiment-refresh-result">
      <span>已刷新 ${Number(counts.symbols || 0)} 只</span>
      ${crawled ? `<span title="本次从股吧/雪球拉取并写入库的评论数，含多日历史帖">抓取入库 ${crawled}</span>` : ""}
      <span title="按社区分析日过滤后参与评分的今日评论数">今日分析 ${todayAnalyzed}</span>
      ${Number(counts.filing_news_evidence || 0) ? `<span>公告/财报 ${Number(counts.filing_news_evidence || 0)}</span>` : ""}
      <span>交易 ${Number(counts.market_evidence || 0)}</span>
      ${llm.configured || usage.configured ? `<span title="条数为各渠道待评条目合计（含缓存命中）；批数为 HTTP 请求次数">${escapeHTML(llmLabel)} ${llmItems} 条 / ${llmRequests} 批${llmBreakdown ? `（${escapeHTML(llmBreakdown)}）` : ""} · ${formatSentimentDuration(llmDuration)}</span>` : `<span>GLM 未配置</span>`}
      ${cacheHits ? `<span>缓存 ${cacheHits} 条</span>` : ""}
      ${slowest ? `<span>最慢 ${escapeHTML(displayText(slowest.step))} ${formatSentimentDuration(slowest.duration_ms)}</span>` : ""}
      ${errors.length ? `<strong>${errors.length} 个提示</strong>` : ""}
    </div>
  `;
}

function formatSentimentDuration(value) {
  const ms = Number(value || 0);
  if (!Number.isFinite(ms) || ms <= 0) return "0秒";
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(ms < 10000 ? 1 : 0)}秒`;
}

function parseLocalDateTime(value) {
  const text = String(value || "").trim();
  if (!text) return null;
  const normalized = text.includes("T") ? text : text.replace(" ", "T");
  const parsed = new Date(normalized);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function formatSentimentSnapshotTime(value) {
  const parsed = parseLocalDateTime(value);
  if (!parsed) return "暂无刷新时间";
  return parsed.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false
  }).replace(/\//g, "-");
}

function formatSentimentSnapshotAge(value) {
  const parsed = parseLocalDateTime(value);
  if (!parsed) return "";
  const minutes = Math.max(0, Math.round((Date.now() - parsed.getTime()) / 60000));
  if (minutes < 1) return "刚刚";
  if (minutes < 60) return `约 ${minutes} 分钟前`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  if (hours < 24) return rest ? `约 ${hours}小时${rest}分钟前` : `约 ${hours}小时前`;
  const days = Math.floor(hours / 24);
  return `约 ${days} 天前`;
}

function renderSentimentSnapshotStatus(snapshot, refreshResult) {
  const generatedAt = snapshot?.generated_at || refreshResult?.refreshed_at || "";
  const age = formatSentimentSnapshotAge(generatedAt);
  return `
    <div class="sentiment-snapshot-status">
      <span>上次刷新 <strong>${escapeHTML(formatSentimentSnapshotTime(generatedAt))}</strong></span>
      ${age ? `<span>${escapeHTML(age)}</span>` : ""}
      <span>关注列表股票在每天 8:00–24:00 期间每 30 分钟自动刷新</span>
    </div>
  `;
}

function renderSentimentEvidencePanel(stock, detail, type) {
  const snapshot = detail?.information?.sentiment;
  if (!stock || !snapshot) {
    return `<div class="sentiment-evidence-panel"><div class="stock-detail-empty"><strong>缺少情绪快照</strong><span>需要先刷新当前股票详情。</span></div></div>`;
  }
  const meta = sentimentMeta(type);
  const windowDays = sentimentWindowDays(snapshot);
  const key = sentimentPayloadKey(stock.symbol, windowDays);
  const payload = sentimentPayloadCache.get(key);
  const loading = sentimentPayloadLoading.has(key);
  const error = sentimentPayloadErrors.get(key);
  const typeScore = sentimentTypeScore(snapshot, type);
  const typeStats = snapshot.raw?.type_scores?.[type] ?? {};
  const effectiveWeight = sentimentEffectiveWeight(snapshot, type);

  if (loading && !payload) {
    return `
      <div class="sentiment-evidence-panel">
        <div class="stock-detail-empty">
          <strong>正在读取${escapeHTML(meta.label)}证据</strong>
          <span>从 sentiment_evidence 拉取原文片段、关键词和单条计算因子。</span>
        </div>
      </div>
    `;
  }
  if (error && !payload) {
    return `
      <div class="sentiment-evidence-panel">
        <div class="stock-detail-empty warn">
          <strong>${escapeHTML(meta.label)}证据读取失败</strong>
          <span>${escapeHTML(error)}</span>
        </div>
      </div>
    `;
  }

  const evidenceRows = payload?.evidence?.[type] ?? [];
  const activeCommunityClass = type === "community" && stock ? (communityClassFilters.get(stock.symbol) || "") : "";
  const filteredRows = activeCommunityClass
    ? evidenceRows.filter((item) => communityClassFromItem(item) === activeCommunityClass)
    : evidenceRows;
  const shownRows = filteredRows.slice(0, type === "community" ? 12 : 8);
  return `
    <div class="sentiment-evidence-panel">
      ${type === "community"
        ? renderCommunitySentimentStrip(typeScore, typeStats, evidenceRows, activeCommunityClass)
        : `
          <div class="sentiment-factor-strip">
            <span>本类分 <strong>${formatSentimentScore(typeScore)}</strong></span>
            <span>本类置信 <strong>${formatSentimentConfidence(typeStats.confidence)}</strong></span>
            <span>基础权重 <strong>${(meta.weight * 100).toFixed(0)}%</strong></span>
            <span>有效权重 <strong>${effectiveWeight === null ? "暂无" : formatDetailNumber(effectiveWeight * 100, 0, "%")}</strong></span>
          </div>
        `}
      <div class="sentiment-source-note">${escapeHTML(meta.sourceNote)}</div>
      ${shownRows.length ? shownRows.map((item, index) => renderSentimentEvidenceCard(item, index, windowDays)).join("") : `
        <div class="stock-detail-empty">
          <strong>${activeCommunityClass ? `暂无${escapeHTML(communityClassLabel(activeCommunityClass))}评论` : "暂无可展开证据"}</strong>
          <span>${activeCommunityClass ? "当前明细接口没有返回这个分类的评论，点「明细」可恢复全部评论。" : "快照里有本类计数，但明细接口没返回评论列表。常见原因是刚升级评分版本尚未重刷；点上方「刷新」即可，或硬刷新页面后再展开。"}</span>
        </div>
      `}
    </div>
  `;
}

function renderCommunitySentimentStrip(typeScore, typeStats, rows, activeClass = "") {
  const counts = normalizedCommunityClassCounts(typeStats, rows);
  const sourceStats = communitySourceStatsFromRows(rows);
  const total = communityClassOrder.reduce((sum, item) => sum + Number(counts[item] || 0), 0);
  const allShownCount = Math.min(rows.length, 12);
  const allTotal = total || rows.length;
  const evidenceDay = latestSentimentEvidenceDay(rows);
  const staleNote = evidenceDay && evidenceDay !== localDateKey()
    ? `<span class="community-stale-note">今日无新帖，展示 ${escapeHTML(evidenceDay)}</span>`
    : "";
  const scoreLabel = staleNote ? "展示日均分" : "今日均分";
  return `
    <div class="sentiment-factor-strip community-summary">
      <span>${scoreLabel} <strong>${formatSentimentScore(typeScore, 0, "community")}</strong></span>
      ${staleNote}
      ${communityClassOrder.map((item) => {
        const active = activeClass === item;
        return `
          <button class="community-class-filter ${active ? "active" : ""}" data-community-class="${escapeHTML(item)}" type="button" aria-pressed="${active ? "true" : "false"}">
            ${escapeHTML(communityClassLabel(item))} <strong>${Number(counts[item] || 0)}</strong>
          </button>
        `;
      }).join("")}
      <button class="community-class-filter ${activeClass ? "" : "active"}" data-community-class="" type="button" aria-pressed="${activeClass ? "false" : "true"}" title="界面最多展示前 12 条明细，完整条数见上方">
        明细 <strong>${allShownCount}/${allTotal}</strong>
      </button>
    </div>
    ${renderCommunitySourceBreakdown(sourceStats, { className: "sentiment-community-sources", emptyText: rows.length ? "暂无来源拆分" : "" })}
  `;
}

function localDateKey(value = new Date()) {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function sentimentEvidenceDayKey(item) {
  const text = String(item?.event_date || item?.analyzed_at || "").trim();
  const match = text.match(/^\d{4}-\d{2}-\d{2}/);
  return match ? match[0] : "";
}

function latestSentimentEvidenceDay(rows = []) {
  return rows
    .map(sentimentEvidenceDayKey)
    .filter(Boolean)
    .sort()
    .at(-1) || "";
}

function renderSentimentEvidenceCard(item, index, windowDays) {
  const terms = uniqueSentimentTerms(item);
  const isCommunity = item.sentiment_type === "community";
  const sourceText = displayText((isCommunity ? item.source_text : "") || item.title || item.evidence?.text || item.category || "暂无原文片段");
  const communitySourceStatus = communityEvidenceSourceStatus(item);
  const failed = isSentimentLlmFailure(item);
  const recency = sentimentRecencyWeight(item.event_date || item.analyzed_at, windowDays);
  const itemWeight = failed ? 0 : sentimentEvidenceWeight(item, windowDays);
  const contribution = failed ? null : sentimentEvidenceContribution(item, windowDays);
  const communityClass = isCommunity && !failed ? communityClassFromItem(item) : "";
  const scoreTone = failed ? "warning" : sentimentToneForType(item.sentiment_score, item.sentiment_label, item.sentiment_type);
  return `
    <article class="sentiment-evidence-card${failed ? " failed" : ""}">
      <div class="sentiment-evidence-top">
        <span>#${index + 1} · ${escapeHTML(displayText(item.source))}</span>
        <div class="sentiment-evidence-score ${scoreTone}">
          ${communityClass ? `<span>${escapeHTML(communityClass)}</span>` : ""}
          <strong>${failed ? "GLM失败" : formatSentimentScore(item.sentiment_score, 0, isCommunity ? "community" : "")}</strong>
        </div>
      </div>
      <p class="sentiment-quote">${renderHighlightedSentimentText(sourceText, terms, scoreTone)}</p>
      ${terms.length && !isCommunity ? `<div class="sentiment-keywords">${terms.map((term) => `<mark class="${scoreTone}">${escapeHTML(term)}</mark>`).join("")}</div>` : ""}
      ${isCommunity ? "" : `
        <div class="sentiment-evidence-factors">
          <span>置信度 ${formatSentimentConfidence(item.confidence)}</span>
          <span>时间权重 ${recency.toFixed(2)}</span>
          <span>证据权重 ${itemWeight.toFixed(2)}</span>
          <span>加权贡献 ${failed ? "未计入" : (contribution === null ? "暂无" : formatSentimentScore(contribution, 0, isCommunity ? "community" : ""))}</span>
        </div>
      `}
      ${failed ? `<div class="sentiment-failure-note">GLM分析失败，仅保留排查信息，不计入情绪分。</div>` : ""}
      ${isCommunity ? "" : renderSentimentStructuredEvidence(item.evidence, item)}
      <div class="sentiment-evidence-meta">
        <span>${escapeHTML(item.event_date || item.analyzed_at || "暂无日期")}</span>
        <span>${escapeHTML(item.model_provider || "local")} / ${escapeHTML(item.model_name || "fallback-v1")}</span>
        ${communitySourceStatus.badge ? `<span class="${escapeHTML(communitySourceStatus.className)}">${escapeHTML(communitySourceStatus.badge)}</span>` : ""}
        ${item.url ? `<a class="${escapeHTML(communitySourceStatus.linkClass)}" href="${escapeHTML(item.url)}" target="_blank" rel="noreferrer" title="${escapeHTML(communitySourceStatus.title)}">${escapeHTML(communitySourceStatus.linkLabel)}</a>` : ""}
      </div>
    </article>
  `;
}

function communityEvidenceSourceStatus(item) {
  if (item?.sentiment_type !== "community") {
    return {
      badge: "",
      className: "",
      linkClass: "",
      linkLabel: "原文",
      title: "打开原文"
    };
  }
  const source = String(item.source || "").toLowerCase();
  const hasVerifiedContent = item.source_content_available === true || item.source_text_kind === "detail_text";
  if (hasVerifiedContent) {
    return {
      badge: "已抓取正文",
      className: "sentiment-source-verified",
      linkClass: "",
      linkLabel: "原文",
      title: "已抓取到正文，打开原帖"
    };
  }
  return {
    badge: "列表标题",
    className: "sentiment-source-warning",
    linkClass: "sentiment-link-unverified",
    linkLabel: "来源链接",
    title: "当前证据没有抓取到正文，仅使用列表标题"
  };
}

function isSentimentLlmFailure(item) {
  const evidence = item?.evidence ?? {};
  const modelProvider = String(item?.model_provider || "");
  const hasStructuredScore = evidence.structured_financial_score !== null && evidence.structured_financial_score !== undefined;
  if (hasStructuredScore) return false;
  return Boolean(evidence.llm_error) || (modelProvider === "local" && evidence.fallback_reason);
}

function renderSentimentStructuredEvidence(evidence = {}, item = {}) {
  const hiddenCommunityFields = new Set(["text_length", "prompt_version", "llm_id", "llm_reason"]);
  const entries = Object.entries(evidence || {})
    .filter(([key, value]) => {
      if (key === "rule_matches" || value === null || value === undefined || value === "") return false;
      if (item?.sentiment_type === "community" && hiddenCommunityFields.has(key)) return false;
      return true;
    })
    .slice(0, 12);
  if (!entries.length) return "";
  return `
    <div class="sentiment-rule-list structured">
      <strong>结构化因子</strong>
      ${entries.map(([key, value]) => `<span>${escapeHTML(displayColumnLabel(key))} <em>${escapeHTML(formatSentimentEvidenceValue(key, value))}</em></span>`).join("")}
    </div>
  `;
}

function formatSentimentEvidenceValue(key, value) {
  const normalized = normalizeFieldKey(key);
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return displayCellValue(value);
  if (["change_1d", "change_5d", "change_20d", "max_drawdown", "turnover_rate", "roe", "gross_margin", "net_margin", "debt_ratio", "revenue_growth"].includes(normalized)) {
    return `${numeric.toFixed(2)}%`;
  }
  if (["amount_ratio_20d", "volume_ratio_20d"].includes(normalized)) {
    return `${numeric.toFixed(2)}x`;
  }
  if (["bar_count", "limit_up_days", "limit_down_days", "text_length"].includes(normalized)) {
    return String(Math.round(numeric));
  }
  return numeric.toFixed(Math.abs(numeric) >= 100 ? 0 : 2);
}

function renderFinancialQuarterPanel(detail) {
  const quarters = detail.financials?.quarters ?? [];
  if (!quarters.length) {
    return `
      <div class="financial-quarter-panel empty">
        <div class="stock-detail-empty">
          <strong>暂无季度财务</strong>
          <span>financial_metrics_history 中还没有这只股票的可用季度指标。</span>
        </div>
      </div>
    `;
  }
  return `
    <div class="financial-quarter-panel">
      <div class="financial-quarter-head">
        <strong>季度财务</strong>
        <span>${escapeHTML(quarters[0].provider ?? "financial_metrics_history")} · ${quarters.length} 期</span>
      </div>
      <div class="financial-quarter-table-wrap">
        <table class="financial-quarter-table">
          <thead>
            <tr>
              <th>报告期</th>
              <th>ROE</th>
              <th>毛利率</th>
              <th>净利率</th>
              <th>负债率</th>
              <th>净利润</th>
              <th>EPS(TTM)</th>
            </tr>
          </thead>
          <tbody>
            ${quarters.slice(0, 8).map((item) => `
              <tr>
                <td>${escapeHTML(item.period ?? item.report_period ?? "")}</td>
                <td>${formatDetailNumber(item.roe, 2, "%")}</td>
                <td>${formatDetailNumber(item.gross_margin, 2, "%")}</td>
                <td>${formatDetailNumber(item.net_margin, 2, "%")}</td>
                <td>${formatDetailNumber(item.debt_ratio, 2, "%")}</td>
                <td>${formatLargeMoney(item.net_profit, "CNY")}</td>
                <td>${formatDetailNumber(item.eps_ttm, 3)}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function renderStockInformationPanel(stock, detail) {
  const info = detail.information ?? {};
  const currentTab = stockInfoTabs.get(stock.symbol) || "filings";
  const rows = Array.isArray(info[currentTab]) ? info[currentTab] : [];
  const tabs = stockInfoTabOptions.map((item) => {
    const count = Array.isArray(info[item.id]) ? info[item.id].length : 0;
    return `
      <button class="stock-info-tab ${item.id === currentTab ? "active" : ""}" data-detail-info-tab="${item.id}" type="button">
        ${item.label}<span>${count}</span>
      </button>
    `;
  }).join("");
  return `
    <div class="stock-info-panel">
      <div class="stock-info-head">
        <strong>公告、资讯与讨论</strong>
        <span>用于后续基本面、情绪面和事件催化分析</span>
      </div>
      <div class="stock-info-tabs">${tabs}</div>
      <div class="stock-info-list">
        ${rows.length ? rows.map(renderStockInfoItem).join("") : renderStockInfoEmpty(currentTab)}
      </div>
    </div>
  `;
}

function renderStockInfoItem(item) {
  const title = item.title || item.summary || "未命名信息";
  const meta = [item.published_at, item.source, item.category].filter(Boolean).join(" · ");
  const url = String(item.url ?? "").trim();
  return `
    <article class="stock-info-item">
      <div>
        <strong>${escapeHTML(title)}</strong>
        <span>${escapeHTML(meta || "暂无来源时间")}</span>
        ${item.summary ? `<p>${escapeHTML(item.summary)}</p>` : ""}
      </div>
      ${url ? `<a href="${escapeHTML(url)}" target="_blank" rel="noreferrer">原文</a>` : ""}
    </article>
  `;
}

function renderStockInfoEmpty(tab) {
  const label = stockInfoTabOptions.find((item) => item.id === tab)?.label ?? "信息";
  const text = tab === "discussions"
    ? "讨论源还没有接入。后续可接入交易所互动平台或自有讨论数据。"
    : `当前数据库还没有这只股票的${label}记录。刷新会优先补公告和已配置资讯源。`;
  return `<div class="stock-detail-empty"><strong>暂无${label}</strong><span>${text}</span></div>`;
}

function formatDetailPrice(value, currency = "CNY", isIndex = false) {
  if (value === null || value === undefined || value === "") return "暂无";
  if (!hasMetric(Number(value))) return "暂无";
  if (isIndex) return Number(value).toFixed(2);
  if (currency === "CNY") return `¥${Number(value).toFixed(2)}`;
  return formatMoney(Number(value), currency);
}

function formatDetailNumber(value, digits = 2, suffix = "") {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? `${numeric.toFixed(digits)}${suffix}` : "暂无";
}

function formatPositiveDetailNumber(value, digits = 2, suffix = "") {
  const numeric = Number(value);
  return Number.isFinite(numeric) && numeric > 0 ? `${numeric.toFixed(digits)}${suffix}` : "暂无";
}

function formatPeTtm(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "暂无";
  if (numeric <= 0) return "亏损";
  return numeric.toFixed(2);
}

function formatSignedNumber(value, digits = 2, suffix = "") {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "暂无";
  const sign = numeric > 0 ? "+" : "";
  return `${sign}${numeric.toFixed(digits)}${suffix}`;
}

function formatLargeMoney(value, currency = "CNY") {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "暂无";
  const prefix = currency === "CNY" ? "" : `${currency} `;
  const absolute = Math.abs(numeric);
  if (absolute >= 1000000000000) return `${prefix}${(numeric / 1000000000000).toFixed(2)}万亿`;
  if (absolute >= 100000000) return `${prefix}${(numeric / 100000000).toFixed(2)}亿`;
  if (absolute >= 10000) return `${prefix}${(numeric / 10000).toFixed(2)}万`;
  return `${prefix}${numeric.toFixed(2)}`;
}

function formatShareVolume(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "暂无";
  if (Math.abs(numeric) >= 100000000) return `${(numeric / 100000000).toFixed(2)}亿`;
  if (Math.abs(numeric) >= 10000) return `${(numeric / 10000).toFixed(2)}万`;
  return numeric.toFixed(0);
}

function renderUncertainty(stock) {
  const reasons = uncertaintyReasons(stock);
  if (!reasons.length) {
    return `
      <article class="uncertainty-item pass">
        <div class="uncertainty-top">
          <strong>当前结论未触发硬阻断</strong>
          <span class="freshness-badge fresh">可继续</span>
        </div>
        <p>数据新鲜度、证据等级和因子冲突均未触发降级规则。</p>
      </article>
    `;
  }
  return reasons.map((item) => `
    <article class="uncertainty-item ${item.status}">
      <div class="uncertainty-top">
        <strong>${item.title}</strong>
        <span class="freshness-badge ${item.status}">${item.status === "stale" ? "阻断" : "需复核"}</span>
      </div>
      <p>${item.text}</p>
      <div class="inline-actions">
        ${item.action === "refresh" ? `<button class="mini-action" data-refresh-source="${item.source}" type="button">刷新数据</button>` : ""}
        ${item.action === "supplement" ? `<button class="mini-action" data-focus-supplement type="button">补充证据</button>` : ""}
        ${item.factor ? `<button class="mini-action" data-factor="${item.factor}" type="button">查看因子</button>` : ""}
      </div>
    </article>
  `).join("");
}

function uncertaintyReasons(stock) {
  const reasons = [];
  if (stock.freshnessStatus !== "fresh") {
    reasons.push({
      status: "stale",
      title: "行情数据不够新",
      text: `当前缓存延迟 ${stock.lagMinutes} 分钟，盘中分析必须刷新行情、K线、成交额和买卖价差。`,
      action: "refresh",
      source: "market"
    });
  }
  if (stock.truthScore < 80 || stock.metrics.unverifiedRatio >= 0.25) {
    reasons.push({
      status: "warn",
      title: "论据真实性不足",
      text: `证据可信度 ${stock.truthScore}%，未证实信息比例 ${(stock.metrics.unverifiedRatio * 100).toFixed(0)}%。只允许观察或复核，不升级为买入。`,
      action: "supplement"
    });
  }
  if (stock.factors.估值 < 55 && stock.factors.催化 >= 80) {
    reasons.push({
      status: "warn",
      title: "强催化与高估值冲突",
      text: `催化评分 ${stock.factors.催化}，估值评分 ${stock.factors.估值}。需要重新计算风险收益比和仓位上限。`,
      factor: "估值"
    });
  }
  if (stock.factors.技术 < 50 && stock.factors.基本面 >= 75) {
    reasons.push({
      status: "warn",
      title: "基本面与技术面冲突",
      text: `基本面评分 ${stock.factors.基本面}，技术评分 ${stock.factors.技术}。买卖判断需要区分长期质量和短期破位。`,
      factor: "技术"
    });
  }
  return reasons;
}

function renderFactorTile(stock, name, value, detailPayload = null) {
  const detail = factorDetail(stock, name, detailPayload);
  const displayValue = name === "情绪" && detail.liveScore !== null && detail.liveScore !== undefined
    ? detail.liveScore
    : value;
  return `
    <article class="factor-tile">
      <div class="factor-tile-top">
        <strong>${name}</strong>
        <span>${displayValue}</span>
      </div>
      <p>${detail.summary}</p>
      <button class="mini-action" data-factor="${name}" type="button">详情</button>
    </article>
  `;
}

function factorDetail(stock, name, detailPayload = null) {
  const m = stock.metrics;
  const sentimentSnapshot = detailPayload?.information?.sentiment ?? stockDetailCache.get(stock.symbol)?.information?.sentiment;
  const liveSentimentScore = sentimentFactorScore(sentimentSnapshot);
  const sentimentCounts = sentimentSnapshot?.source_counts ?? {};
  const map = {
    基本面: {
      summary: `ROE ${formatMetric(m.roe, 1, "%")}，收入增速 ${formatMetric(m.revenueGrowth, 1, "%")}，自由现金流率 ${formatMetric(m.fcfMargin, 1, "%")}。`,
      source: sourceDescriptionForKinds(stock, ["financial"]),
      values: [
        ["ROE", formatMetric(m.roe, 1, "%")],
        ["收入增速", formatMetric(m.revenueGrowth, 1, "%")],
        ["自由现金流率", formatMetric(m.fcfMargin, 1, "%")],
        ["资产负债率", formatMetric(m.debtRatio, 1, "%")]
      ],
      process: "先按最新完整财报归一化，再与行业中位数和自身三年分位比较；缺财报时不能用记忆替代。"
    },
    估值: {
      summary: `PE ${formatMetric(m.pe, 1)}，PE历史分位 ${formatMetricInt(m.pePercentile, "%")}，PB ${formatMetric(m.pb, 1)}。`,
      source: sourceDescriptionForKinds(stock, ["market", "financial"]),
      values: [
        ["PE", formatMetric(m.pe, 1)],
        ["PE历史分位", formatMetricInt(m.pePercentile, "%")],
        ["PB", formatMetric(m.pb, 1)],
        ["评分", stock.factors.估值]
      ],
      process: "价格必须取最新行情，盈利口径取最新可追溯财报；旧记忆只能提供上次估值分位作为对比。"
    },
    技术: {
      summary: `20日线偏离 ${m.ma20GapPct.toFixed(1)}%，量能 ${m.volumeRatio.toFixed(2)}倍，ATR ${m.atrPct.toFixed(1)}%。`,
      source: sourceDescriptionForKinds(stock, ["market"]),
      values: [
        ["20日线偏离", `${m.ma20GapPct.toFixed(1)}%`],
        ["量能倍数", `${m.volumeRatio.toFixed(2)}x`],
        ["ATR", `${m.atrPct.toFixed(1)}%`],
        ["60日最大回撤", `${m.maxDrawdown60d}%`]
      ],
      process: "必须重新读取历史K线和成交量，不能复用旧趋势结论；只复用上次关键价位作为比较点。"
    },
    催化: {
      summary: `催化评分 ${formatMetricInt(m.catalystScore)}，72小时新闻 ${formatMetricInt(m.newsCount72h)} 条，已验证比例 ${formatRatio(m.verifiedCatalystRatio)}。`,
      source: sourceDescriptionForKinds(stock, ["filing", "news"]),
      values: [
        ["催化评分", formatMetricInt(m.catalystScore)],
        ["72小时新闻数", formatMetricInt(m.newsCount72h)],
        ["已验证比例", formatRatio(m.verifiedCatalystRatio)],
        ["未证实比例", formatRatio(m.unverifiedRatio)]
      ],
      process: "先从公告和新闻抽 claim，再按来源等级、实体匹配和时效降权；C级来源不能单独触发买入。"
    },
    情绪: {
      summary: sentimentSnapshot
        ? `综合情绪 ${formatSentimentScore(sentimentSnapshot.composite_score)}（${sentimentLabelText(sentimentSnapshot.sentiment_label)}），公告/财报 ${formatSentimentScore(sentimentSnapshot.filing_news_score)}，社区 ${formatSentimentScore(sentimentSnapshot.community_score, 0, "community")}，交易 ${formatSentimentScore(sentimentSnapshot.market_score)}。`
        : `情绪分 ${formatMetricInt(m.sentimentScore)}，未证实比例 ${formatRatio(m.unverifiedRatio)}，72小时热度 ${formatMetricInt(m.newsCount72h)}。`,
      source: sentimentSnapshot
        ? `sentiment_snapshots：${sentimentSnapshot.as_of || "暂无日期"}，${sentimentSnapshot.window_days || 30}天窗口，${sentimentSourceCount(sentimentSnapshot)}条证据。`
        : sourceDescriptionForKinds(stock, ["news"]),
      values: sentimentSnapshot
        ? [
            ["综合情绪", formatSentimentScore(sentimentSnapshot.composite_score)],
            ["因子换算", liveSentimentScore ?? "暂无"],
            ["公告/财报", `${formatSentimentScore(sentimentSnapshot.filing_news_score)} · ${sentimentCounts.filing_news || 0}条`],
            ["社区舆论", `${formatSentimentScore(sentimentSnapshot.community_score, 0, "community")} · ${sentimentCounts.community || 0}条`],
            ["交易行为", `${formatSentimentScore(sentimentSnapshot.market_score)} · ${sentimentCounts.market || 0}条`],
            ["置信度", formatSentimentConfidence(sentimentSnapshot.confidence)]
          ]
        : [
            ["情绪分", formatMetricInt(m.sentimentScore)],
            ["未证实比例", formatRatio(m.unverifiedRatio)],
            ["热度", formatMetricInt(m.newsCount72h)],
            ["已验证催化", formatRatio(m.verifiedCatalystRatio)]
          ],
      process: sentimentSnapshot
        ? "把公告/财报/新闻、社区讨论和交易行为按证据数量、置信度和时间衰减聚合；情绪只作为辅助因子，不单独生成交易动作。"
        : "情绪只作为辅助。若未证实比例高，会降低结论强度，并要求补公告或公司来源。",
      liveScore: liveSentimentScore
    },
    风险: {
      summary: `20日波动 ${m.volatility20d}%，60日最大回撤 ${m.maxDrawdown60d}%，ATR ${m.atrPct.toFixed(1)}%。`,
      source: sourceDescriptionForKinds(stock, ["market", "filing"]),
      values: [
        ["20日波动", `${m.volatility20d}%`],
        ["60日最大回撤", `${m.maxDrawdown60d}%`],
        ["ATR", `${m.atrPct.toFixed(1)}%`],
        ["买卖价差", `${m.spreadBps}bp`]
      ],
      process: "把价格波动、流动性、公告风险和传闻比例合成；风险升高时优先限制动作强度和仓位。"
    }
  };
  return map[name];
}

function sourceDescriptionForKinds(stock, kinds) {
  return kinds.map((kind) => sourceDescriptionForKind(stock, kind)).join("；");
}

function sourceDescriptionForKind(stock, kind) {
  const label = sourceKindLabels[kind] ?? kind;
  if (kind === "financial" && stock.sourceStatus?.valuationBasis) {
    const basis = stock.sourceStatus.valuationBasis;
    if (basis.mode === "latest-market-with-prior-valuation") {
      return `${label}：${basis.label}，行情 ${basis.marketProvider ?? "行情数据源"} 快照 ${basis.asOf}`;
    }
    return `${label}：${basis.label}${basis.asOf ? `，快照 ${basis.asOf}` : ""}`;
  }
  const snapshot = kind === "market"
    ? stock.sourceStatus?.marketSnapshot
    : kind === "financial"
      ? stock.sourceStatus?.financialSnapshot
      : null;
  const snapshotProvider = snapshot?.provider ? providerDisplayName(snapshot.provider) : "";
  const activeLabels = activeSourceLabelsForKind(kind, stock.market);
  const providerText = snapshotProvider || activeLabels.join("、");
  const missing = (stock.sourceStatus?.missingKinds ?? []).includes(kind);
  if (missing && providerText) return `${label}：${providerText} 已启用，当前股票暂无可用快照`;
  if (missing || !providerText) return `${label}：未启用或未配置`;
  const asOf = snapshot?.asOf ? `，快照 ${snapshot.asOf}` : "";
  return `${label}：${providerText}${asOf}`;
}

function renderEvidence(item, index) {
  return `
    <div class="evidence-item">
      <div class="evidence-top">
        <span class="source-tier">${item.tier}</span>
        <span class="confidence">${Math.round(item.confidence * 100)}% · ${escapeHTML(displayText(item.source))}</span>
      </div>
      <p>${escapeHTML(displayText(item.claim))}</p>
      <button class="mini-action" data-claim-index="${index}" type="button">详情</button>
    </div>
  `;
}

function renderReflection(item) {
  return `
    <div class="reflection-item ${item.status}">
      <div class="reflection-top">
        <strong>${item.round} · ${item.label}</strong>
        <span class="freshness-badge ${item.status === "pass" ? "fresh" : item.status}">${statusText(item.status)}</span>
      </div>
      <p>${item.text}</p>
    </div>
  `;
}

function renderMemory(stock) {
  memoryList.innerHTML = `
    <div class="memory-meta">
      <span>更新时间 ${stock.memoryUpdatedAt}</span>
      <span>补充证据 ${stock.supplementCount} 条</span>
    </div>
    <section class="memory-section">
      <h4>可复用中间结果</h4>
      ${stock.memory.reusable.map((item) => `<article><strong>${item.title}</strong><p>${item.text}</p></article>`).join("")}
    </section>
    <section class="memory-section">
      <h4>必须重新拉原数据</h4>
      <ul>${stock.memory.mustRefresh.map((item) => `<li>${item}</li>`).join("")}</ul>
    </section>
    <section class="memory-section">
      <h4>本次增量</h4>
      <ul>${stock.memory.delta.map((item) => `<li>${item}</li>`).join("")}</ul>
    </section>
  `;
}

function renderUnknown(symbol) {
  const normalized = symbol || "未输入";
  detailTitle.textContent = `${normalized} · 未接入样本`;
  if (detailFavorite) detailFavorite.hidden = true;
  detailBody.innerHTML = `
    <p class="thesis">本地数据源没有找到 ${escapeHTML(normalized)}。接口未返回足够证据时，系统拒绝生成买入或卖出结论。</p>
    <div class="evidence-list">
      ${renderEvidence({ tier: "F", source: "Data gate", claim: "缺少行情、财务、公告和新闻证据，必须先刷新或接入真实数据源。", confidence: 0, process: [], rawFields: {}, url: "" }, 0)}
    </div>
  `;
  reflectionList.innerHTML = [
    { round: "第 1 轮", label: "数据闸门", status: "fail", text: "没有可用数据，提前停止反思。" },
    { round: "第 2 轮", label: "证据闸门", status: "fail", text: "无证据链，禁止生成投资结论。" },
    { round: "第 3 轮", label: "投资逻辑", status: "fail", text: "由于前置闸门失败，本轮不消耗更多分析。" }
  ].map(renderReflection).join("");
  memoryList.innerHTML = `<div class="empty-state compact">没有可复用记忆。</div>`;
  if (sentimentAside) {
    sentimentAside.innerHTML = `
      <div class="sentiment-panel sentiment-panel-side empty">
        <div class="stock-detail-empty warn">
          <strong>暂无情绪面</strong>
          <span>本地数据源没有找到 ${escapeHTML(normalized)}，无法展开情绪证据。</span>
        </div>
      </div>
    `;
  }
}

function renderWatchlist() {
  const positions = openPositions();
  if (!positions.some((position) => position.symbol === selectedHoldingSymbol)) {
    selectedHoldingSymbol = positions[0]?.symbol ?? "";
  }
  renderPortfolioSummary();
  renderHoldingRows();
  renderTradeRows();
  renderFavoriteRows();
  if (activeTab === "holdings") {
    schedulePortfolioDraw();
    schedulePositionDraw();
  }
}

function renderPortfolioSummary() {
  const backend = backendPortfolio();
  if (backend) {
    const totals = backend.totals;
    const byCurrency = Object.entries(totals.by_currency ?? {}).map(([currency, values]) => `
      <span>${currency}: ${formatMoney(values.market_value, currency)} / ${formatMoney(values.total_profit, currency)}</span>
    `).join("");

    portfolioSummary.innerHTML = `
      <article class="portfolio-card">
        <span>持仓数</span>
        <strong>${totals.position_count}</strong>
      </article>
      <article class="portfolio-card">
        <span>市值折算</span>
        <strong>${formatMoney(totals.market_value_cny, "CNY")}</strong>
      </article>
      <article class="portfolio-card profit-card">
        <span>盈利金额</span>
        <strong class="${totals.profit_cny >= 0 ? "profit" : "loss"}">${formatMoney(totals.profit_cny, "CNY")}</strong>
        <button class="mini-action refresh-profit" data-refresh-profit type="button">刷新股价</button>
      </article>
      <article class="portfolio-card">
        <span>总收益率</span>
        <strong class="${totals.return_rate >= 0 ? "profit" : "loss"}">${formatPct(totals.return_rate)}</strong>
      </article>
      <div class="currency-breakdown">
        ${byCurrency || "暂无持仓"}
        <span>后端计算：${backend.computed_at}</span>
        <span>最新价：${latestPriceRefreshAt}</span>
      </div>
    `;
    return;
  }

  const totals = portfolioTotals();
  const byCurrency = [...totals.byCurrency.entries()].map(([currency, values]) => `
    <span>${currency}: ${formatMoney(values.marketValue, currency)} / ${formatMoney(values.totalProfit, currency)}</span>
  `).join("");

  portfolioSummary.innerHTML = `
    <article class="portfolio-card">
      <span>持仓数</span>
      <strong>${totals.positions.length}</strong>
    </article>
    <article class="portfolio-card">
      <span>市值折算</span>
      <strong>${formatMoney(totals.marketValueCny, "CNY")}</strong>
    </article>
    <article class="portfolio-card profit-card">
      <span>盈利金额</span>
      <strong class="${totals.profitCny >= 0 ? "profit" : "loss"}">${formatMoney(totals.profitCny, "CNY")}</strong>
      <button class="mini-action refresh-profit" data-refresh-profit type="button">刷新股价</button>
    </article>
    <article class="portfolio-card">
      <span>总收益率</span>
      <strong class="${totals.returnRate >= 0 ? "profit" : "loss"}">${formatPct(totals.returnRate)}</strong>
    </article>
    <div class="currency-breakdown">
      ${byCurrency || "暂无持仓"}
      <span>最新价：${latestPriceRefreshAt}</span>
    </div>
  `;
}

function renderHoldingRows() {
  const backend = backendPortfolio();
  if (backend) {
    holdingRows.innerHTML = backend.positions.length ? backend.positions.map((position) => `
      <tr class="${position.symbol === selectedHoldingSymbol ? "selected-row" : ""}" data-holding-symbol="${position.symbol}">
        <td><strong>${position.symbol}</strong><br /><span class="confidence">${position.name}</span></td>
        <td>${position.quantity}</td>
        <td>${formatMoney(position.avg_cost, position.currency)}</td>
        <td>${formatMoney(position.current_price, position.currency)}</td>
        <td><strong class="${position.total_profit >= 0 ? "profit" : "loss"}">${formatMoney(position.total_profit, position.currency)}</strong></td>
        <td><strong class="${position.return_rate >= 0 ? "profit" : "loss"}">${formatPct(position.return_rate)}</strong></td>
      </tr>
    `).join("") : `
      <tr><td colspan="6"><span class="confidence">暂无持仓，录入 Buy 后会显示。</span></td></tr>
    `;
    return;
  }

  const positions = openPositions();
  holdingRows.innerHTML = positions.length ? positions.map((position) => {
    const stock = position.stock;
    return `
      <tr class="${position.symbol === selectedHoldingSymbol ? "selected-row" : ""}" data-holding-symbol="${position.symbol}">
        <td><strong>${stock.symbol}</strong><br /><span class="confidence">${stock.name}</span></td>
        <td>${position.quantity}</td>
        <td>${formatMoney(position.avgCost, stock.currency)}</td>
        <td>${formatMoney(stock.price, stock.currency)}</td>
        <td><strong class="${position.totalProfit >= 0 ? "profit" : "loss"}">${formatMoney(position.totalProfit, stock.currency)}</strong></td>
        <td><strong class="${position.returnRate >= 0 ? "profit" : "loss"}">${formatPct(position.returnRate)}</strong></td>
      </tr>
    `;
  }).join("") : `
    <tr><td colspan="6"><span class="confidence">暂无持仓，录入 Buy 后会显示。</span></td></tr>
  `;
}

function renderTradeRows() {
  const rows = selectedHoldingSymbol
    ? portfolioTrades.filter((trade) => trade.symbol === selectedHoldingSymbol)
    : portfolioTrades;
  tradeRows.innerHTML = [...rows].sort(tradeSort).reverse().map((trade) => {
    const stock = stockBySymbol(trade.symbol);
    return `
      <tr>
        <td>${trade.date}</td>
        <td><strong>${trade.symbol}</strong><br /><span class="confidence">${stock?.name ?? "未知股票"}</span></td>
        <td><span class="trade-chip ${trade.side.toLowerCase()}">${trade.side === "BUY" ? "B" : "S"}</span></td>
        <td>${trade.quantity}</td>
        <td>${formatMoney(trade.price, stock?.currency ?? "CNY")}</td>
        <td>${formatMoney(trade.fee, stock?.currency ?? "CNY")}</td>
      </tr>
    `;
  }).join("") || `<tr><td colspan="6"><span class="confidence">暂无流水。</span></td></tr>`;
}

function renderFavoriteRows() {
  const favoriteItems = [...favoriteSymbols].map((symbol) => {
    const stock = stockBySymbol(symbol);
    if (!stock) queueFavoriteStockLoad(symbol);
    return stock ?? { symbol, missing: true };
  });
  favoriteCount.textContent = `${favoriteItems.length} 只`;
  favoriteGrid.innerHTML = favoriteItems.length
    ? favoriteItems.map((item) => item.missing ? renderFavoritePlaceholder(item.symbol) : renderStockCard(item)).join("")
    : `<div class="empty-state">还没有加入关注的股票。</div>`;
  scheduleSparklineDraw();
}

function renderFavoritePlaceholder(symbol) {
  return `
    <article class="stock-card favorite-placeholder" data-symbol="${escapeHTML(symbol)}">
      <div class="card-head">
        <div>
          <p class="symbol">${escapeHTML(symbol)}</p>
          <p class="company">正在补全股票资料</p>
        </div>
        <div class="card-actions">
          <button class="status-badge active" data-favorite="${escapeHTML(symbol)}" type="button" aria-label="取消关注 ${escapeHTML(symbol)}">
            <span class="badge-icon bookmark-icon"></span>
            <span>已关注</span>
          </button>
        </div>
      </div>
      <div class="empty-state compact">已加入关注列表，正在从数据库读取名称、行情和 K 线。</div>
    </article>
  `;
}

async function queueFavoriteStockLoad(symbol) {
  if (!apiState.connected || favoriteStockLoading.has(symbol) || favoriteStockLoadFailed.has(symbol) || stockBySymbol(symbol)) return;
  favoriteStockLoading.add(symbol);
  try {
    const params = new URLSearchParams({
      q: symbol,
      market: "all",
      account_id: apiState.accountId
    });
    const payload = await apiRequest(`/api/stocks/search?${params.toString()}`);
    const apiStocks = Array.isArray(payload.stocks) ? payload.stocks : [];
    if (!apiStocks.length) favoriteStockLoadFailed.add(symbol);
    mergeApiStocks(apiStocks);
  } catch (error) {
    favoriteStockLoadFailed.add(symbol);
    apiState.lastError = `关注股票补全失败：${error.message}`;
    updateBackendStatus(apiState.lastError);
  } finally {
    favoriteStockLoading.delete(symbol);
    renderFavoriteRows();
    renderCandidates();
  }
}

function portfolioCurvePoints() {
  const positions = openPositions();
  const length = Math.max(...stocks.map((stock) => stock.spark.length));
  return Array.from({ length }, (_, index) => {
    let value = 0;
    let base = 0;
    positions.forEach((position) => {
      const stock = position.stock;
      const price = stock.spark[index] ?? stock.price;
      const fx = fxToCny[stock.currency] ?? 1;
      value += (position.quantity * price + position.realizedProfit) * fx;
      base += position.costBasis * fx;
    });
    return {
      label: `D-${length - index - 1}`,
      profit: value - base
    };
  });
}

function drawPortfolioCurve() {
  if (!portfolioCurve) return;
  const ctx = portfolioCurve.getContext("2d");
  const width = portfolioCurve.width;
  const height = portfolioCurve.height;
  const points = portfolioCurvePoints();
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#fbfcfd";
  ctx.fillRect(0, 0, width, height);

  if (!points.length) return;
  const profits = points.map((point) => point.profit);
  const min = Math.min(...profits, 0);
  const max = Math.max(...profits, 0);
  const span = Math.max(max - min, 1);
  const padX = 42;
  const padY = 26;
  const zeroY = height - padY - ((0 - min) / span) * (height - padY * 2);

  ctx.strokeStyle = "#dbe2e7";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(padX, zeroY);
  ctx.lineTo(width - padX, zeroY);
  ctx.stroke();

  ctx.strokeStyle = profits.at(-1) >= 0 ? "#16815f" : "#b43c43";
  ctx.lineWidth = 4;
  ctx.beginPath();
  points.forEach((point, index) => {
    const x = padX + (index / Math.max(points.length - 1, 1)) * (width - padX * 2);
    const y = height - padY - ((point.profit - min) / span) * (height - padY * 2);
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  ctx.fillStyle = "#66737d";
  ctx.font = "700 22px system-ui";
  ctx.fillText(`盈利 ${formatMoney(profits.at(-1), "CNY")}`, padX, 34);
}

function drawPositionKline() {
  if (!positionKline || !tradeDetailsOpen) return;
  const stock = stockBySymbol(selectedHoldingSymbol) ?? openPositions()[0]?.stock;
  if (!stock) return;

  const ctx = positionKline.getContext("2d");
  const width = positionKline.width;
  const height = positionKline.height;
  const padX = 46;
  const padY = 30;
  const prices = stock.spark;
  const candles = prices.map((close, index) => {
    const prev = prices[Math.max(index - 1, 0)];
    const open = index === 0 ? close * 0.99 : prev;
    const high = Math.max(open, close) * (1 + 0.006 + index * 0.0006);
    const low = Math.min(open, close) * (1 - 0.006 - index * 0.0004);
    return { open, close, high, low };
  });
  const min = Math.min(...candles.map((item) => item.low));
  const max = Math.max(...candles.map((item) => item.high));
  const span = Math.max(max - min, 1);
  const plotWidth = width - padX * 2;
  const plotHeight = height - padY * 2;
  const step = plotWidth / Math.max(candles.length, 1);
  const candleWidth = Math.max(12, step * 0.5);
  const yFor = (value) => height - padY - ((value - min) / span) * plotHeight;

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#fbfcfd";
  ctx.fillRect(0, 0, width, height);
  ctx.strokeStyle = "#dbe2e7";
  ctx.lineWidth = 1;
  ctx.beginPath();
  [0, 0.5, 1].forEach((ratio) => {
    const y = padY + plotHeight * ratio;
    ctx.moveTo(padX, y);
    ctx.lineTo(width - padX, y);
  });
  ctx.stroke();

  candles.forEach((item, index) => {
    const x = padX + step * index + step / 2;
    const up = item.close >= item.open;
    const color = up ? "#16815f" : "#b43c43";
    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(x, yFor(item.high));
    ctx.lineTo(x, yFor(item.low));
    ctx.stroke();

    const top = yFor(Math.max(item.open, item.close));
    const bottom = yFor(Math.min(item.open, item.close));
    ctx.fillRect(x - candleWidth / 2, top, candleWidth, Math.max(bottom - top, 4));
  });

  const selectedTrades = tradesForSymbol(stock.symbol);
  selectedTrades.forEach((trade, index) => {
    const candleIndex = Math.min(candles.length - 1, Math.max(0, candles.length - selectedTrades.length + index));
    const x = padX + step * candleIndex + step / 2;
    const y = yFor(candles[candleIndex].high) - 18;
    ctx.beginPath();
    ctx.arc(x, y, 14, 0, Math.PI * 2);
    ctx.fillStyle = trade.side === "BUY" ? "#dff5ec" : "#fde2e5";
    ctx.fill();
    ctx.strokeStyle = trade.side === "BUY" ? "#16815f" : "#b43c43";
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.fillStyle = trade.side === "BUY" ? "#16815f" : "#b43c43";
    ctx.font = "900 14px system-ui";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(trade.side === "BUY" ? "B" : "S", x, y + 1);
  });

  ctx.fillStyle = "#172026";
  ctx.font = "900 20px system-ui";
  ctx.textAlign = "left";
  ctx.fillText(`${stock.symbol} ${stock.name}`, padX, 24);
  ctx.fillStyle = "#66737d";
  ctx.font = "800 13px system-ui";
  ctx.fillText(`当前价 ${formatMoney(stock.price, stock.currency)} · 流水 ${selectedTrades.length} 笔`, padX + 190, 24);
}

function drawStockDetailCharts() {
  document.querySelectorAll("[data-stock-kline]").forEach((canvas) => {
    redrawStockKlineCanvas(canvas);
  });
}

function redrawStockKlineCanvas(canvas) {
  if (!canvas) return;
  const symbol = canvas.dataset.stockKline;
  const period = canvas.dataset.period;
  const detail = stockDetailCache.get(symbol);
  const bars = detail?.market_data?.periods?.[period]?.bars ?? [];
  drawStockKlineChart(canvas, bars, detail?.summary ?? {});
}

function normalizeStockKlineBars(bars) {
  return (bars || [])
    .filter((bar) => Number.isFinite(Number(bar.close)))
    .map((bar) => ({
      ...bar,
      open: Number.isFinite(Number(bar.open)) ? Number(bar.open) : Number(bar.close),
      high: Number.isFinite(Number(bar.high)) ? Number(bar.high) : Number(bar.close),
      low: Number.isFinite(Number(bar.low)) ? Number(bar.low) : Number(bar.close),
      close: Number(bar.close),
      volume: Number.isFinite(Number(bar.volume)) ? Number(bar.volume) : 0,
      amount: Number.isFinite(Number(bar.amount)) ? Number(bar.amount) : 0,
      change_pct: Number.isFinite(Number(bar.change_pct)) ? Number(bar.change_pct) : null,
      turnover_rate: Number.isFinite(Number(bar.turnover_rate)) ? Number(bar.turnover_rate) : null,
      date: bar.date ?? bar.trade_date ?? bar.datetime
    }));
}

function drawStockKlineChart(canvas, bars, summary = {}) {
  const { ctx, width, height } = prepareCanvasForDraw(canvas, 920, 420);
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, width, height);

  const validBars = normalizeStockKlineBars(bars);
  const visible = validBars.slice(-92);
  if (visible.length < 2) {
    ctx.fillStyle = "#66737d";
    ctx.font = "800 18px system-ui";
    ctx.fillText("暂无足够 K 线数据", 42, 72);
    return;
  }

  const yScale = height / 420;
  const scaleY = (value) => Math.round(value * yScale);
  const isNarrowChart = width < 640;
  const padLeft = 16;
  const priceTop = isNarrowChart ? Math.max(72, scaleY(86)) : Math.max(48, scaleY(58));
  const priceHeight = isNarrowChart ? Math.max(140, scaleY(182)) : Math.max(136, scaleY(210));
  const volumeTop = Math.max(priceTop + priceHeight + 22, scaleY(isNarrowChart ? 286 : 292));
  const volumeHeight = isNarrowChart ? Math.max(54, scaleY(58)) : Math.max(42, scaleY(58));
  const macdTop = Math.max(volumeTop + volumeHeight + 24, scaleY(374));
  const macdHeight = Math.max(28, Math.min(scaleY(34), height - macdTop - 8));
  const highs = visible.map((bar) => bar.high);
  const lows = visible.map((bar) => bar.low);
  const technicalRange = estimateSupportResistance(visible, summary);
  const currentPrice = Number(summary.price ?? visible.at(-1)?.close);
  ctx.font = "900 14px system-ui";
  const markerLabelWidth = Math.max(
    ...[technicalRange.resistance, currentPrice, technicalRange.support]
      .filter(Number.isFinite)
      .map((value) => ctx.measureText(formatTechnicalLevel(value)).width),
    42
  );
  const padRight = Math.max(62, Math.ceil(markerLabelWidth + 24));
  const plotWidth = width - padLeft - padRight;
  const xStep = plotWidth / visible.length;
  const candleWidth = Math.max(2, Math.min(11, xStep * 0.62));
  const markerValues = [technicalRange.support, technicalRange.resistance, currentPrice].filter(Number.isFinite);
  const rawPriceMin = Math.min(...lows, ...markerValues);
  const rawPriceMax = Math.max(...highs, ...markerValues);
  const pricePadding = Math.max((rawPriceMax - rawPriceMin) * 0.08, Math.abs(rawPriceMax || 1) * 0.006);
  const priceMin = rawPriceMin - pricePadding;
  const priceMax = rawPriceMax + pricePadding;
  const priceSpan = Math.max(priceMax - priceMin, 0.01);
  const yPrice = (value) => priceTop + priceHeight - ((value - priceMin) / priceSpan) * priceHeight;
  const xFor = (index) => padLeft + xStep * index + xStep / 2;
  const chartRight = width - padRight;
  const hover = stockKlineHoverState.get(canvas);
  const hoverIndex = stockKlineHoverIndex(hover, padLeft, chartRight, xStep, visible.length, height);
  const activeIndex = hoverIndex ?? visible.length - 1;
  const maConfigs = [
    { window: 5, label: "MA5", color: "#5f6368" },
    { window: 10, label: "MA10", color: "#8a17ff" },
    { window: 30, label: "MA30", color: "#f5a400" }
  ];
  const closeValues = validBars.map((bar) => bar.close);
  const maSeries = maConfigs.map((config) => {
    const values = movingAverage(closeValues, config.window);
    return {
      ...config,
      values,
      visibleValues: values.slice(-visible.length)
    };
  });

  drawStockChartGrid(ctx, padLeft, padRight, priceTop, priceHeight, width, priceMin, priceMax);
  if (hoverIndex !== null) {
    ctx.fillStyle = "rgba(49, 109, 255, 0.06)";
    ctx.fillRect(Math.max(padLeft, xFor(hoverIndex) - xStep / 2), priceTop, Math.min(xStep, chartRight - padLeft), height - priceTop - 8);
  }
  drawStockChartLegend(ctx, visible, validBars, summary, padLeft, priceTop, width, activeIndex, maSeries);

  visible.forEach((bar, index) => {
    const x = xFor(index);
    const up = bar.close >= bar.open;
    const color = up ? "#e23b22" : "#059447";
    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(x, yPrice(bar.high));
    ctx.lineTo(x, yPrice(bar.low));
    ctx.stroke();
    const top = yPrice(Math.max(bar.open, bar.close));
    const bottom = yPrice(Math.min(bar.open, bar.close));
    ctx.fillRect(x - candleWidth / 2, top, candleWidth, Math.max(bottom - top, 2));
  });

  maSeries.forEach((config) => {
    drawIndicatorLine(ctx, config.visibleValues, xFor, yPrice, config.color, 1.8);
  });

  const priceMarkerSlots = [];
  drawPriceMarker(ctx, padLeft, chartRight, yPrice, technicalRange.resistance, formatTechnicalLevel(technicalRange.resistance), "#ff263d", "resistance", priceMarkerSlots);
  drawPriceMarker(ctx, padLeft, chartRight, yPrice, currentPrice, formatAxisNumber(currentPrice), "#ff263d", "current", priceMarkerSlots);
  drawPriceMarker(ctx, padLeft, chartRight, yPrice, technicalRange.support, formatTechnicalLevel(technicalRange.support), "#55b72f", "support", priceMarkerSlots);
  drawStockVolumePanel(ctx, visible, xFor, candleWidth, padLeft, padRight, volumeTop, volumeHeight, width, activeIndex);
  if (!isNarrowChart) {
    drawStockMacdPanel(ctx, validBars, visible.length, xFor, padLeft, padRight, macdTop, macdHeight, width, activeIndex);
  }
  drawStockXAxis(ctx, visible, xFor, isNarrowChart ? height - 14 : macdTop - 8, width, padLeft, padRight);
  if (hoverIndex !== null) {
    drawStockKlineHoverOverlay(ctx, {
      visible,
      allBars: validBars,
      summary,
      hover,
      hoverIndex,
      xFor,
      yPrice,
      padLeft,
      chartRight,
      priceTop,
      priceHeight,
      priceMin,
      priceMax,
      priceSpan,
      volumeTop,
      volumeHeight,
      macdTop,
      macdHeight,
      width,
      height,
      isNarrowChart,
      maSeries
    });
  }
}

function stockKlineHoverIndex(hover, padLeft, chartRight, xStep, visibleLength, height) {
  if (!hover || !Number.isFinite(hover.x) || !Number.isFinite(hover.y)) return null;
  if (hover.x < padLeft || hover.x > chartRight || hover.y < 0 || hover.y > height) return null;
  const index = Math.floor((hover.x - padLeft) / Math.max(xStep, 1));
  return Math.max(0, Math.min(visibleLength - 1, index));
}

function drawStockKlineHoverOverlay(ctx, options) {
  const {
    visible,
    allBars,
    summary,
    hover,
    hoverIndex,
    xFor,
    yPrice,
    padLeft,
    chartRight,
    priceTop,
    priceHeight,
    priceMax,
    priceSpan,
    volumeTop,
    volumeHeight,
    macdTop,
    macdHeight,
    width,
    height,
    isNarrowChart,
    maSeries
  } = options;
  const bar = visible[hoverIndex];
  if (!bar) return;

  const x = xFor(hoverIndex);
  const overlayBottom = isNarrowChart
    ? height - 24
    : Math.min(height - 8, macdTop + macdHeight);
  const pointerInPricePanel = hover.y >= priceTop && hover.y <= priceTop + priceHeight;
  const horizontalY = pointerInPricePanel
    ? hover.y
    : yPrice(bar.close);
  const hoverPrice = priceMax - ((horizontalY - priceTop) / Math.max(priceHeight, 1)) * priceSpan;

  ctx.save();
  ctx.strokeStyle = "rgba(82, 89, 99, 0.86)";
  ctx.lineWidth = 1;
  ctx.setLineDash([3, 5]);
  ctx.beginPath();
  ctx.moveTo(x, priceTop);
  ctx.lineTo(x, overlayBottom);
  ctx.moveTo(padLeft, horizontalY);
  ctx.lineTo(chartRight, horizontalY);
  ctx.stroke();
  ctx.setLineDash([]);

  drawStockKlineAxisPill(ctx, formatStockHoverPrice(hoverPrice), chartRight + 6, horizontalY, width);
  drawStockKlineDatePill(ctx, longTradeDate(bar.date), x, overlayBottom, padLeft, chartRight);
  drawStockKlineHoverTooltip(ctx, {
    visible,
    allBars,
    summary,
    hoverIndex,
    x,
    padLeft,
    chartRight,
    priceTop,
    width,
    height,
    maSeries
  });
  ctx.restore();
}

function drawStockKlineAxisPill(ctx, text, x, y, width) {
  ctx.save();
  ctx.font = "900 12px system-ui";
  const labelWidth = Math.max(50, ctx.measureText(text).width + 12);
  const labelHeight = 22;
  const labelX = Math.min(x, width - labelWidth - 4);
  const labelY = Math.max(4, Math.min(y - labelHeight / 2, ctx.canvas.getBoundingClientRect().height - labelHeight - 4));
  roundedRectPath(ctx, labelX, labelY, labelWidth, labelHeight, 6);
  ctx.fillStyle = "#ff263d";
  ctx.fill();
  ctx.fillStyle = "#ffffff";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text, labelX + labelWidth / 2, labelY + labelHeight / 2 + 0.5);
  ctx.restore();
}

function drawStockKlineDatePill(ctx, text, x, y, padLeft, chartRight) {
  ctx.save();
  ctx.font = "900 12px system-ui";
  const labelWidth = Math.max(74, ctx.measureText(text).width + 16);
  const labelHeight = 22;
  const labelX = Math.max(padLeft, Math.min(x - labelWidth / 2, chartRight - labelWidth));
  const labelY = Math.max(4, y - labelHeight + 2);
  roundedRectPath(ctx, labelX, labelY, labelWidth, labelHeight, 6);
  ctx.fillStyle = "#172026";
  ctx.fill();
  ctx.fillStyle = "#ffffff";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text, labelX + labelWidth / 2, labelY + labelHeight / 2 + 0.5);
  ctx.restore();
}

function drawStockKlineHoverTooltip(ctx, options) {
  const {
    visible,
    allBars,
    summary,
    hoverIndex,
    x,
    padLeft,
    chartRight,
    priceTop,
    width,
    height,
  } = options;
  const metrics = stockKlineBarMetrics(allBars, visible, hoverIndex, summary);
  const directionColor = metrics.change >= 0 ? "#e23b22" : "#059447";
  const currency = summary.currency || "CNY";
  const rows = [
    { label: "时间", value: longTradeDate(metrics.bar.date), color: "#172026" },
    { label: "开盘价", value: formatStockHoverPrice(metrics.bar.open), color: "#172026" },
    { label: "最高价", value: formatStockHoverPrice(metrics.bar.high), color: "#e23b22" },
    { label: "最低价", value: formatStockHoverPrice(metrics.bar.low), color: "#059447" },
    { label: "收盘价", value: formatStockHoverPrice(metrics.bar.close), color: directionColor },
    { label: "涨跌额", value: formatSignedNumber(metrics.change, 2), color: directionColor },
    { label: "涨跌幅", value: Number.isFinite(metrics.changePct) ? formatSignedNumber(metrics.changePct, 2, "%") : "暂无", color: directionColor },
    { label: "成交量", value: formatShareVolume(metrics.bar.volume), color: "#172026" },
    { label: "成交额", value: formatLargeMoney(metrics.bar.amount, currency), color: "#172026" },
    { label: "换手率", value: Number.isFinite(Number(metrics.bar.turnover_rate)) ? formatDetailNumber(metrics.bar.turnover_rate, 2, "%") : "暂无", color: "#172026" }
  ];
  const compact = width < 640;
  const rowHeight = compact ? 17 : 19;
  const paddingX = 12;
  const paddingY = 10;
  const tooltipWidth = compact ? 176 : 196;
  const tooltipHeight = paddingY * 2 + rows.length * rowHeight;
  const boxWidth = Math.max(150, Math.min(tooltipWidth, chartRight - padLeft - 12));
  const boxHeight = tooltipHeight;
  let boxX = padLeft + 10;
  if (x < boxX + boxWidth + 16) {
    boxX = Math.min(chartRight - boxWidth - 8, x + 16);
  }
  boxX = Math.max(padLeft + 6, Math.min(boxX, chartRight - boxWidth - 6));
  const boxY = Math.max(8, Math.min(priceTop + 8, height - boxHeight - 8));

  ctx.save();
  ctx.shadowColor = "rgba(15, 23, 32, 0.16)";
  ctx.shadowBlur = 14;
  ctx.shadowOffsetY = 5;
  roundedRectPath(ctx, boxX, boxY, boxWidth, boxHeight, 8);
  ctx.fillStyle = "rgba(255, 255, 255, 0.97)";
  ctx.fill();
  ctx.shadowColor = "transparent";
  ctx.lineWidth = 2;
  ctx.strokeStyle = "#ff4d4f";
  ctx.stroke();

  ctx.textBaseline = "middle";
  ctx.beginPath();
  ctx.rect(boxX + 6, boxY + 6, boxWidth - 12, boxHeight - 12);
  ctx.clip();
  rows.forEach((row, index) => {
    const y = boxY + paddingY + rowHeight / 2 + index * rowHeight;
    ctx.font = "850 13px system-ui";
    ctx.textAlign = "left";
    ctx.fillStyle = "#4e5a64";
    ctx.fillText(row.label, boxX + paddingX, y);
    ctx.fillStyle = row.color;
    ctx.font = "900 13px system-ui";
    drawCanvasFittedText(ctx, row.value, boxX + boxWidth - paddingX, y, boxWidth - 92, "right");
  });
  ctx.restore();
}

function drawCanvasFittedText(ctx, text, x, y, maxWidth, align = "left") {
  const raw = String(text ?? "");
  let output = raw;
  if (ctx.measureText(output).width > maxWidth) {
    while (output.length > 1 && ctx.measureText(`${output}...`).width > maxWidth) {
      output = output.slice(0, -1);
    }
    output = `${output}...`;
  }
  ctx.textAlign = align;
  ctx.fillText(output, x, y);
}

function stockKlineBarMetrics(allBars, visible, visibleIndex, summary = {}) {
  const bar = visible[visibleIndex];
  const globalIndex = Math.max(0, allBars.length - visible.length + visibleIndex);
  const previousClose = Number(allBars[globalIndex - 1]?.close ?? bar.open);
  const rawChangePct = Number(bar.change_pct);
  const changePct = Number.isFinite(rawChangePct)
    ? rawChangePct
    : (Number.isFinite(previousClose) && previousClose !== 0 ? ((bar.close - previousClose) / previousClose) * 100 : null);
  const change = Number.isFinite(changePct) && Number.isFinite(previousClose)
    ? (previousClose * changePct) / 100
    : bar.close - previousClose;
  return {
    bar,
    globalIndex,
    previousClose,
    change,
    changePct
  };
}

function formatStockHoverPrice(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric.toFixed(2) : "暂无";
}

function prepareCanvasForDraw(canvas, fallbackWidth, fallbackHeight) {
  const rect = canvas.getBoundingClientRect();
  const cssWidth = Math.max(1, Math.round(rect.width || fallbackWidth));
  const cssHeight = Math.max(1, Math.round(rect.height || fallbackHeight));
  const dpr = Math.max(1, Math.min(window.devicePixelRatio || 1, 3));
  const targetWidth = Math.round(cssWidth * dpr);
  const targetHeight = Math.round(cssHeight * dpr);
  if (canvas.width !== targetWidth || canvas.height !== targetHeight) {
    canvas.width = targetWidth;
    canvas.height = targetHeight;
  }
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.imageSmoothingEnabled = true;
  return { ctx, width: cssWidth, height: cssHeight };
}

function drawStockChartGrid(ctx, padLeft, padRight, top, panelHeight, width, min, max) {
  ctx.strokeStyle = "#e6e8eb";
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (let index = 0; index <= 4; index += 1) {
    const ratio = index / 4;
    const y = top + panelHeight * ratio;
    ctx.moveTo(padLeft, y);
    ctx.lineTo(width - padRight, y);
  }
  for (let index = 0; index <= 4; index += 1) {
    const x = padLeft + ((width - padLeft - padRight) * index) / 4;
    ctx.moveTo(x, top);
    ctx.lineTo(x, top + panelHeight);
  }
  ctx.stroke();

  ctx.fillStyle = "#555b62";
  ctx.font = "700 13px system-ui";
  ctx.textAlign = "left";
  ctx.textBaseline = "middle";
  for (let index = 0; index <= 4; index += 1) {
    const ratio = index / 4;
    const value = max - (max - min) * ratio;
    const y = top + panelHeight * ratio;
    ctx.fillText(formatAxisNumber(value), width - padRight + 12, y);
  }
}

function drawStockVolumePanel(ctx, visible, xFor, candleWidth, padLeft, padRight, top, panelHeight, width, activeIndex = visible.length - 1) {
  const maxVolume = Math.max(...visible.map((bar) => bar.volume), 1);
  const chartRight = width - padRight;
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(padLeft, top, chartRight - padLeft, panelHeight);
  ctx.strokeStyle = "#e6e8eb";
  ctx.beginPath();
  [0, 0.5, 1].forEach((ratio) => {
    const y = top + panelHeight * ratio;
    ctx.moveTo(padLeft, y);
    ctx.lineTo(chartRight, y);
  });
  ctx.stroke();
  visible.forEach((bar, index) => {
    const x = xFor(index);
    const up = bar.close >= bar.open;
    const barHeight = (bar.volume / maxVolume) * (panelHeight - 16);
    ctx.fillStyle = up ? "#e23b22" : "#059447";
    ctx.fillRect(x - candleWidth / 2, top + panelHeight - barHeight, candleWidth, Math.max(barHeight, 1));
  });
  ctx.fillStyle = "#ff263d";
  ctx.font = "900 14px system-ui";
  ctx.textAlign = "left";
  ctx.fillText(`VOLUME: ${formatShareVolume(visible[activeIndex]?.volume)}`, padLeft + 8, top + 18);
  ctx.fillStyle = "#555b62";
  ctx.font = "700 13px system-ui";
  ctx.textAlign = "left";
  [[maxVolume, 0], [maxVolume / 2, 0.5], [0, 1]].forEach(([value, ratio]) => {
    ctx.fillText(formatShareVolume(value), chartRight + 12, top + panelHeight * ratio);
  });
}

function drawStockMacdPanel(ctx, allBars, visibleLength, xFor, padLeft, padRight, top, panelHeight, width, activeIndex = visibleLength - 1) {
  const macd = computeMacd(allBars.map((bar) => bar.close));
  const visibleMacd = macd.slice(-visibleLength);
  const values = visibleMacd.flatMap((item) => [item.dif, item.dea, item.hist]);
  const maxAbs = Math.max(...values.map((value) => Math.abs(value)).filter(Number.isFinite), 0.01);
  const yMacd = (value) => top + panelHeight / 2 - (value / maxAbs) * (panelHeight / 2 - 8);
  const chartRight = width - padRight;
  ctx.strokeStyle = "#e6e8eb";
  ctx.beginPath();
  ctx.moveTo(padLeft, top + panelHeight / 2);
  ctx.lineTo(chartRight, top + panelHeight / 2);
  ctx.stroke();
  visibleMacd.forEach((item, index) => {
    const x = xFor(index);
    const y = yMacd(item.hist);
    const zero = yMacd(0);
    ctx.strokeStyle = item.hist >= 0 ? "#e23b22" : "#059447";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(x, zero);
    ctx.lineTo(x, y);
    ctx.stroke();
  });
  drawIndicatorLine(ctx, visibleMacd.map((item) => item.dif), xFor, yMacd, "#5f6368", 1.8);
  drawIndicatorLine(ctx, visibleMacd.map((item) => item.dea), xFor, yMacd, "#8a17ff", 1.8);
  const last = visibleMacd[activeIndex] ?? visibleMacd.at(-1);
  ctx.font = "900 14px system-ui";
  ctx.textAlign = "left";
  let legendX = padLeft + 10;
  legendX = drawCanvasText(ctx, `MACD: ${formatAxisNumber(last?.hist)}`, legendX, top + 18, "#ff263d", "900 14px system-ui") + 12;
  legendX = drawCanvasText(ctx, `DIF: ${formatAxisNumber(last?.dif)}`, legendX, top + 18, "#5f6368", "900 14px system-ui") + 12;
  drawCanvasText(ctx, `DEA: ${formatAxisNumber(last?.dea)}`, legendX, top + 18, "#8a17ff", "900 14px system-ui");
  ctx.fillStyle = "#555b62";
  ctx.font = "700 13px system-ui";
  ctx.textAlign = "left";
  ctx.fillText(formatAxisNumber(maxAbs), chartRight + 12, top + 6);
  ctx.fillText("0.00", chartRight + 12, top + panelHeight / 2 + 5);
  ctx.fillText(formatAxisNumber(-maxAbs), chartRight + 12, top + panelHeight - 2);
}

function drawStockXAxis(ctx, visible, xFor, axisY, width, padLeft, padRight) {
  ctx.fillStyle = "#555b62";
  ctx.font = "800 13px system-ui";
  ctx.textBaseline = "alphabetic";
  if (width < 640) {
    ctx.textAlign = "left";
    ctx.fillText(longTradeDate(visible[0]?.date), padLeft, axisY);
    ctx.textAlign = "right";
    ctx.fillText(longTradeDate(visible.at(-1)?.date), width - padRight, axisY);
    return;
  }
  const count = Math.min(4, visible.length);
  for (let index = 0; index < count; index += 1) {
    const itemIndex = Math.round((visible.length - 1) * (index / Math.max(count - 1, 1)));
    const bar = visible[itemIndex];
    if (itemIndex === 0) {
      ctx.textAlign = "left";
      ctx.fillText(longTradeDate(bar.date), padLeft, axisY);
    } else if (itemIndex === visible.length - 1) {
      ctx.textAlign = "right";
      ctx.fillText(longTradeDate(bar.date), width - padRight, axisY);
    } else {
      ctx.textAlign = "center";
      ctx.fillText(longTradeDate(bar.date), xFor(itemIndex), axisY);
    }
  }
}

function drawStockChartLegend(ctx, visible, allBars, summary, padLeft, priceTop, width, activeIndex = visible.length - 1, maSeries = []) {
  const latest = visible[activeIndex] ?? visible.at(-1);
  const metrics = stockKlineBarMetrics(allBars, visible, activeIndex, summary);
  ctx.textAlign = "left";
  ctx.textBaseline = "alphabetic";
  const change = metrics.change;
  const changePct = metrics.changePct;
  const isNarrow = width < 640;
  const legendY = Math.max(22, priceTop - (isNarrow ? 54 : 34));
  const secondLineY = legendY + 20;
  const maY = isNarrow ? secondLineY + 20 : Math.max(legendY + 20, priceTop - 13);
  const labelFont = "850 15px system-ui";
  const valueFont = "950 15px system-ui";
  let x = padLeft + 6;
  x = drawCanvasText(ctx, `${longTradeDate(latest.date)} `, x, legendY, "#18202a", "950 16px system-ui");
  x = drawCanvasText(ctx, "开 ", x, legendY, "#4e5a64", labelFont);
  x = drawCanvasText(ctx, `${formatAxisNumber(latest.open)}  `, x, legendY, "#059447", valueFont);
  x = drawCanvasText(ctx, "高 ", x, legendY, "#4e5a64", labelFont);
  x = drawCanvasText(ctx, `${formatAxisNumber(latest.high)}  `, x, legendY, "#e23b22", valueFont);
  if (isNarrow) {
    x = padLeft + 6;
  }
  x = drawCanvasText(ctx, "低 ", x, isNarrow ? secondLineY : legendY, "#4e5a64", labelFont);
  x = drawCanvasText(ctx, `${formatAxisNumber(latest.low)}  `, x, isNarrow ? secondLineY : legendY, "#059447", valueFont);
  x = drawCanvasText(ctx, "收 ", x, isNarrow ? secondLineY : legendY, "#4e5a64", labelFont);
  x = drawCanvasText(ctx, `${formatAxisNumber(latest.close)}  `, x, isNarrow ? secondLineY : legendY, "#e23b22", valueFont);
  x = drawCanvasText(ctx, "涨跌 ", x, isNarrow ? secondLineY : legendY, "#4e5a64", labelFont);
  x = drawCanvasText(ctx, `${formatSignedNumber(change, 2)}  `, x, isNarrow ? secondLineY : legendY, change >= 0 ? "#e23b22" : "#059447", valueFont);
  if (!isNarrow) {
    x = drawCanvasText(ctx, "涨跌幅 ", x, legendY, "#4e5a64", labelFont);
    drawCanvasText(ctx, Number.isFinite(changePct) ? formatSignedNumber(changePct, 2, "%") : "暂无", x, legendY, changePct >= 0 ? "#e23b22" : "#059447", valueFont);
  }

  let maX = padLeft + 6;
  maSeries.forEach((config) => {
    maX = drawCanvasText(ctx, `${config.label} ${formatAxisNumber(config.values[metrics.globalIndex])}  `, maX, maY, config.color, valueFont);
  });
}

function drawPriceMarker(ctx, padLeft, chartRight, yFor, value, label, color, kind = "", occupiedSlots = []) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return;
  const y = yFor(numeric);
  ctx.save();
  ctx.strokeStyle = color;
  ctx.lineWidth = kind === "current" ? 1.5 : 1.2;
  ctx.setLineDash(kind === "current" ? [9, 9] : [5, 4]);
  ctx.beginPath();
  ctx.moveTo(padLeft, y);
  ctx.lineTo(chartRight, y);
  ctx.stroke();
  ctx.setLineDash([]);

  const text = label || formatAxisNumber(numeric);
  ctx.font = "900 14px system-ui";
  const labelWidth = Math.max(54, ctx.measureText(text).width + 14);
  const x = chartRight + 6;
  const h = 24;
  const canvasHeight = ctx.canvas?.getBoundingClientRect?.().height || ctx.canvas?.height || 720;
  const minY = 18;
  const maxY = canvasHeight - h - 6;
  let labelY = Math.max(minY, Math.min(y - h / 2, maxY));
  for (let attempt = 0; attempt < 4; attempt += 1) {
    const conflict = occupiedSlots.find((slot) => labelY < slot.y + slot.h + 4 && labelY + h + 4 > slot.y);
    if (!conflict) break;
    const nextY = conflict.y + conflict.h + 4;
    const previousY = conflict.y - h - 4;
    labelY = nextY <= maxY ? nextY : Math.max(minY, previousY);
  }
  occupiedSlots.push({ y: labelY, h });
  ctx.fillStyle = kind === "support" ? "#f5fff0" : kind === "current" ? "#ff263d" : "#111111";
  ctx.strokeStyle = kind === "support" ? color : "#ff263d";
  roundedRectPath(ctx, x, labelY, labelWidth, h, 7);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = kind === "support" ? color : "#ffffff";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text, x + labelWidth / 2, labelY + h / 2 + 0.5);
  ctx.restore();
}

function drawCanvasText(ctx, text, x, y, color, font) {
  ctx.save();
  ctx.fillStyle = color;
  ctx.font = font;
  ctx.lineJoin = "round";
  ctx.lineWidth = 3;
  ctx.strokeStyle = "rgba(255, 255, 255, 0.92)";
  ctx.strokeText(text, x, y);
  ctx.fillText(text, x, y);
  const nextX = x + ctx.measureText(text).width;
  ctx.restore();
  return nextX;
}

function roundedRectPath(ctx, x, y, width, height, radius) {
  const r = Math.min(radius, width / 2, height / 2);
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + width - r, y);
  ctx.quadraticCurveTo(x + width, y, x + width, y + r);
  ctx.lineTo(x + width, y + height - r);
  ctx.quadraticCurveTo(x + width, y + height, x + width - r, y + height);
  ctx.lineTo(x + r, y + height);
  ctx.quadraticCurveTo(x, y + height, x, y + height - r);
  ctx.lineTo(x, y + r);
  ctx.quadraticCurveTo(x, y, x + r, y);
  ctx.closePath();
}

function drawIndicatorLine(ctx, values, xFor, yFor, color, width = 2) {
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.beginPath();
  let hasPoint = false;
  values.forEach((value, index) => {
    if (!Number.isFinite(Number(value))) {
      return;
    }
    const x = xFor(index);
    const y = yFor(Number(value));
    if (!hasPoint) {
      ctx.moveTo(x, y);
      hasPoint = true;
    } else {
      ctx.lineTo(x, y);
    }
  });
  if (hasPoint) ctx.stroke();
}

function movingAverage(values, windowSize) {
  const result = [];
  let sum = 0;
  values.forEach((value, index) => {
    sum += Number(value);
    if (index >= windowSize) sum -= Number(values[index - windowSize]);
    result.push(index >= windowSize - 1 ? sum / windowSize : null);
  });
  return result;
}

function computeMacd(values) {
  const ema12 = ema(values, 12);
  const ema26 = ema(values, 26);
  const dif = values.map((_, index) => ema12[index] - ema26[index]);
  const dea = ema(dif, 9);
  return values.map((_, index) => ({
    dif: dif[index],
    dea: dea[index],
    hist: (dif[index] - dea[index]) * 2
  }));
}

function ema(values, period) {
  const multiplier = 2 / (period + 1);
  const result = [];
  let previous = Number(values[0] ?? 0);
  values.forEach((raw, index) => {
    const value = Number(raw);
    previous = index === 0 ? value : value * multiplier + previous * (1 - multiplier);
    result.push(previous);
  });
  return result;
}

function shortTradeDate(value) {
  const text = String(value ?? "");
  if (text.length >= 10) return text.slice(5, 10);
  return text;
}

function longTradeDate(value) {
  const text = String(value ?? "");
  if (text.length >= 10) return text.slice(0, 10);
  return text || "暂无日期";
}

function formatAxisNumber(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "暂无";
  if (Math.abs(numeric) >= 1000) return numeric.toFixed(0);
  if (Math.abs(numeric) >= 100) return numeric.toFixed(1);
  return numeric.toFixed(2);
}

function renderHealth() {
  if (!healthGrid) return;
  healthGrid.innerHTML = buildHealthSources().map((item) => `
    <article
      class="health-card ${item.kind === sourceTestKindFilter ? "active" : ""}"
      data-health-kind="${escapeHTML(item.kind)}"
      role="button"
      tabindex="0"
    >
      <div class="health-top">
        <strong>${escapeHTML(item.name)}</strong>
        <span class="freshness-badge ${item.status}">${statusText(item.status)}</span>
      </div>
      <p class="confidence">${escapeHTML(item.source)}</p>
      <p>${escapeHTML(item.text)}</p>
    </article>
  `).join("");
}

function buildHealthSources() {
  return healthSourceKinds.map((config) => {
    const sources = sourcesForKind(config.kind);
    const active = sources.filter((source) => source.active);
    const enabled = sources.filter((source) => source.enabled);
    const tests = (sourceTestCatalog?.tests ?? []).filter((test) => test.source_kind === config.kind);
    const activeTests = tests.filter((test) => test.active);
    const status = active.length ? "fresh" : enabled.length ? "warn" : "stale";
    const providerText = active.length
      ? active.map((source) => source.label).join("、")
      : enabled.length
        ? `${enabled.map((source) => source.label).join("、")} 需配置`
        : "未启用";
    const sourceText = `${providerText} · ${active.length}/${sources.length || 0} 已生效`;
    const testText = tests.length ? `${activeTests.length}/${tests.length} 项可测试` : "等待测试清单";
    return {
      ...config,
      status,
      source: sourceText,
      text: `${config.text} ${testText}。`
    };
  });
}

function sourcesForKind(kind, market = "") {
  return currentDataSources().filter((source) => {
    if (source.source_kind !== kind) return false;
    return !market || source.market === market;
  });
}

function activeSourceLabelsForKind(kind, market = "") {
  return sourcesForKind(kind, market)
    .filter((source) => source.active)
    .map((source) => source.label);
}

function currentDataSources() {
  return dataSources.length ? dataSources : fallbackDataSources;
}

function sourceReliability(source) {
  const item = source?.reliability ?? (source?.id === "cn-xueqiu-community"
    ? {
      source_id: "cn-xueqiu-community",
      method: "community_crawl_runs",
      total: 1,
      successes: 0,
      failures: 1,
      success_rate: 0,
      failure_rate: 100,
      latest_error: "雪球评论还没有最近成功刷新任务，当前按 0% 成功率处理",
      note: "雪球评论需最近刷新任务成功后才计入成功率"
    }
    : {});
  const successRate = item.success_rate === null || item.success_rate === undefined || item.success_rate === ""
    ? NaN
    : Number(item.success_rate);
  const failureRate = item.failure_rate === null || item.failure_rate === undefined || item.failure_rate === ""
    ? NaN
    : Number(item.failure_rate);
  return {
    ...item,
    total: Number(item.total || 0),
    successes: Number(item.successes || 0),
    failures: Number(item.failures || 0),
    successRate: Number.isFinite(successRate) ? successRate : null,
    failureRate: Number.isFinite(failureRate) ? failureRate : null,
    latestError: String(item.latest_error ?? ""),
    note: String(item.note ?? "")
  };
}

function formatReliabilityRate(value) {
  if (!Number.isFinite(value)) return "暂无";
  return `${Number.isInteger(value) ? value.toFixed(0) : value.toFixed(1)}%`;
}

function sourceReliabilityTone(reliability) {
  if (!reliability.total) return "stale";
  if (reliability.failures > 0 || reliability.successRate === 0) return "warn";
  return "fresh";
}

function sourceNeedsAttention(source) {
  const reliability = sourceReliability(source);
  return reliability.total > 0 && (reliability.failures > 0 || reliability.successRate === 0);
}

function renderSourceReliability(source) {
  const reliability = sourceReliability(source);
  const tone = sourceReliabilityTone(reliability);
  const successWidth = Number.isFinite(reliability.successRate)
    ? Math.max(0, Math.min(100, reliability.successRate))
    : 0;
  const note = reliability.latestError || reliability.note || "暂无刷新记录";
  return `
    <div class="source-reliability ${tone}" aria-label="${escapeHTML(source.label)} 刷新成功率">
      <div>
        <span>刷新成功率</span>
        <strong>${formatReliabilityRate(reliability.successRate)}</strong>
      </div>
      <div>
        <span>失败率</span>
        <strong>${formatReliabilityRate(reliability.failureRate)}</strong>
      </div>
      <div class="source-reliability-track"><span style="width: ${successWidth}%"></span></div>
      <p>${escapeHTML(note)}</p>
    </div>
  `;
}

function sourceNotificationItems() {
  return currentDataSources()
    .map((source) => ({ source, reliability: sourceReliability(source) }))
    .filter(({ reliability }) => reliability.total > 0 && (reliability.failures > 0 || reliability.successRate === 0))
    .sort((left, right) => {
      const failureDelta = Number(right.reliability.failureRate ?? -1) - Number(left.reliability.failureRate ?? -1);
      if (failureDelta) return failureDelta;
      return String(left.source.label).localeCompare(String(right.source.label), "zh-CN");
    });
}

function setSourceNotificationsOpen(open) {
  sourceNotificationsOpen = Boolean(open);
  if (sourceNotificationPanel) sourceNotificationPanel.hidden = !sourceNotificationsOpen;
  if (sourceNotificationButton) sourceNotificationButton.setAttribute("aria-expanded", sourceNotificationsOpen ? "true" : "false");
}

function renderSourceNotifications() {
  if (!sourceNotificationButton || !sourceNotificationCount || !sourceNotificationPanel || !sourceNotificationSummary || !sourceNotificationList) return;
  const items = sourceNotificationItems();
  const trackedCount = currentDataSources().filter((source) => sourceReliability(source).total > 0).length;
  sourceNotificationButton.classList.toggle("has-alerts", items.length > 0);
  sourceNotificationCount.hidden = items.length === 0;
  sourceNotificationCount.textContent = String(items.length);
  sourceNotificationSummary.textContent = items.length
    ? `${items.length} 个数据源需复核`
    : trackedCount
      ? `${trackedCount} 个数据源暂无失败`
      : "暂无刷新记录";
  sourceNotificationList.innerHTML = items.length
    ? items.map(({ source, reliability }) => `
        <button class="notification-item" type="button" data-open-source="${escapeHTML(source.id)}">
          <span>
            <strong>${escapeHTML(source.label)}</strong>
            <small>${escapeHTML(providerDisplayName(source.provider))} · ${escapeHTML(reliability.latestError || reliability.note || "最近刷新失败")}</small>
          </span>
          <em>${formatReliabilityRate(reliability.successRate)}</em>
        </button>
      `).join("")
    : `<div class="notification-empty">所有已跟踪数据源暂无失败记录。</div>`;
  setSourceNotificationsOpen(sourceNotificationsOpen);
}

function renderDataSources() {
  if (!dataSourceGrid) return;
  const sources = currentDataSources();
  const grouped = sources.reduce((map, source) => {
    const market = source.market;
    if (!map.has(market)) map.set(market, []);
    map.get(market).push(source);
    return map;
  }, new Map());
  const activeCount = sources.filter((source) => source.active).length;
  const attentionCount = sources.filter(sourceNeedsAttention).length;
  if (sourceSettingsStatus) {
    sourceSettingsStatus.textContent = apiState.connected && attentionCount
      ? `异常 ${attentionCount} 个 · ${activeCount}/${sources.length} 已生效`
      : apiState.connected
      ? `${activeCount}/${sources.length} 已生效`
      : "本地 fallback";
  }
  dataSourceGrid.innerHTML = [...grouped.entries()].map(([market, items]) => `
    <section class="source-market-group">
      <div class="source-market-head">
        <h4>${marketLabels[market] ?? market}</h4>
        <span class="confidence">${items.filter((item) => item.active).length}/${items.length} 个数据源已生效</span>
      </div>
      <div class="source-card-grid">
        ${items.map(renderSourceCard).join("")}
      </div>
    </section>
  `).join("");
}

function renderSourceCard(source) {
  const active = source.enabled && source.configured;
  const needsConfig = source.enabled && source.requires_key && !source.configured;
  const status = active ? "已生效" : needsConfig ? "需配置 API" : source.enabled ? "已勾选" : "未使用";
  const statusClass = active ? "fresh" : needsConfig ? "warn" : "stale";
  const cardClass = active ? "active" : needsConfig ? "needs-config" : "";
  const placeholder = source.requires_key
    ? (source.credential_hint ? `已配置 ${source.credential_hint}` : source.credential_label)
    : source.credential_label;
  return `
    <article class="source-card ${cardClass}" data-source-card="${escapeHTML(source.id)}">
      <div class="source-top">
        <div class="source-title">
          <strong>${escapeHTML(source.label)}</strong>
          <span>${escapeHTML(providerDisplayName(source.provider))} · ${escapeHTML(source.source_kind_label ?? sourceKindLabels[source.source_kind] ?? source.source_kind)}</span>
        </div>
        <label class="source-toggle">
          <input type="checkbox" data-source-enabled="${source.id}" ${source.enabled ? "checked" : ""} />
          <span>使用</span>
        </label>
      </div>
      <div class="source-fields">
        <label>
          <span>${escapeHTML(source.credential_label)}</span>
          <input data-source-key="${source.id}" type="${source.requires_key ? "password" : "text"}" placeholder="${escapeHTML(placeholder)}" ${source.requires_key ? "" : "disabled"} />
        </label>
        <button class="primary-action" data-source-save="${source.id}" type="button">保存配置</button>
        ${["akshare", "baostock", "baostock-financial", "cninfo_sse_szse", "cninfo", "sse", "szse", "tushare", "finnhub", "xueqiu"].includes(source.provider) ? `<button class="ghost-action small" data-source-refresh="${escapeHTML(source.provider)}" type="button">刷新数据</button>` : ""}
      </div>
      ${renderSourceReliability(source)}
      <div class="source-meta">
        <span class="status-chip ${statusClass}">${status}</span>
        <span class="status-chip verified">${escapeHTML(source.source_kind_label ?? source.source_kind)}</span>
      </div>
    </article>
  `;
}

function renderSourceTests() {
  if (!sourceTestStatus || !sourceTestSelect || !sourceTestList || !sourceTestParams || !sourceTestResult) return;

  if (!apiState.connected) {
    sourceTestStatus.textContent = "后端未连接";
    sourceTestSelect.innerHTML = "";
    sourceTestList.innerHTML = `<p class="empty-state compact">启动本地后端后可测试真实数据源。</p>`;
    sourceTestParams.innerHTML = "";
    sourceTestResult.innerHTML = "";
    return;
  }

  if (!sourceTestCatalog) {
    sourceTestStatus.textContent = "加载失败";
    sourceTestSelect.innerHTML = "";
    sourceTestList.innerHTML = `<p class="empty-state compact">${escapeHTML(sourceTestError || "数据源测试清单不可用。")}</p>`;
    sourceTestParams.innerHTML = "";
    sourceTestResult.innerHTML = "";
    return;
  }

  const allTests = sourceTestCatalog.tests ?? [];
  const tests = sourceTestKindFilter
    ? allTests.filter((item) => item.source_kind === sourceTestKindFilter)
    : allTests;
  if (tests.length && !tests.some((item) => item.id === selectedSourceTestId)) {
    selectedSourceTestId = tests[0].id;
    sourceTestPayload = null;
    sourceTestError = "";
    if (sourceTestSymbol) sourceTestSymbol.value = "";
  }
  const activeCount = tests.filter((item) => item.active).length;
  const testKindLabel = sourceKindLabels[sourceTestKindFilter] ?? "全部";
  sourceTestStatus.textContent = `${testKindLabel} · ${activeCount}/${tests.length} 可测试`;

  sourceTestSelect.innerHTML = tests.map((test) => `
    <option value="${escapeHTML(test.id)}" ${test.id === selectedSourceTestId ? "selected" : ""}>
      ${escapeHTML(displayText(test.label))}
    </option>
  `).join("");

  const grouped = tests.reduce((map, test) => {
    const group = sourceTestKindFilter
      ? (marketLabels[test.market] ?? test.market ?? "其他")
      : (test.source_kind_label || test.source_kind || "其他");
    if (!map.has(group)) map.set(group, []);
    map.get(group).push(test);
    return map;
  }, new Map());
  sourceTestList.innerHTML = tests.length
    ? [...grouped.entries()].map(([group, items]) => `
      <section class="source-test-group">
        <h4>${escapeHTML(displayText(group))}</h4>
        ${items.map(renderSourceTestItem).join("")}
      </section>
    `).join("")
    : `<p class="empty-state compact">当前板块没有可用测试项。</p>`;

  renderSourceTestForm();
  renderSourceTestResult();
}

function renderSourceTestItem(test) {
  const selected = test.id === selectedSourceTestId;
  const statusClass = test.active ? "fresh" : test.implemented ? "warn" : "stale";
  return `
    <button class="source-test-item ${selected ? "active" : ""}" data-source-test-id="${escapeHTML(test.id)}" type="button">
      <span>
        <strong>${escapeHTML(displayText(test.label))}</strong>
        <small>${escapeHTML(providerDisplayName(test.provider))} · ${escapeHTML(marketLabels[test.market] ?? test.market ?? "")}</small>
      </span>
      <em class="${statusClass}">${escapeHTML(displayText(test.status))}</em>
    </button>
  `;
}

function renderSourceTestForm() {
  const test = selectedSourceTest();
  if (!test || !sourceTestSymbol || !sourceTestParams) return;
  if (!sourceTestSymbol.value || sourceTestSymbol.dataset.testDefaultFor !== test.id) {
    sourceTestSymbol.value = test.default_symbol ?? "";
    sourceTestSymbol.dataset.testDefaultFor = test.id;
  }
  sourceTestParams.innerHTML = (test.params ?? []).map((param) => {
    const type = param.kind === "date" ? "date" : param.kind === "int" || param.kind === "float" ? "number" : "search";
    const step = param.kind === "float" ? "0.01" : "1";
    return `
      <label>
        <span>${escapeHTML(param.label ?? param.name)}</span>
        <input
          data-source-test-param="${escapeHTML(param.name)}"
          data-source-test-kind="${escapeHTML(param.kind ?? "str")}"
          type="${type}"
          step="${step}"
          value="${escapeHTML(param.default ?? "")}"
        />
      </label>
    `;
  }).join("");
  renderSearchHistories();
}

function renderSourceTestResult() {
  if (!sourceTestResult) return;
  if (sourceTestLoading) {
    sourceTestResult.innerHTML = `<p class="empty-state compact">正在测试数据源...</p>`;
    return;
  }
  if (sourceTestError) {
    sourceTestResult.innerHTML = `<p class="empty-state compact">${escapeHTML(sourceTestError)}</p>`;
    return;
  }
  if (!sourceTestPayload) {
    const test = selectedSourceTest();
    sourceTestResult.innerHTML = test
      ? `
        <div class="source-test-empty">
          <strong>${escapeHTML(test.label)}</strong>
          <p>${escapeHTML(displayText(test.description ?? ""))}</p>
        </div>
      `
      : `<p class="empty-state compact">请选择数据源。</p>`;
    return;
  }

  const result = sourceTestPayload.result ?? {};
  const rows = Array.isArray(result.rows) ? result.rows : [];
  const columns = result.columns?.length ? result.columns : Object.keys(rows[0] ?? {});
  const visibleColumns = columns.slice(0, 10);
  const errorList = Array.isArray(result.errors) ? result.errors : [];
  const errorHtml = errorList.length
    ? `
      <div class="source-test-error-list">
        ${errorList.map((item) => `<span>${escapeHTML(displayCellValue(item.source ?? "source", "source"))}：${escapeHTML(displayText(item.message ?? item.error ?? ""))}</span>`).join("")}
      </div>
    `
    : "";
  const table = rows.length
    ? `
      <div class="table-wrap source-test-table-wrap">
        <table>
          <thead>
            <tr>${visibleColumns.map((column) => `<th>${escapeHTML(displayColumnLabel(column))}</th>`).join("")}</tr>
          </thead>
          <tbody>
            ${rows.slice(0, 12).map((row) => `
              <tr>${visibleColumns.map((column) => renderResultCell(row?.[column], column, row)).join("")}</tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    `
    : `<p class="empty-state compact">本次调用没有表格行。</p>`;

  sourceTestResult.innerHTML = `
    <div class="source-test-result-head">
      <div>
        <strong>${escapeHTML(displayText(sourceTestPayload.test?.label ?? "数据源测试结果"))}</strong>
        <p>${escapeHTML(sourceTestPayload.request?.symbol ?? "")} · ${escapeHTML(providerDisplayName(sourceTestPayload.test?.provider ?? ""))}</p>
      </div>
      <span class="count-pill">${result.returned_rows ?? rows.length}/${result.total_rows ?? rows.length} 行</span>
    </div>
    ${errorHtml}
    ${table}
    <details class="source-test-raw">
      <summary>原始 JSON</summary>
      <pre>${escapeHTML(JSON.stringify(sourceTestPayload, null, 2))}</pre>
    </details>
  `;
}

function renderResultCell(value, column = "", row = null) {
  const text = value === null || value === undefined ? "" : String(value);
  const href = text.startsWith("http://") || text.startsWith("https://");
  const display = displayCellValue(value, column);
  const linkedTitle = normalizeFieldKey(column) === "title" ? rowExternalUrl(row) : "";
  if (linkedTitle && display) {
    return `<td><a class="source-text-link result-cell-clamp" href="${escapeHTML(linkedTitle)}" target="_blank" rel="noreferrer" title="${escapeHTML(display)}">${escapeHTML(display)}</a></td>`;
  }
  return href
    ? `<td><a class="source-link" href="${escapeHTML(text)}" target="_blank" rel="noreferrer">打开</a></td>`
    : `<td><div class="result-cell-clamp" title="${escapeHTML(display)}">${escapeHTML(display)}</div></td>`;
}

function rowExternalUrl(row) {
  if (!row || typeof row !== "object") return "";
  for (const key of ["url", "href", "link", "source_url", "document_url"]) {
    const value = row[key];
    if (typeof value === "string" && (value.startsWith("http://") || value.startsWith("https://"))) {
      return value;
    }
  }
  return "";
}

function selectedSourceTest() {
  const tests = sourceTestKindFilter
    ? (sourceTestCatalog?.tests ?? []).filter((item) => item.source_kind === sourceTestKindFilter)
    : (sourceTestCatalog?.tests ?? []);
  return tests.find((item) => item.id === selectedSourceTestId);
}

function sourceTestParamPayload() {
  const payload = {};
  sourceTestParams?.querySelectorAll("[data-source-test-param]").forEach((input) => {
    const key = input.dataset.sourceTestParam;
    const kind = input.dataset.sourceTestKind;
    if (!key) return;
    if (kind === "int") payload[key] = input.value ? Number.parseInt(input.value, 10) : "";
    else if (kind === "float") payload[key] = input.value ? Number.parseFloat(input.value) : "";
    else payload[key] = input.value.trim();
  });
  return payload;
}

async function runSourceTest() {
  const test = selectedSourceTest();
  if (!test) return;
  sourceTestLoading = true;
  sourceTestError = "";
  sourceTestPayload = null;
  renderSourceTestResult();
  try {
    sourceTestPayload = await apiRequest("/api/data-source-tests/run", {
      method: "POST",
      body: JSON.stringify({
        test_id: test.id,
        symbol: sourceTestSymbol?.value.trim() || test.default_symbol || "",
        account_id: apiState.accountId,
        params: sourceTestParamPayload()
      })
    });
    sourceTestError = "";
    await loadSearchHistory();
  } catch (error) {
    sourceTestError = `数据源测试失败：${error.message}`;
  } finally {
    sourceTestLoading = false;
    renderSourceTestResult();
  }
}

function selectHealthKind(kind) {
  if (!healthSourceKinds.some((item) => item.kind === kind)) return;
  sourceTestKindFilter = kind;
  sourceTestPayload = null;
  sourceTestError = "";
  if (sourceTestSymbol) sourceTestSymbol.value = "";
  renderHealth();
  renderSourceTests();
}

function renderAkshareExplorer() {
  if (!akshareStatus || !akshareCapabilityTabs || !akshareCapabilityGrid || !aksharePreview) return;
  syncAkshareExplorerChrome();

  if (!apiState.connected) {
    akshareStatus.textContent = "后端未连接";
    akshareStatus.className = "status-chip warn";
    akshareCapabilityTabs.innerHTML = "";
    akshareCapabilityGrid.innerHTML = `<p class="empty-state compact">启动本地后端后可查看 AKShare 能力清单。</p>`;
    aksharePreview.innerHTML = "";
    return;
  }

  if (!aksharePayload) {
    akshareStatus.textContent = "加载失败";
    akshareStatus.className = "status-chip warn";
    akshareCapabilityTabs.innerHTML = "";
    akshareCapabilityGrid.innerHTML = `<p class="empty-state compact">${escapeHTML(aksharePreviewError || "AKShare 能力清单不可用。")}</p>`;
    aksharePreview.innerHTML = "";
    return;
  }

  const installed = Boolean(aksharePayload.status?.installed);
  const total = aksharePayload.summary?.total ?? 0;
  const available = aksharePayload.summary?.available ?? 0;
  akshareStatus.textContent = installed
    ? `AKShare ${aksharePayload.status?.version ?? ""} · ${available}/${total} 可用`
    : "未安装 AKShare";
  akshareStatus.className = `status-chip ${installed ? "fresh" : "warn"}`;
  akshareStatus.title = aksharePayload.status?.note ?? "";

  const groups = aksharePayload.groups ?? [];
  akshareCapabilityTabs.innerHTML = groups.map((group) => `
    <button class="akshare-tab ${group.id === activeAkshareCategory ? "active" : ""}" data-ak-category="${group.id}" type="button">
      ${escapeHTML(group.label)} <span>${group.count}</span>
    </button>
  `).join("");

  const capabilities = (aksharePayload.capabilities ?? []).filter((item) => item.category === activeAkshareCategory);
  akshareCapabilityGrid.innerHTML = capabilities.length
    ? capabilities.map(renderAkshareCapabilityCard).join("")
    : `<p class="empty-state compact">当前分类没有已登记能力。</p>`;

  renderAksharePreview();
}

function syncAkshareExplorerChrome() {
  if (akshareBody) akshareBody.hidden = !akshareExpanded;
  if (akshareToggle) {
    akshareToggle.textContent = akshareExpanded ? "收起" : "展开";
    akshareToggle.setAttribute("aria-expanded", String(akshareExpanded));
  }
}

function renderAkshareCapabilityCard(capability) {
  const available = capability.available;
  const statusClass = available ? "fresh" : "warn";
  const statusTextValue = available ? "当前版本可用" : "未安装或版本不含";
  const params = capability.params ?? [];

  return `
    <article class="akshare-card" data-ak-card="${capability.id}">
      <div class="akshare-card-head">
        <div>
          <strong>${escapeHTML(capability.label)}</strong>
          <span>${escapeHTML(capability.function)}</span>
        </div>
        <span class="status-chip ${statusClass}">${statusTextValue}</span>
      </div>
      <p>${escapeHTML(capability.description)}</p>
      ${params.length ? `<div class="provider-param-grid">${params.map((param) => renderAkshareParamField(capability, param)).join("")}</div>` : `<p class="akshare-card-meta">无需参数，直接获取。</p>`}
      <div class="akshare-card-actions">
        <button class="primary-action small" data-ak-fetch="${escapeHTML(capability.id)}" type="button" ${available ? "" : "disabled"}>获取数据</button>
      </div>
    </article>
  `;
}

function renderAkshareParamField(capability, param) {
  const fieldId = `ak-${capability.id}-${param.name}`;
  const defaultValue = akshareParamDefault(capability, param);
  const description = akshareParamDescription(param);
  const choices = Array.isArray(param.choices) && param.choices.length ? param.choices : [];
  const input = choices.length
    ? `
      <select id="${escapeHTML(fieldId)}" data-ak-param="${escapeHTML(param.name)}">
        ${choices.map((choice) => `<option value="${escapeHTML(choice)}" ${String(choice) === String(defaultValue) ? "selected" : ""}>${escapeHTML(choice)}</option>`).join("")}
      </select>
    `
    : `<input id="${escapeHTML(fieldId)}" data-ak-param="${escapeHTML(param.name)}" type="text" value="${escapeHTML(defaultValue)}" placeholder="${escapeHTML(param.required ? "必填" : "可选")}" />`;
  return `
    <label class="provider-param-field" for="${escapeHTML(fieldId)}">
      <span>${escapeHTML(param.name)}${param.required ? " *" : ""}</span>
      <small>${escapeHTML(description)}</small>
      ${input}
    </label>
  `;
}

function akshareParamDefault(capability, param) {
  const example = capability.examples?.[0] ?? {};
  const value = example[param.name] ?? param.default ?? akshareFallbackParamDefault(param);
  return value === null || value === undefined ? "" : String(value);
}

function akshareFallbackParamDefault(param) {
  const name = param.name;
  if (name === "period") return "daily";
  if (name === "adjust") return "qfq";
  if (name === "start_date") return "20250101";
  if (name === "end_date") return "20260605";
  if (name === "symbol") return "600519";
  return "";
}

function akshareParamDescription(param) {
  if (param.name === "period") return "周期：daily 日线，weekly 周线，monthly 月线；分钟线接口可用 1/5/15/30/60。";
  if (param.name === "adjust") return "复权方式：空值为不复权，qfq 为前复权，hfq 为后复权。";
  if (param.name === "symbol") return param.description || "股票代码，A 股通常填 6 位代码，例如 600519。";
  if (param.name === "start_date" || param.name === "end_date") return param.description || "日期，通常为 YYYYMMDD。";
  return param.description || "接口参数。";
}

function renderAksharePreview() {
  if (!aksharePreview) return;
  if (aksharePreviewLoading) {
    aksharePreview.innerHTML = `<p class="empty-state compact">正在调用 AKShare...</p>`;
    return;
  }
  if (aksharePreviewError) {
    aksharePreview.innerHTML = `<p class="empty-state compact">${escapeHTML(aksharePreviewError)}</p>`;
    return;
  }
  if (!aksharePreviewPayload) {
    aksharePreview.innerHTML = `<p class="empty-state compact">选择一个能力试跑后，这里会显示返回行数、字段和前几行数据。</p>`;
    return;
  }

  const result = aksharePreviewPayload.result ?? {};
  const capability = aksharePreviewPayload.capability ?? {};
  const rows = Array.isArray(result.rows) ? result.rows : [];
  const columns = result.columns?.length ? result.columns : Object.keys(rows[0] ?? {});
  const visibleColumns = columns.slice(0, 8);
  const rowHtml = rows.slice(0, 8).map((row) => `
    <tr>
      ${visibleColumns.map((column) => renderResultCell(row?.[column], column, row)).join("")}
    </tr>
  `).join("");

  const table = rows.length
    ? `
      <div class="table-wrap akshare-table-wrap">
        <table>
          <thead>
            <tr>${visibleColumns.map((column) => `<th>${escapeHTML(displayColumnLabel(column))}</th>`).join("")}</tr>
          </thead>
          <tbody>${rowHtml}</tbody>
        </table>
      </div>
    `
    : `<p class="empty-state compact">本次调用没有表格行，返回类型：${escapeHTML(result.type ?? "unknown")}</p>`;

  aksharePreview.innerHTML = `
    <div class="akshare-preview-head">
      <div>
        <strong>${escapeHTML(capability.label ?? "AKShare 结果")}</strong>
        <p>${escapeHTML(displayText(capability.function ?? ""))} · ${escapeHTML(aksharePreviewPayload.fetched_at ?? "")}</p>
      </div>
      <span class="count-pill">${result.returned_rows ?? 0}/${result.total_rows ?? 0} 行</span>
    </div>
    ${table}
  `;
}

function renderAlphaVantageExplorer() {
  if (!alphaVantageStatus || !alphaVantageCapabilityTabs || !alphaVantageCapabilityGrid || !alphaVantagePreview) return;

  if (!apiState.connected) {
    alphaVantageStatus.textContent = "后端未连接";
    alphaVantageStatus.className = "status-chip warn";
    alphaVantageCapabilityTabs.innerHTML = "";
    alphaVantageCapabilityGrid.innerHTML = `<p class="empty-state compact">启动本地后端后可查看 Alpha Vantage 能力清单。</p>`;
    alphaVantagePreview.innerHTML = "";
    return;
  }

  if (!alphaVantagePayload) {
    alphaVantageStatus.textContent = "加载失败";
    alphaVantageStatus.className = "status-chip warn";
    alphaVantageCapabilityTabs.innerHTML = "";
    alphaVantageCapabilityGrid.innerHTML = `<p class="empty-state compact">${escapeHTML(alphaVantagePreviewError || "Alpha Vantage 能力清单不可用。")}</p>`;
    alphaVantagePreview.innerHTML = "";
    return;
  }

  const configured = Boolean(alphaVantagePayload.status?.configured);
  const total = alphaVantagePayload.summary?.total ?? 0;
  const available = alphaVantagePayload.summary?.available ?? 0;
  const hint = alphaVantagePayload.status?.credential_hint ? ` · ${alphaVantagePayload.status.credential_hint}` : "";
  alphaVantageStatus.textContent = configured
    ? `Alpha Vantage 已配置${hint} · ${available}/${total} 可用`
    : "未配置 Alpha Vantage key";
  alphaVantageStatus.className = `status-chip ${configured ? "fresh" : "warn"}`;
  alphaVantageStatus.title = alphaVantagePayload.status?.note ?? "";

  const groups = alphaVantagePayload.groups ?? [];
  alphaVantageCapabilityTabs.innerHTML = groups.map((group) => `
    <button class="akshare-tab ${group.id === activeAlphaVantageCategory ? "active" : ""}" data-av-category="${group.id}" type="button">
      ${escapeHTML(group.label)} <span>${group.count}</span>
    </button>
  `).join("");

  const capabilities = (alphaVantagePayload.capabilities ?? []).filter((item) => item.category === activeAlphaVantageCategory);
  alphaVantageCapabilityGrid.innerHTML = capabilities.length
    ? capabilities.map(renderAlphaVantageCapabilityCard).join("")
    : `<p class="empty-state compact">当前分类没有已登记能力。</p>`;

  renderAlphaVantagePreview();
}

function renderAlphaVantageCapabilityCard(capability) {
  const available = capability.available;
  const statusClass = available ? "fresh" : "warn";
  const statusTextValue = available ? "key 已配置" : "等待 key";
  const params = capability.params?.length
    ? capability.params.map((param) => `${param.name}${param.required ? "*" : ""}`).join(" / ")
    : "无需参数";
  const examples = capability.examples?.length ? capability.examples : [{}];

  return `
    <article class="akshare-card" data-av-card="${capability.id}">
      <div class="akshare-card-head">
        <div>
          <strong>${escapeHTML(capability.label)}</strong>
          <span>${escapeHTML(capability.function)}</span>
        </div>
        <span class="status-chip ${statusClass}">${statusTextValue}</span>
      </div>
      <p>${escapeHTML(capability.description)}</p>
      <div class="akshare-card-meta">
        <span>参数：${escapeHTML(params)}</span>
      </div>
      <div class="provider-example-row">
        ${examples.map((example, index) => renderProviderExampleButton("av", capability.id, example, index, available)).join("")}
      </div>
      <div class="akshare-card-actions">
        <a class="source-link" href="${escapeHTML(capability.docs_url)}" target="_blank" rel="noreferrer">文档</a>
      </div>
    </article>
  `;
}

function renderProviderExampleButton(provider, capabilityId, example, index, enabled = true) {
  const attr = provider === "ak" ? "data-ak-run" : "data-av-run";
  const exampleAttr = provider === "ak" ? "data-ak-example" : "data-av-example";
  const label = Object.keys(example).length
    ? Object.entries(example).slice(0, 3).map(([key, value]) => `${key}=${value}`).join(" · ")
    : "直接调用";
  return `
    <button class="provider-example-button" ${attr}="${escapeHTML(capabilityId)}" ${exampleAttr}="${index}" type="button" ${enabled ? "" : "disabled"}>
      <span>示例 ${index + 1}</span>
      <strong>${escapeHTML(label)}</strong>
    </button>
  `;
}

function renderAlphaVantagePreview() {
  if (!alphaVantagePreview) return;
  if (alphaVantagePreviewLoading) {
    alphaVantagePreview.innerHTML = `<p class="empty-state compact">正在调用 Alpha Vantage...</p>`;
    return;
  }
  if (alphaVantagePreviewError) {
    alphaVantagePreview.innerHTML = `<p class="empty-state compact">${escapeHTML(alphaVantagePreviewError)}</p>`;
    return;
  }
  if (!alphaVantagePreviewPayload) {
    alphaVantagePreview.innerHTML = `<p class="empty-state compact">选择一个能力试跑后，这里会显示返回行数、字段和前几行数据。</p>`;
    return;
  }

  const result = alphaVantagePreviewPayload.result ?? {};
  const capability = alphaVantagePreviewPayload.capability ?? {};
  const rows = Array.isArray(result.rows) ? result.rows : [];
  const columns = result.columns?.length ? result.columns : Object.keys(rows[0] ?? {});
  const visibleColumns = columns.slice(0, 8);
  const rowHtml = rows.slice(0, 8).map((row) => `
    <tr>
      ${visibleColumns.map((column) => renderResultCell(row?.[column], column, row)).join("")}
    </tr>
  `).join("");

  const table = rows.length
    ? `
      <div class="table-wrap akshare-table-wrap">
        <table>
          <thead>
            <tr>${visibleColumns.map((column) => `<th>${escapeHTML(displayColumnLabel(column))}</th>`).join("")}</tr>
          </thead>
          <tbody>${rowHtml}</tbody>
        </table>
      </div>
    `
    : `<p class="empty-state compact">本次调用没有表格行，返回类型：${escapeHTML(result.type ?? "unknown")}</p>`;

  alphaVantagePreview.innerHTML = `
    <div class="akshare-preview-head">
      <div>
        <strong>${escapeHTML(capability.label ?? "Alpha Vantage 结果")}</strong>
        <p>${escapeHTML(capability.function ?? "")} · ${escapeHTML(alphaVantagePreviewPayload.fetched_at ?? "")}</p>
      </div>
      <span class="count-pill">${result.returned_rows ?? 0}/${result.total_rows ?? 0} 行</span>
    </div>
    ${table}
  `;
}

function formatPreviewCell(value, column = "") {
  return displayCellValue(value, column);
}

function akshareCapabilityById(capabilityId) {
  return (aksharePayload?.capabilities ?? []).find((item) => item.id === capabilityId);
}

function buildAkshareQuery(capability, card = null) {
  const searchParams = new URLSearchParams();
  searchParams.set("account_id", apiState.accountId);
  searchParams.set("limit", String(Math.min(capability.default_limit ?? 50, 50)));
  for (const param of capability.params ?? []) {
    const input = card?.querySelector(`[data-ak-param="${CSS.escape(param.name)}"]`);
    const value = input ? input.value.trim() : akshareParamDefault(capability, param);
    if (param.required && (value === "" || value === null || value === undefined)) {
      throw new Error(`缺少参数：${param.name}`);
    }
    if (value !== "" && value !== null && value !== undefined) {
      searchParams.set(param.name, value);
    }
  }
  return searchParams.toString();
}

async function runAkshareCapability(capabilityId, card = null) {
  const capability = akshareCapabilityById(capabilityId);
  if (!capability) return;
  aksharePreviewLoading = true;
  aksharePreviewError = "";
  renderAksharePreview();
  try {
    const query = buildAkshareQuery(capability, card);
    const suffix = query ? `?${query}` : "";
    aksharePreviewPayload = await apiRequest(`/api/akshare/query/${encodeURIComponent(capabilityId)}${suffix}`);
    aksharePreviewError = "";
    await loadSearchHistory();
  } catch (error) {
    aksharePreviewPayload = null;
    aksharePreviewError = `AKShare 试跑失败：${error.message}`;
  } finally {
    aksharePreviewLoading = false;
    renderAksharePreview();
  }
}

function alphaVantageCapabilityById(capabilityId) {
  return (alphaVantagePayload?.capabilities ?? []).find((item) => item.id === capabilityId);
}

function buildAlphaVantageQuery(capability, exampleIndex = 0) {
  const searchParams = new URLSearchParams();
  const example = capability.examples?.[exampleIndex] ?? capability.examples?.[0] ?? {};
  searchParams.set("account_id", apiState.accountId);
  searchParams.set("return_limit", String(Math.min(capability.default_return_limit ?? 50, 50)));
  for (const param of capability.params ?? []) {
    const value = example[param.name] ?? param.default ?? "";
    if (param.required && (value === "" || value === null || value === undefined)) {
      throw new Error(`缺少示例参数：${param.name}`);
    }
    if (value !== "" && value !== null && value !== undefined) {
      searchParams.set(param.name, value);
    }
  }
  return searchParams.toString();
}

async function runAlphaVantageCapability(capabilityId, exampleIndex = 0) {
  const capability = alphaVantageCapabilityById(capabilityId);
  if (!capability) return;
  alphaVantagePreviewLoading = true;
  alphaVantagePreviewError = "";
  renderAlphaVantagePreview();
  try {
    const query = buildAlphaVantageQuery(capability, exampleIndex);
    const suffix = query ? `?${query}` : "";
    alphaVantagePreviewPayload = await apiRequest(`/api/alpha-vantage/query/${encodeURIComponent(capabilityId)}${suffix}`);
    alphaVantagePreviewError = "";
    await loadSearchHistory();
  } catch (error) {
    alphaVantagePreviewPayload = null;
    alphaVantagePreviewError = `Alpha Vantage 试跑失败：${error.message}`;
  } finally {
    alphaVantagePreviewLoading = false;
    renderAlphaVantagePreview();
  }
}

async function saveDataSource(sourceId) {
  const card = dataSourceGrid?.querySelector(`[data-source-card="${CSS.escape(sourceId)}"]`);
  const source = dataSources.find((item) => item.id === sourceId) ?? fallbackDataSources.find((item) => item.id === sourceId);
  if (!card || !source) return;
  const enabled = Boolean(card.querySelector(`[data-source-enabled="${CSS.escape(sourceId)}"]`)?.checked);
  const credential = card.querySelector(`[data-source-key="${CSS.escape(sourceId)}"]`)?.value.trim() ?? "";

  if (!apiState.connected) {
    source.enabled = enabled;
    if (credential || !source.requires_key) source.configured = true;
    source.active = source.enabled && source.configured;
    if (credential) source.credential_hint = credential.length <= 6 ? "******" : `${credential.slice(0, 3)}...${credential.slice(-3)}`;
    renderDataSources();
    return;
  }

  try {
    const payload = await apiRequest(`/api/data-sources/${encodeURIComponent(sourceId)}?account_id=${encodeURIComponent(apiState.accountId)}`, {
      method: "PUT",
      body: JSON.stringify({ enabled, credential })
    });
    applyDataSourcePayload(payload);
    if (source.provider === "alpha_vantage") await loadAlphaVantageCapabilities();
    await loadSourceTestCatalog();
    await loadStocksFromApi();
    renderCandidates();
    renderDetails(selectedStock() ?? stocks[0]);
    renderWatchlist();
    renderStockAnomalyReport(selectedAnomalySymbol);
    updateBackendStatus(`数据源 ${source.label} 已更新`);
  } catch (error) {
    apiState.lastError = `数据源配置失败：${error.message}`;
    updateBackendStatus(apiState.lastError);
  }
}

async function refreshProviderData(provider) {
  if (!apiState.connected) {
    updateBackendStatus("后端未连接，无法刷新真实数据源。");
    return;
  }

  try {
    const label = provider === "finnhub" ? "Finnhub"
      : provider === "tushare" ? "Tushare"
      : provider === "akshare" ? "AKShare"
      : provider === "baostock" ? "BaoStock 历史回刷"
      : provider === "baostock-financial" ? "BaoStock 季频财务"
      : provider === "cninfo_sse_szse" ? "A 股公告自动源"
      : provider === "cninfo" ? "CNINFO 公告"
      : provider === "sse" ? "上交所公告"
      : provider === "szse" ? "深交所公告"
      : provider === "xueqiu" ? "雪球评论"
      : provider;
    if (provider === "xueqiu") {
      const selected = selectedStock()?.symbol;
      const symbols = [...new Set([selected, ...favoriteSymbols].filter(Boolean))].slice(0, 30);
      updateBackendStatus(`${label} 刷新中`);
      const payload = await apiRequest("/api/community/crawl", {
        method: "POST",
        body: JSON.stringify({
          symbols,
          source: provider,
          limit: 120,
          timeout: provider === "xueqiu" ? 30 : 15,
          sleep_seconds: 0.8
        })
      });
      await loadAccountFromApi(apiState.accountId);
      const counts = payload.counts ?? {};
      const errors = payload.errors ?? [];
      updateBackendStatus(`${label} 已刷新：覆盖 ${counts.symbols ?? 0} 只，入库 ${counts.posts ?? 0} 条${errors.length ? `，失败 ${errors.length} 个` : ""}`);
      return;
    }
    const backgroundProviders = ["baostock", "baostock-financial", "cninfo_sse_szse", "cninfo", "sse", "szse"];
    updateBackendStatus(`${label} 数据刷新中`);
    const payload = await apiRequest("/api/data/refresh", {
      method: "POST",
      body: JSON.stringify({ provider, scope: provider, account_id: apiState.accountId, refresh_universe: backgroundProviders.includes(provider) })
    });
    if ((payload.mode === "baostock-backfill-background" || payload.mode === "baostock-quarterly-financials-background" || payload.mode === "a-share-filings-background") && payload.run_id) {
      startDataJobPolling(payload.run_id, label);
      const counts = payload.counts ?? payload.job?.counts ?? {};
      updateBackendStatus(`${label} 后台任务 ${payload.already_running ? "运行中" : "已启动"}：剩余 ${counts.remaining_candidates ?? "?"} 只`);
      return;
    }
    await loadAccountFromApi(apiState.accountId);
    const counts = payload.counts ?? {};
    updateBackendStatus(`${label} 已刷新：股票 ${counts.symbols ?? 0}，日线 ${counts.daily_bars ?? counts.market_snapshots ?? 0}，财务 ${counts.financial_snapshots ?? 0}，公告 ${counts.filings ?? 0}，新闻 ${counts.news_items ?? 0}`);
  } catch (error) {
    apiState.lastError = `真实数据刷新失败：${error.message}`;
    updateBackendStatus(apiState.lastError);
  }
}

function startDataJobPolling(runId, label) {
  if (dataJobPoller) clearInterval(dataJobPoller);
  pollDataJob(runId, label);
  dataJobPoller = setInterval(() => pollDataJob(runId, label), 5000);
}

async function pollDataJob(runId, label) {
  try {
    const payload = await apiRequest(`/api/data/jobs/${encodeURIComponent(runId)}`);
    const counts = payload.counts ?? {};
    const status = payload.status ?? "running";
    const batches = counts.batches ?? 0;
    const progressText = dataJobProgressText(counts);
    const remaining = counts.remaining_candidates ?? "?";
    if (status === "running") {
      updateBackendStatus(`${label} 后台回刷中：${batches} 批，${progressText}，剩余 ${remaining}`);
      return;
    }
    if (dataJobPoller) {
      clearInterval(dataJobPoller);
      dataJobPoller = null;
    }
    await loadAccountFromApi(apiState.accountId);
    updateBackendStatus(`${label} 后台回刷${status === "ok" ? "完成" : status}：${batches} 批，${progressText}，剩余 ${remaining}`);
  } catch (error) {
    if (dataJobPoller) {
      clearInterval(dataJobPoller);
      dataJobPoller = null;
    }
    apiState.lastError = `后台任务查询失败：${error.message}`;
    updateBackendStatus(apiState.lastError);
  }
}

function dataJobProgressText(counts) {
  if (counts.financial_metrics !== undefined || counts.company_reports !== undefined) {
    return `季频指标 ${counts.financial_metrics ?? 0}，公司报告 ${counts.company_reports ?? 0}`;
  }
  if (counts.filings !== undefined) {
    return `公告 ${counts.filings ?? 0}，无公告 ${counts.no_data_symbols ?? 0}`;
  }
  return `日线 ${counts.daily_bars ?? 0}`;
}

function openClaimDetail(index) {
  const stock = selectedStock();
  if (!stock || !stock.evidence[index]) return;
  const item = stock.evidence[index];
  openModal("证据详情", displayText(item.claim), `
    <div class="modal-grid">
      <div class="metric-box"><span>来源等级</span><strong>${item.tier}</strong></div>
      <div class="metric-box"><span>置信度</span><strong>${Math.round(item.confidence * 100)}%</strong></div>
      <div class="metric-box"><span>来源</span><strong>${escapeHTML(displayText(item.source))}</strong></div>
    </div>
    <section class="modal-section">
      <h4>分析过程</h4>
      <ol>${item.process.map((step) => `<li>${escapeHTML(displayText(step))}</li>`).join("")}</ol>
    </section>
    <section class="modal-section">
      <h4>原始字段快照</h4>
      ${renderKeyValue(item.rawFields)}
    </section>
    ${item.url ? `<a class="source-link" href="${item.url}" target="_blank" rel="noreferrer">打开来源链接</a>` : `<p class="empty-state compact">没有可打开链接。</p>`}
  `);
}

function openFactorDetail(name) {
  const stock = selectedStock();
  if (!stock) return;
  const detail = factorDetail(stock, name);
  openModal("因子详情", `${stock.symbol} · ${name}`, `
    <p class="thesis">${detail.summary}</p>
    <section class="modal-section">
      <h4>具体数据值</h4>
      ${renderKeyValue(Object.fromEntries(detail.values))}
    </section>
    <section class="modal-section">
      <h4>数据来源</h4>
      <p>${escapeHTML(displayText(detail.source))}</p>
    </section>
    <section class="modal-section">
      <h4>计算和复核逻辑</h4>
      <p>${detail.process}</p>
    </section>
  `);
}

function renderKeyValue(values) {
  return `
    <dl class="kv-list">
      ${Object.entries(values).map(([key, value]) => `
        <div>
          <dt>${escapeHTML(displayColumnLabel(key))}</dt>
          <dd>${escapeHTML(displayCellValue(value, key))}</dd>
        </div>
      `).join("")}
    </dl>
  `;
}

function openModal(kicker, title, body) {
  modalKicker.textContent = kicker;
  modalTitle.textContent = title;
  modalBody.innerHTML = body;
  modalShell.hidden = false;
}

function closeModal() {
  modalShell.hidden = true;
}

async function refreshStockData(source) {
  const stock = selectedStock();
  if (!stock) return;
  if (source === "detail" && stockDetailRefreshing.has(stock.symbol)) return;
  stockDetailCache.delete(stock.symbol);
  stockDetailErrors.delete(stock.symbol);
  stockDetailRefreshErrors.delete(stock.symbol);
  if (apiState.connected && source === "detail" && stock.market !== "US") {
    stockDetailRefreshing.add(stock.symbol);
    stockDetailRefreshStartedAt.set(stock.symbol, Date.now());
    stockDetailRefreshSteps.set(stock.symbol, "正在刷新行情、K线、季度财务、公司报告、公告和资讯源。");
    ensureRefreshElapsedTimer();
    renderDetails(stock);
    try {
      updateBackendStatus(`刷新 ${stock.symbol} 数据中`);
      const refreshResult = await apiRequest(`/api/stocks/${encodeURIComponent(stock.symbol)}/refresh?market=${encodeURIComponent(stock.market || "all")}&days=260&quarters=8`, {
        method: "POST"
      });
      const slowestStep = [...(refreshResult.performance?.steps ?? [])].sort((a, b) => Number(b.duration_ms || 0) - Number(a.duration_ms || 0))[0];
      const slowestText = slowestStep ? `最慢：${slowestStep.step} ${Math.round(Number(slowestStep.duration_ms || 0) / 1000)}秒。` : "";
      stockDetailRefreshSteps.set(stock.symbol, `刷新完成，正在读取最新详情并重绘页面。${slowestText}`);
      renderDetails(stock);
      await loadStockDetail(stock.symbol, stock.market);
      await loadStocksFromApi();
      const refreshed = stockBySymbol(stock.symbol) ?? stock;
      renderDetails(refreshed);
      renderCandidates();
      renderWatchlist();
      updateBackendStatus(`${stock.symbol} 已刷新${slowestText ? `，${slowestText}` : ""}`);
      return;
    } catch (error) {
      stockDetailRefreshErrors.set(stock.symbol, error.message);
      apiState.lastError = `${stock.symbol} 刷新失败：${error.message}`;
      updateBackendStatus(apiState.lastError);
    } finally {
      stockDetailRefreshing.delete(stock.symbol);
      stockDetailRefreshStartedAt.delete(stock.symbol);
      stockDetailRefreshSteps.delete(stock.symbol);
      stopRefreshElapsedTimerIfIdle();
      const current = stockBySymbol(stock.symbol) ?? stock;
      renderDetails(current);
    }
    return;
  }
  if (apiState.connected && source === "market" && stock.market === "US") {
    try {
      updateBackendStatus(`Finnhub 刷新 ${stock.symbol} 中`);
      await apiRequest("/api/data/refresh", {
        method: "POST",
        body: JSON.stringify({ provider: "finnhub", scope: "finnhub", account_id: apiState.accountId, symbols: [stock.symbol] })
      });
      await loadStocksFromApi();
      const refreshed = stockBySymbol(stock.symbol) ?? stock;
      renderDetails(refreshed);
      renderCandidates();
      renderWatchlist();
      updateBackendStatus(`Finnhub 已刷新 ${stock.symbol}`);
      return;
    } catch (error) {
      apiState.lastError = `Finnhub 刷新失败：${error.message}`;
      updateBackendStatus(apiState.lastError);
    }
  }
  if (source === "market") {
    stock.lagMinutes = 0;
    stock.freshnessStatus = "fresh";
    stock.metrics.volumeRatio = Number((stock.metrics.volumeRatio + 0.05).toFixed(2));
    stock.memory.delta.unshift(`用户刷新行情：${formatAsOf(0)} 已重新读取行情、K线、成交额、买卖价差。`);
  }
  renderDetails(stock);
  renderCandidates();
  renderWatchlist();
}

function addSupplementEvidence() {
  const stock = selectedStock();
  if (!stock) return;
  const text = document.querySelector("#supplementText")?.value.trim();
  const url = document.querySelector("#supplementUrl")?.value.trim();
  if (!text) return;
  const item = {
    tier: "U",
    source: "用户补充",
    claim: escapeHTML(text),
    confidence: url ? 0.58 : 0.48,
    url: escapeHTML(url),
    sourceRank: 45,
    process: [
      `用户补充材料进入待核验队列：${text.slice(0, 70)}`,
      "系统只把它作为候选证据，不直接替代官方公告或原始财务数据",
      url ? "存在链接，可在真实版本中抓取页面并做实体匹配" : "没有链接，真实版本需要人工确认来源"
    ],
    rawFields: {
      submitted_at: new Date().toISOString(),
      provider: "user_supplement",
      source_url: url || "none",
      entity_match: `${stock.symbol}:${stock.name}`
    }
  };
  stock.evidence.push(item);
  stock.supplementCount += 1;
  stock.truthScore = Math.min(96, stock.truthScore + (url ? 4 : 2));
  stock.memory.reusable.push({
    title: `用户补证 #${stock.supplementCount}`,
    text: `${text}${url ? `；链接：${url}` : ""}`
  });
  stock.memory.delta.unshift(`用户补充证据后，证据可信度更新为 ${stock.truthScore}%。`);
  renderDetails(stock);
  renderCandidates();
  renderWatchlist();
}

function updateMemory() {
  const stock = selectedStock();
  if (!stock) return;
  stock.memoryUpdatedAt = new Date().toLocaleString("zh-CN", { hour12: false });
  stock.memory.delta.unshift(`记忆已更新：综合评分 ${stock.score}，当前动作 ${stock.action}，数据状态 ${statusText(stock.freshnessStatus)}。`);
  renderMemory(stock);
}

function syncFilterModeButtons() {
  document.querySelectorAll("[data-filter-mode]").forEach((button) => {
    button.classList.toggle("active", button.dataset.filterMode === filterMode);
  });
}

async function refreshPortfolioPrices() {
  priceRefreshCount += 1;
  if (apiState.connected) {
    try {
      const data = await apiRequest("/api/data/refresh", {
        method: "POST",
        body: JSON.stringify({ scope: "portfolio", account_id: apiState.accountId })
      });
      if (data.portfolio) {
        apiState.portfolio = data.portfolio;
        syncStocksFromBackendPortfolio(data.portfolio);
        latestPriceRefreshAt = new Date().toLocaleString("zh-CN", { hour12: false });
        const stock = selectedStock();
        if (stock) renderDetails(stock);
        renderCandidates();
        renderWatchlist();
        return;
      }
    } catch (error) {
      apiState.lastError = `刷新队列同步失败：${error.message}`;
      updateBackendStatus(apiState.lastError);
    }
  }
  const deltas = [0.006, -0.003, 0.004, -0.002, 0.007, 0.001];
  openPositions().forEach((position, index) => {
    const stock = position.stock;
    const delta = deltas[(priceRefreshCount + index) % deltas.length];
    const nextPrice = Number((stock.price * (1 + delta)).toFixed(2));
    stock.price = nextPrice;
    stock.lagMinutes = 0;
    stock.freshnessStatus = "fresh";
    stock.spark = [...stock.spark.slice(1), nextPrice];
    stock.memory.delta.unshift(`用户刷新最新股价：${formatMoney(nextPrice, stock.currency)}，用于重新计算持仓盈亏。`);
  });
  latestPriceRefreshAt = new Date().toLocaleString("zh-CN", { hour12: false });
  const stock = selectedStock();
  if (stock) renderDetails(stock);
  renderCandidates();
  renderWatchlist();
}

function populateTradeForm() {
  tradeSymbol.innerHTML = stocks.map((stock) => `
    <option value="${stock.symbol}">${stock.symbol} · ${stock.name}</option>
  `).join("");
  tradeDate.value = "2026-06-05";
  tradeQty.value = 100;
  tradeFee.value = 0;
  syncTradePrice();
}

function syncTradePrice() {
  const stock = stockBySymbol(tradeSymbol.value);
  if (stock) tradePrice.value = stock.price.toFixed(2);
}

async function handleTradeSubmit(event) {
  event.preventDefault();
  const symbol = tradeSymbol.value;
  const side = tradeSide.value;
  const stock = stockBySymbol(symbol);
  const quantity = Number(tradeQty.value);
  const price = Number(tradePrice.value);
  const fee = Number(tradeFee.value || 0);
  const date = tradeDate.value;

  if (!stock || !date || !quantity || !price || quantity <= 0 || price <= 0 || fee < 0) {
    tradeFormStatus.textContent = "请填写有效的日期、数量、价格和费用。";
    tradeFormStatus.className = "form-status warn";
    return;
  }

  if (side === "SELL") {
    const position = calculatePosition(symbol);
    if (quantity > position.quantity) {
      tradeFormStatus.textContent = `Sell 数量不能超过当前持仓 ${position.quantity}。`;
      tradeFormStatus.className = "form-status warn";
      return;
    }
  }

  let trade = {
    id: Date.now(),
    symbol,
    side,
    date,
    quantity,
    price,
    fee
  };

  if (apiState.connected) {
    try {
      trade = await persistTrade(trade);
    } catch (error) {
      tradeFormStatus.textContent = `交易同步失败：${error.message}`;
      tradeFormStatus.className = "form-status warn";
      return;
    }
  }

  portfolioTrades.push(trade);

  if (side === "BUY") {
    favoriteSymbols.add(symbol);
    await persistFavorite(symbol, true);
  }
  tradeFormStatus.textContent = `${symbol} ${side === "BUY" ? "Buy" : "Sell"} 已录入。`;
  tradeFormStatus.className = "form-status fresh";
  renderDetails(stock);
  renderCandidates();
  renderWatchlist();
}

async function toggleFavorite(symbol) {
  const normalized = String(symbol || "").trim().toUpperCase();
  if (!normalized || favoriteToggleInFlight.has(normalized)) return;
  favoriteToggleInFlight.add(normalized);
  const wasFavorite = favoriteSymbols.has(normalized);
  const nextFavorite = !wasFavorite;
  if (nextFavorite) {
    favoriteSymbols.add(normalized);
    favoriteStockLoadFailed.delete(normalized);
  } else {
    favoriteSymbols.delete(normalized);
  }
  renderCandidates();
  renderWatchlist();
  const stock = selectedStock();
  if (stock) renderDetails(stock);
  const saved = await persistFavorite(normalized, nextFavorite);
  if (!saved) {
    if (wasFavorite) favoriteSymbols.add(normalized);
    else favoriteSymbols.delete(normalized);
    apiState.lastError = apiState.lastError || `关注列表同步失败：${normalized}`;
    updateBackendStatus(apiState.lastError);
  }
  favoriteToggleInFlight.delete(normalized);
  renderCandidates();
  renderWatchlist();
  if (stock) renderDetails(stock);
}

function normalizeTabId(id) {
  return id === "source-tests" ? "health" : id;
}

function syncActiveNav() {
  const hashTarget = normalizeTabId(location.hash.slice(1));
  setActiveTab(navSectionIds.includes(hashTarget) ? hashTarget : activeTab, false);
}

function setActiveTab(current, shouldUpdateHash = true) {
  const normalized = normalizeTabId(current);
  const next = navSectionIds.includes(normalized) ? normalized : "skillhub";
  activeTab = next;
  document.querySelectorAll(".section-block").forEach((section) => {
    const active = section.id === next;
    section.classList.toggle("active-panel", active);
    section.hidden = !active;
  });
  setActiveNav(next);
  if (shouldUpdateHash && location.hash !== `#${next}`) {
    history.replaceState(null, "", `#${next}`);
  }
  scheduleActiveTabDraws(next);
  maybeAutoRunBacktest();
}

function setActiveNav(current) {
  document.querySelectorAll(".nav-item").forEach((link) => {
    link.classList.toggle("active", link.getAttribute("href") === `#${current}`);
  });
}

skillHubSearchForm?.addEventListener("submit", handleSkillHubSearchSubmit);

skillHubPrompt?.addEventListener("input", () => {
  skillHubSearchText = skillHubPrompt.value.trim();
  renderSkillHub();
});

skillHubCategoryTabs?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-skill-category]");
  if (!button) return;
  activeSkillCategory = button.dataset.skillCategory;
  renderSkillHub();
});

skillHubHotQueries?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-skill-hot-query]");
  if (!button) return;
  skillHubSearchText = button.dataset.skillHotQuery;
  if (skillHubPrompt) skillHubPrompt.value = skillHubSearchText;
  activeSkillCategory = "news";
  const match = skillHubCatalog.find((skill) => skill.query === skillHubSearchText);
  if (match) executeSkillHubSkill(match, "", false);
  else renderSkillHub();
});

skillHubResults?.addEventListener("click", handleSkillHubAction);
skillHubFavorites?.addEventListener("click", handleSkillHubAction);
skillHubHistoryList?.addEventListener("click", handleSkillHubAction);
skillHubExecutionPanel?.addEventListener("click", handleSkillHubAction);

document.querySelectorAll(".segment").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".segment").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    activeMarket = button.dataset.market;
    activeIndustry = "";
    hideStockSearchSuggestions();
    void (async () => {
      await loadIndustryOptions();
      await runDatabaseScreener();
    })();
  });
});

document.querySelectorAll("[data-filter-mode]").forEach((button) => {
  button.addEventListener("click", () => {
    filterMode = button.dataset.filterMode;
    syncFilterModeButtons();
    void runDatabaseScreener();
  });
});

filterGroups.addEventListener("change", (event) => {
  const checkbox = event.target.closest("[data-filter-id]");
  if (!checkbox) return;
  if (checkbox.checked) activeFilterIds.add(checkbox.dataset.filterId);
  else activeFilterIds.delete(checkbox.dataset.filterId);
  renderActiveRules();
  void runDatabaseScreener();
});

industryFilter?.addEventListener("change", () => {
  activeIndustry = industryFilter.value;
  renderActiveRules();
  void runDatabaseScreener();
});

function handleStockGridClick(event) {
  const favoriteButton = event.target.closest("[data-favorite]");
  const button = event.target.closest("[data-analyze]");
  const card = event.target.closest(".stock-card");
  if (favoriteButton) {
    event.preventDefault();
    event.stopPropagation();
    void toggleFavorite(favoriteButton.dataset.favorite);
    return;
  }
  if (button) selectStock(button.dataset.analyze);
  else if (card) selectStock(card.dataset.symbol);
}

candidateGrid.addEventListener("click", handleStockGridClick);
favoriteGrid.addEventListener("click", handleStockGridClick);
filterResultGrid?.addEventListener("click", handleStockGridClick);

anomalyStockSearch.addEventListener("input", renderAnomalyStockList);
anomalyStockSearch.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    void saveSearchHistory("anomaly_stock", anomalyStockSearch.value);
  }
});

anomalyStockList.addEventListener("click", (event) => {
  const button = event.target.closest("[data-anomaly-symbol]");
  if (!button) return;
  renderStockAnomalyReport(button.dataset.anomalySymbol);
});

runAnomalyPrompt.addEventListener("click", renderPromptAnomalyReport);

anomalyPrompt.addEventListener("keydown", (event) => {
  if (event.key === "Enter") renderPromptAnomalyReport();
});

backtestForm?.addEventListener("submit", handleBacktestSubmit);

anomalyReport.addEventListener("click", (event) => {
  const anomalyButton = event.target.closest("[data-anomaly-symbol]");
  const openStockButton = event.target.closest("[data-anomaly-open-stock]");
  const refreshButton = event.target.closest("[data-refresh-source]");
  if (anomalyButton) renderStockAnomalyReport(anomalyButton.dataset.anomalySymbol);
  else if (openStockButton) selectStock(openStockButton.dataset.anomalyOpenStock);
  else if (refreshButton) {
    selectedSymbol = selectedAnomalySymbol;
    refreshStockData(refreshButton.dataset.refreshSource);
    renderStockAnomalyReport(selectedAnomalySymbol);
  }
});

function handleStockKlinePointer(event) {
  const canvas = event.target.closest?.("[data-stock-kline]");
  if (!canvas) return;
  if (event.type === "pointerdown") {
    canvas.setPointerCapture?.(event.pointerId);
  }
  const rect = canvas.getBoundingClientRect();
  stockKlineHoverState.set(canvas, {
    x: event.clientX - rect.left,
    y: event.clientY - rect.top
  });
  redrawStockKlineCanvas(canvas);
}

function clearStockKlineHover(canvas) {
  if (!canvas || !stockKlineHoverState.has(canvas)) return;
  stockKlineHoverState.delete(canvas);
  redrawStockKlineCanvas(canvas);
}

function handleStockKlinePointerOut(event) {
  const canvas = event.target.closest?.("[data-stock-kline]");
  if (!canvas) return;
  if (event.relatedTarget && canvas.contains(event.relatedTarget)) return;
  clearStockKlineHover(canvas);
}

function handleStockKlinePointerEnd(event) {
  if (event.pointerType === "mouse") return;
  const canvas = event.target.closest?.("[data-stock-kline]");
  clearStockKlineHover(canvas);
}

detailBody.addEventListener("pointerdown", handleStockKlinePointer);
detailBody.addEventListener("pointermove", handleStockKlinePointer);
detailBody.addEventListener("pointerout", handleStockKlinePointerOut);
detailBody.addEventListener("pointercancel", handleStockKlinePointerEnd);
detailBody.addEventListener("pointerup", handleStockKlinePointerEnd);

detailBody.addEventListener("click", (event) => {
  const periodButton = event.target.closest("[data-detail-period]");
  const infoTabButton = event.target.closest("[data-detail-info-tab]");
  const claimButton = event.target.closest("[data-claim-index]");
  const factorButton = event.target.closest("[data-factor]");
  const refreshButton = event.target.closest("[data-refresh-source]");
  const supplementButton = event.target.closest("[data-focus-supplement]");
  const addEvidenceButton = event.target.closest("#addEvidence");

  if (periodButton) {
    const stock = selectedStock();
    if (!stock) return;
    stockDetailPeriods.set(stock.symbol, periodButton.dataset.detailPeriod);
    renderDetails(stock);
  }
  else if (infoTabButton) {
    const stock = selectedStock();
    if (!stock) return;
    stockInfoTabs.set(stock.symbol, infoTabButton.dataset.detailInfoTab);
    renderDetails(stock);
  }
  else if (claimButton) openClaimDetail(Number(claimButton.dataset.claimIndex));
  else if (factorButton) openFactorDetail(factorButton.dataset.factor);
  else if (refreshButton) refreshStockData(refreshButton.dataset.refreshSource);
  else if (supplementButton) document.querySelector("#supplementText")?.focus();
  else if (addEvidenceButton) addSupplementEvidence();
});

sentimentAside?.addEventListener("click", (event) => {
  const refreshButton = event.target.closest("[data-sentiment-refresh]");
  if (refreshButton) {
    refreshCurrentSentiment(refreshButton.dataset.sentimentRefresh === "llm");
    return;
  }
  const communityClassButton = event.target.closest("[data-community-class]");
  if (communityClassButton) {
    toggleCommunityClassFilter(communityClassButton.dataset.communityClass || "");
    return;
  }
  const sentimentButton = event.target.closest("[data-sentiment-type]");
  if (!sentimentButton) return;
  toggleSentimentEvidence(sentimentButton.dataset.sentimentType);
});

document.querySelector("#runAnalysis").addEventListener("click", () => {
  submitStockSearch();
});

symbolInput.addEventListener("keydown", (event) => {
  if (event.key === "ArrowDown" || event.key === "ArrowUp") {
    if (!stockSearchSuggestions.length) return;
    event.preventDefault();
    stockSearchOpen = true;
    const direction = event.key === "ArrowDown" ? 1 : -1;
    highlightedStockSuggestion = (highlightedStockSuggestion + direction + stockSearchSuggestions.length) % stockSearchSuggestions.length;
    renderStockSearchSuggestions();
    return;
  }
  if (event.key === "Escape") {
    hideStockSearchSuggestions();
    return;
  }
  if (event.key === "Enter") {
    event.preventDefault();
    submitStockSearch();
  }
});

symbolInput.addEventListener("input", scheduleStockSearchSuggestions);
symbolInput.addEventListener("focus", scheduleStockSearchSuggestions);

stockSearchList?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-stock-suggestion]");
  if (!button) return;
  chooseStockSearchSuggestion(button.dataset.stockSuggestion);
});

stockSearchList?.addEventListener("pointerdown", (event) => {
  const button = event.target.closest("[data-stock-suggestion]");
  if (!button) return;
  event.preventDefault();
  event.stopPropagation();
  chooseStockSearchSuggestion(button.dataset.stockSuggestion);
});

stockSearchList?.addEventListener("mouseover", (event) => {
  const button = event.target.closest("[data-stock-suggestion]");
  if (!button) return;
  const nextIndex = stockSearchSuggestions.findIndex((stock) => stock.symbol === button.dataset.stockSuggestion);
  if (nextIndex < 0 || nextIndex === highlightedStockSuggestion) return;
  const activeButton = stockSearchList.querySelector(".stock-suggestion.active");
  activeButton?.classList.remove("active");
  activeButton?.setAttribute("aria-selected", "false");
  highlightedStockSuggestion = nextIndex;
  button.classList.add("active");
  button.setAttribute("aria-selected", "true");
});

document.querySelector("#applyPromptFilter").addEventListener("click", applyNaturalLanguageFilter);

filterPrompt.addEventListener("keydown", (event) => {
  if (event.key === "Enter") applyNaturalLanguageFilter();
});
filterPrompt.addEventListener("input", renderActiveRules);

document.querySelector("#resetFilters").addEventListener("click", () => {
  activeFilterIds = new Set();
  activeMarket = "all";
  activeIndustry = "";
  document.querySelectorAll(".segment").forEach((item) => item.classList.toggle("active", item.dataset.market === "all"));
  if (industryFilter) industryFilter.value = "";
  filterPrompt.value = "";
  renderFilterGroups();
  void (async () => {
    await loadIndustryOptions();
    await runDatabaseScreener();
  })();
});

accountSelect.addEventListener("change", () => {
  loadAccountFromApi(accountSelect.value);
});

document.querySelector("#updateMemory").addEventListener("click", updateMemory);

holdingRows.addEventListener("click", (event) => {
  const row = event.target.closest("[data-holding-symbol]");
  if (!row) return;
  selectedHoldingSymbol = row.dataset.holdingSymbol;
  renderHoldingRows();
  renderTradeRows();
  schedulePositionDraw();
});

toggleTradeDetails.addEventListener("click", () => {
  tradeDetailsOpen = !tradeDetailsOpen;
  tradeDetails.hidden = !tradeDetailsOpen;
  toggleTradeDetails.textContent = tradeDetailsOpen ? "收起流水和K线" : "展开流水和K线";
  toggleTradeDetails.setAttribute("aria-expanded", String(tradeDetailsOpen));
  if (tradeDetailsOpen) schedulePositionDraw();
});

tradeSymbol.addEventListener("change", syncTradePrice);
tradeForm.addEventListener("submit", handleTradeSubmit);

portfolioSummary.addEventListener("click", (event) => {
  if (event.target.closest("[data-refresh-profit]")) refreshPortfolioPrices();
});

healthGrid?.addEventListener("click", (event) => {
  const card = event.target.closest("[data-health-kind]");
  if (card) selectHealthKind(card.dataset.healthKind);
});

healthGrid?.addEventListener("keydown", (event) => {
  if (event.key !== "Enter" && event.key !== " ") return;
  const card = event.target.closest("[data-health-kind]");
  if (!card) return;
  event.preventDefault();
  selectHealthKind(card.dataset.healthKind);
});

sourceNotificationButton?.addEventListener("click", (event) => {
  event.stopPropagation();
  setSourceNotificationsOpen(!sourceNotificationsOpen);
});

sourceNotificationPanel?.addEventListener("click", (event) => {
  event.stopPropagation();
  const button = event.target.closest("[data-open-source]");
  if (!button) return;
  setSourceNotificationsOpen(false);
  setActiveTab("settings");
  requestAnimationFrame(() => {
    const card = dataSourceGrid?.querySelector(`[data-source-card="${CSS.escape(button.dataset.openSource)}"]`);
    if (!card) return;
    card.scrollIntoView({ behavior: "smooth", block: "center" });
    card.classList.add("source-card-focus");
    window.setTimeout(() => card.classList.remove("source-card-focus"), 1400);
  });
});

document.addEventListener("click", (event) => {
  if (!sourceNotificationsOpen) return;
  if (sourceNotificationPanel?.contains(event.target) || sourceNotificationButton?.contains(event.target)) return;
  setSourceNotificationsOpen(false);
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && sourceNotificationsOpen) setSourceNotificationsOpen(false);
});

dataSourceGrid?.addEventListener("click", (event) => {
  const refreshButton = event.target.closest("[data-source-refresh]");
  if (refreshButton) {
    refreshProviderData(refreshButton.dataset.sourceRefresh);
    return;
  }
  const button = event.target.closest("[data-source-save]");
  if (button) saveDataSource(button.dataset.sourceSave);
});

dataSourceGrid?.addEventListener("change", (event) => {
  const checkbox = event.target.closest("[data-source-enabled]");
  if (checkbox) saveDataSource(checkbox.dataset.sourceEnabled);
});

sourceTestSelect?.addEventListener("change", () => {
  selectedSourceTestId = sourceTestSelect.value;
  sourceTestPayload = null;
  sourceTestError = "";
  if (sourceTestSymbol) sourceTestSymbol.value = "";
  renderSourceTests();
});

sourceTestList?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-source-test-id]");
  if (!button) return;
  selectedSourceTestId = button.dataset.sourceTestId;
  sourceTestPayload = null;
  sourceTestError = "";
  if (sourceTestSymbol) sourceTestSymbol.value = "";
  renderSourceTests();
  runSourceTest();
});

sourceTestForm?.addEventListener("submit", (event) => {
  event.preventDefault();
  runSourceTest();
});

akshareToggle?.addEventListener("click", () => {
  akshareExpanded = !akshareExpanded;
  renderAkshareExplorer();
});

akshareCapabilityTabs?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-ak-category]");
  if (!button) return;
  activeAkshareCategory = button.dataset.akCategory;
  aksharePreviewPayload = null;
  aksharePreviewError = "";
  renderAkshareExplorer();
});

akshareCapabilityGrid?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-ak-fetch]");
  if (!button || button.disabled) return;
  runAkshareCapability(button.dataset.akFetch, button.closest("[data-ak-card]"));
});

alphaVantageCapabilityTabs?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-av-category]");
  if (!button) return;
  activeAlphaVantageCategory = button.dataset.avCategory;
  alphaVantagePreviewPayload = null;
  alphaVantagePreviewError = "";
  renderAlphaVantageExplorer();
});

alphaVantageCapabilityGrid?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-av-run]");
  if (button && !button.disabled) {
    runAlphaVantageCapability(button.dataset.avRun, Number.parseInt(button.dataset.avExample ?? "0", 10));
  }
});

modalShell.addEventListener("click", (event) => {
  if (event.target.closest("[data-close-modal]")) closeModal();
});

singleDrawer.addEventListener("click", (event) => {
  const favoriteButton = event.target.closest("[data-drawer-favorite]");
  if (favoriteButton) {
    event.preventDefault();
    event.stopPropagation();
    void toggleFavorite(favoriteButton.dataset.drawerFavorite);
    return;
  }
  if (event.target.closest("[data-close-drawer]")) closeSingleDrawer();
});

document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  if (stockSearchOpen) hideStockSearchSuggestions();
  else if (!modalShell.hidden) closeModal();
  else if (!singleDrawer.hidden) closeSingleDrawer();
});

document.addEventListener("click", (event) => {
  if (stockSearchOpen && !event.target.closest(".stock-search-control")) {
    hideStockSearchSuggestions();
  }
  const button = event.target.closest("[data-history-value]");
  if (!button) return;
  event.preventDefault();
  event.stopPropagation();
  applySearchHistoryValue(button.dataset.historySurface, button.dataset.historyValue);
});

window.addEventListener("hashchange", syncActiveNav);
window.addEventListener("load", () => {
  const hashTarget = normalizeTabId(location.hash.slice(1));
  setActiveTab(navSectionIds.includes(hashTarget) ? hashTarget : "skillhub", false);
});

document.querySelectorAll(".nav-item").forEach((link) => {
  link.addEventListener("click", (event) => {
    const target = link.getAttribute("href")?.slice(1);
    if (!navSectionIds.includes(target)) return;
    event.preventDefault();
    setActiveTab(target);
  });
});

applyDataSourcePayload({ sources: fallbackDataSources });
renderAkshareExplorer();
renderAlphaVantageExplorer();
renderSourceTests();
renderSkillHub();
renderFilterGroups();
syncFilterModeButtons();
populateTradeForm();
renderCandidates();
renderDetails(stocks[0]);
renderWatchlist();
renderHealth();
renderStockAnomalyReport(selectedAnomalySymbol);
renderBacktestResult();
setActiveTab(navSectionIds.includes(normalizeTabId(location.hash.slice(1))) ? normalizeTabId(location.hash.slice(1)) : "skillhub", false);
updateBackendStatus();
loadAccountFromApi();

function isLocalDevHost() {
  return ["localhost", "127.0.0.1", "0.0.0.0", "::1"].includes(location.hostname);
}

function clearLocalAppCaches() {
  if (!isLocalDevHost()) return;
  navigator.serviceWorker?.getRegistrations?.().then((registrations) => {
    registrations.forEach((registration) => registration.unregister());
  }).catch(() => {});
  window.caches?.keys?.().then((keys) => {
    keys.forEach((key) => window.caches.delete(key));
  }).catch(() => {});
}

clearLocalAppCaches();

if ("serviceWorker" in navigator && location.protocol !== "file:" && !isLocalDevHost()) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/service-worker.js").catch((error) => {
      apiState.lastError = `PWA 缓存注册失败：${error.message}`;
      updateBackendStatus(apiState.lastError);
    });
  });
}
