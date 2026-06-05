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
      { tier: "S", source: "交易所公告 Mock", claim: "近期公告未发现停牌或重大风险提示", confidence: 0.93 },
      { tier: "A", source: "财务数据 Mock", claim: "收入和现金流质量维持正向", confidence: 0.84 },
      { tier: "B", source: "新闻情绪 Mock", claim: "行业订单和出口话题热度上升", confidence: 0.72 }
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
      { tier: "S", source: "HKEXnews Mock", claim: "公告源可追溯，未发现冲突信息", confidence: 0.91 },
      { tier: "A", source: "公司财务 Mock", claim: "利润率稳定，现金流良好", confidence: 0.82 },
      { tier: "B", source: "财经新闻 Mock", claim: "回购和 AI 业务话题带动情绪", confidence: 0.68 }
    ],
    reflection: [
      { round: "第 1 轮", label: "数据闸门", status: "pass", text: "港股 mock 行情延迟 8 分钟，仍在本原型阈值内。" },
      { round: "第 2 轮", label: "证据闸门", status: "pass", text: "公司动作以 HKEXnews Mock 为核心证据，新闻未单独触发结论。" },
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
      { tier: "S", source: "SEC EDGAR Mock", claim: "财报字段完整，可核验收入和利润", confidence: 0.9 },
      { tier: "A", source: "结构化基本面 Mock", claim: "增长和毛利率维持高位", confidence: 0.86 },
      { tier: "B", source: "新闻情绪 Mock", claim: "AI 芯片需求叙事仍强", confidence: 0.7 }
    ],
    reflection: [
      { round: "第 1 轮", label: "数据闸门", status: "warn", text: "美股当前按上一交易日数据分析，盘前/盘中需要刷新。" },
      { round: "第 2 轮", label: "证据闸门", status: "pass", text: "核心财务 claim 来自 SEC Mock，新闻情绪只做辅助。" },
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
      { tier: "S", source: "交易所公告 Mock", claim: "公告源未出现硬性利空", confidence: 0.88 },
      { tier: "A", source: "财务数据 Mock", claim: "盈利质量仍高", confidence: 0.8 },
      { tier: "B", source: "情绪数据 Mock", claim: "消费板块情绪偏弱", confidence: 0.62 }
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
    thesis: "催化和技术面较强，但部分情绪来自市场传闻，真实版本必须用公告和销量数据核验。",
    reasons: ["智能硬件和汽车业务催化明显", "趋势强于港股大盘", "情绪热度高但未证实比例偏高"],
    risks: ["新业务估值波动", "传闻驱动导致追高风险"],
    evidence: [
      { tier: "S", source: "HKEXnews Mock", claim: "公告字段可追溯", confidence: 0.86 },
      { tier: "B", source: "新闻情绪 Mock", claim: "汽车业务话题热度上升", confidence: 0.66 },
      { tier: "C", source: "社媒热度 Mock", claim: "短线讨论度快速上升", confidence: 0.38 }
    ],
    reflection: [
      { round: "第 1 轮", label: "数据闸门", status: "warn", text: "行情延迟 22 分钟，接近原型阈值上限。" },
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
      { tier: "S", source: "SEC EDGAR Mock", claim: "财务披露完整", confidence: 0.9 },
      { tier: "A", source: "公司 IR Mock", claim: "回购和现金流可核验", confidence: 0.82 },
      { tier: "B", source: "新闻情绪 Mock", claim: "产品周期讨论度中性", confidence: 0.64 }
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
      { id: "amount-high", label: "成交额 >= 50亿", test: (stock) => stock.metrics.avgAmountCny >= 5000000000, keywords: ["成交额", "流动性", "活跃", "大成交"] },
      { id: "turnover-high", label: "换手率 >= 1%", test: (stock) => stock.metrics.turnoverRate >= 1, keywords: ["换手", "活跃"] },
      { id: "spread-low", label: "买卖价差 <= 5bp", test: (stock) => stock.metrics.spreadBps <= 5, keywords: ["价差", "买卖价差", "低摩擦", "滑点小"] }
    ]
  },
  {
    group: "估值与质量",
    items: [
      { id: "valuation-not-hot", label: "PE分位 <= 70", test: (stock) => stock.metrics.pePercentile <= 70, keywords: ["估值合理", "不贵", "安全边际", "pe"] },
      { id: "roe-high", label: "ROE >= 15%", test: (stock) => stock.metrics.roe >= 15, keywords: ["roe", "质量", "盈利能力"] },
      { id: "cashflow-good", label: "自由现金流率 >= 5%", test: (stock) => stock.metrics.fcfMargin >= 5, keywords: ["现金流", "自由现金流"] }
    ]
  },
  {
    group: "技术与催化",
    items: [
      { id: "trend-strong", label: "站上20日线", test: (stock) => stock.metrics.ma20GapPct > 0, keywords: ["趋势", "均线", "站上", "技术强"] },
      { id: "volume-confirm", label: "量能 >= 1.2倍", test: (stock) => stock.metrics.volumeRatio >= 1.2, keywords: ["放量", "成交量", "量能"] },
      { id: "catalyst-strong", label: "催化评分 >= 75", test: (stock) => stock.metrics.catalystScore >= 75, keywords: ["催化", "订单", "业绩", "政策", "新品"] }
    ]
  },
  {
    group: "证据与风险",
    items: [
      { id: "data-fresh", label: "数据 fresh", test: (stock) => stock.freshnessStatus === "fresh", keywords: ["新鲜", "实时", "不过期", "fresh"] },
      { id: "evidence-high", label: "证据可信 >= 80%", test: (stock) => stock.truthScore >= 80, keywords: ["证据", "可信", "真实性", "可靠"] },
      { id: "rumor-low", label: "未证实 < 25%", test: (stock) => stock.metrics.unverifiedRatio < 0.25, keywords: ["少传闻", "未证实少", "真实性高"] }
    ]
  }
];

const healthSources = [
  {
    name: "行情/K 线",
    status: "fresh",
    source: "Mock adapter",
    text: "盘中阈值 90 秒；延迟源按授权合同单独配置。过期则禁止输出买卖结论。"
  },
  {
    name: "财务/估值",
    status: "fresh",
    source: "Structured mock",
    text: "估值依赖行情价格，行情过期时 PE/PB 同步降级。"
  },
  {
    name: "公告/披露",
    status: "fresh",
    source: "Exchange mock",
    text: "真实版本优先 CNINFO、SSE/SZSE、HKEXnews、SEC EDGAR。"
  },
  {
    name: "新闻/情绪",
    status: "warn",
    source: "Sentiment mock",
    text: "未证实信息比例偏高时只允许观察，不允许升级动作。"
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
  hkexnews: "HKEXnews 公告",
  mock: "模拟数据",
  mock_hk_market: "港股模拟行情",
  mock_hk_financial: "港股模拟财务",
  mock_news_cn: "A 股模拟新闻情绪",
  mock_news_hk: "港股模拟新闻情绪",
  mock_news_us: "美股模拟新闻情绪",
  sse: "上交所公告",
  szse: "深交所公告",
  tushare: "Tushare Pro",
  "mock-adapter": "模拟适配器",
  "mock adapter": "模拟适配器",
  "structured mock": "结构化模拟数据",
  "exchange mock": "交易所模拟数据",
  "sentiment mock": "情绪模拟数据",
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
  price: "最新价",
  published_at: "发布时间",
  quarterlyreports: "季度报告",
  raw_ticker_sentiment: "原始标的情绪",
  section: "分组",
  sentiment_score: "情绪分",
  source: "来源",
  source_tier: "来源等级",
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
  { id: "cn-tushare-market", market: "A", label: "Tushare Pro A股行情", provider: "tushare", source_kind: "market", source_kind_label: "行情", requires_key: true, credential_label: "Tushare token", enabled: false, configured: false, active: false, credential_hint: "" },
  { id: "cn-tushare-financial", market: "A", label: "Tushare Pro 财务/估值", provider: "tushare", source_kind: "financial", source_kind_label: "财务/估值", requires_key: true, credential_label: "Tushare token", enabled: false, configured: false, active: false, credential_hint: "" },
  { id: "cn-exchange-filings", market: "A", label: "CNINFO / 交易所公告", provider: "cninfo_sse_szse", source_kind: "filing", source_kind_label: "公告/披露", requires_key: false, credential_label: "无需 key", enabled: true, configured: true, active: true, credential_hint: "" },
  { id: "cn-news-sentiment", market: "A", label: "A股新闻情绪", provider: "mock_news_cn", source_kind: "news", source_kind_label: "新闻情绪", requires_key: true, credential_label: "News API key", enabled: false, configured: false, active: false, credential_hint: "" },
  { id: "hk-market-vendor", market: "HK", label: "港股行情供应商", provider: "mock_hk_market", source_kind: "market", source_kind_label: "行情", requires_key: true, credential_label: "Market API key", enabled: false, configured: false, active: false, credential_hint: "" },
  { id: "hk-financial-provider", market: "HK", label: "港股财务/估值", provider: "mock_hk_financial", source_kind: "financial", source_kind_label: "财务/估值", requires_key: true, credential_label: "Financial API key", enabled: false, configured: false, active: false, credential_hint: "" },
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
let stocks = baseStocks.map((stock) => enrichStock(stock));

let activeMarket = "all";
let selectedSymbol = stocks[0].symbol;
let filterMode = "all";
let activeFilterIds = new Set(["amount-high", "evidence-high"]);
let favoriteSymbols = new Set(["002594.SZ", "0700.HK", "1810.HK"]);
let priceRefreshCount = 0;
let latestPriceRefreshAt = "未刷新";
let selectedHoldingSymbol = "002594.SZ";
let tradeDetailsOpen = false;
let selectedAnomalySymbol = "002594.SZ";
let activeTab = "filters";
let dataSources = [];
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
let sourceTestPayload = null;
let sourceTestLoading = false;
let sourceTestError = "";
let searchHistoryItems = [];
let backtestPayload = null;
let backtestLoading = false;
let backtestError = "";
const apiState = {
  connected: false,
  accountId: "acct-admin",
  accounts: [],
  sharedCache: null,
  sourceSummary: null,
  portfolio: null,
  lastError: ""
};
const navSectionIds = ["filters", "health", "source-tests", "daily", "anomalies", "backtests", "favorites", "holdings", "settings"];

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
const detailAction = document.querySelector("#detailAction");
const detailBody = document.querySelector("#detailBody");
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
const filterGroups = document.querySelector("#filterGroups");
const filterPrompt = document.querySelector("#filterPrompt");
const activeRules = document.querySelector("#activeRules");
const accountSelect = document.querySelector("#accountSelect");
const backendStatus = document.querySelector("#backendStatus");
const sharedCacheStatus = document.querySelector("#sharedCacheStatus");
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
  { surface: "anomaly_prompt", input: () => anomalyPrompt }
];

function enrichStock(stock) {
  const metrics = stock.metrics ?? metricProfiles[stock.symbol];
  const enriched = {
    ...stock,
    metrics,
    memoryUpdatedAt: "2026-06-04 22:10",
    supplementCount: 0
  };
  enriched.evidence = stock.evidence.map((item, index) => enrichEvidence(enriched, item, index));
  enriched.memory = buildMemory(enriched);
  return enriched;
}

function enrichEvidence(stock, item, index) {
  const authorityUrl = officialUrlFor(stock, item);
  return {
    ...item,
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
      provider: item.source,
      entity_match: `${stock.symbol}:${stock.name}`,
      checksum: `${stock.symbol.replace(".", "")}-${index + 1}-${Math.round(item.confidence * 1000)}`
    }
  };
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
        text: `最近一次完整分析已保存：ROE ${metrics.roe.toFixed(1)}%，收入增速 ${metrics.revenueGrowth.toFixed(1)}%，自由现金流率 ${metrics.fcfMargin.toFixed(1)}%，资产负债率 ${metrics.debtRatio.toFixed(1)}%。这些字段可作为二次分析基线，但遇到新财报必须重新读取原始财报。`
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

function formatPrice(stock) {
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
  const anchor = input.closest("label") ?? input;
  let row = document.querySelector(`[data-search-history-row="${CSS.escape(surface)}"]`);
  if (!row || !document.body.contains(row)) {
    row = document.createElement("div");
    row.className = "search-history-row";
    row.dataset.searchHistoryRow = surface;
  }
  if (anchor.tagName === "LABEL") {
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
  if (surface === "stock_analysis") selectStock(value);
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
  backendStatus.textContent = apiState.connected ? "Mock API connected" : "本地 fallback";
  backendStatus.className = `status-chip ${apiState.connected ? "fresh" : "warn"}`;
  backendStatus.title = message || apiState.lastError || "前端可在后端关闭时继续使用内置 mock。";

  if (apiState.sharedCache) {
    sharedCacheStatus.textContent = `共享分析 ${apiState.sharedCache.stock_analysis_runs} 条`;
    sharedCacheStatus.title = "股票分析、异动分析和记忆是跨账户共享资产。";
  } else {
    sharedCacheStatus.textContent = "共享分析 local";
    sharedCacheStatus.title = "当前使用前端内置 mock 共享分析。";
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

function populateAccountSelect() {
  if (!accountSelect || !apiState.accounts.length) return;
  accountSelect.innerHTML = apiState.accounts.map((account) => `
    <option value="${account.id}" ${account.id === apiState.accountId ? "selected" : ""}>${account.name}</option>
  `).join("");
}

async function loadStocksFromApi() {
  if (!apiState.connected) return;
  const data = await apiRequest(`/api/stocks/search?account_id=${encodeURIComponent(apiState.accountId)}`);
  if (!Array.isArray(data.stocks) || !data.stocks.length) return;
  stocks = data.stocks.map(normalizeApiStock).map((stock) => enrichStock(stock));
  if (!stockBySymbol(selectedSymbol)) selectedSymbol = stocks[0].symbol;
  if (!stockBySymbol(selectedAnomalySymbol)) selectedAnomalySymbol = stocks[0].symbol;
}

function applyDataSourcePayload(payload) {
  dataSources = Array.isArray(payload?.sources) ? payload.sources : fallbackDataSources;
  apiState.sourceSummary = payload?.summary ?? null;
  renderDataSources();
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
  } catch (error) {
    apiState.connected = false;
    apiState.sharedCache = null;
    apiState.sourceSummary = null;
    apiState.portfolio = null;
    apiState.lastError = `Mock API 未连接：${error.message}`;
    applyDataSourcePayload({ sources: fallbackDataSources });
    await loadAkshareCapabilities();
    await loadAlphaVantageCapabilities();
    await loadSourceTestCatalog();
    updateBackendStatus(apiState.lastError);
  }
}

async function persistFavorite(symbol, favorite) {
  if (!apiState.connected) return;
  try {
    const data = await apiRequest(`/api/accounts/${encodeURIComponent(apiState.accountId)}/favorites/${encodeURIComponent(symbol)}`, {
      method: "PUT",
      body: JSON.stringify({ favorite })
    });
    favoriteSymbols = new Set(data.favorites);
  } catch (error) {
    apiState.lastError = `关注列表同步失败：${error.message}`;
    updateBackendStatus(apiState.lastError);
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
  const marketList = activeMarket === "all" ? stocks : stocks.filter((stock) => stock.market === activeMarket);
  const activeRulesList = [...activeFilterIds].map((id) => filtersById.get(id)).filter(Boolean);
  if (!activeRulesList.length) return marketList;
  return marketList.filter((stock) => {
    const results = activeRulesList.map((rule) => rule.test(stock));
    return filterMode === "all" ? results.every(Boolean) : results.some(Boolean);
  });
}

function renderFilterGroups() {
  filterGroups.innerHTML = filterCatalog.map((group) => `
    <section class="filter-group">
      <h4>${group.group}</h4>
      <div class="filter-options">
        ${group.items.map((item) => `
          <label class="check-row">
            <input type="checkbox" data-filter-id="${item.id}" ${activeFilterIds.has(item.id) ? "checked" : ""} />
            <span>${item.label}</span>
          </label>
        `).join("")}
      </div>
    </section>
  `).join("");
  renderActiveRules();
}

function renderActiveRules() {
  const rules = [...activeFilterIds].map((id) => filtersById.get(id)).filter(Boolean);
  activeRules.innerHTML = rules.length
    ? rules.map((rule) => `<span class="rule-pill">${rule.label}</span>`).join("")
    : `<span class="rule-pill muted">未启用过滤</span>`;
}

function applyNaturalLanguageFilter() {
  const text = filterPrompt.value.trim().toLowerCase();
  if (!text) return;
  void saveSearchHistory("filter_prompt", filterPrompt.value);
  filterCatalog.forEach((group) => {
    group.items.forEach((item) => {
      const matched = item.keywords.some((keyword) => text.includes(keyword.toLowerCase()));
      if (matched) activeFilterIds.add(item.id);
    });
  });
  if (text.includes("宽松") || text.includes("任一") || text.includes("或者")) {
    filterMode = "any";
    syncFilterModeButtons();
  }
  renderFilterGroups();
  renderCandidates();
}

function renderCandidates() {
  const list = filteredStocks();
  candidateCount.textContent = `${list.length} 只`;
  if (candidateGrid) {
    candidateGrid.innerHTML = list.length
      ? list.map(renderStockCard).join("")
      : `<div class="empty-state">当前过滤组合没有匹配股票。</div>`;
  }
  if (filterResultCount) filterResultCount.textContent = `${list.length} 只`;
  if (filterResultGrid) {
    filterResultGrid.innerHTML = list.length
      ? list.map(renderStockCard).join("")
      : `<div class="empty-state">当前过滤组合没有匹配股票。</div>`;
  }
  requestAnimationFrame(drawAllSparklines);
  renderAnomalyStockList();
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
        <p class="eyebrow">Stock anomaly · Mock</p>
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
        <li>本报告只使用 mock 行情、新闻热度和因子快照；真实版本需要拉取最新盘口、逐笔、公告和新闻源。</li>
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
        <p class="eyebrow">Question anomaly · Mock</p>
        <h4>${title}</h4>
      </div>
      <span class="anomaly-score">${negative ? 78 : 62}</span>
    </div>
    <p class="thesis">${subject}出现${direction}时，优先拆成三层：指数/板块同步性、资金流和消息面真实性。本报告是 mock 推理模板，不代表实时市场事实。</p>
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
  const config = backtestConfigFromForm();
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

function renderBacktestResult() {
  if (!backtestResult) return;
  if (backtestStatus) {
    backtestStatus.textContent = backtestLoading ? "运行中" : backtestPayload ? "已生成报告" : "Mock 研究回测";
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
      <p>${escapeHTML(strategy.thesis ?? "用于验证策略假设的 mock 研究回测。")}</p>
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
          <span class="confidence">${escapeHTML(backtestPayload.mode ?? "mock")}</span>
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
  requestAnimationFrame(drawBacktestCurve);
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
    mode: "local-mock-research-backtest",
    run_id: `local-${Date.now()}`,
    config,
    strategy: { label: strategyLabel(config.strategy), thesis: "本地 fallback 使用页面内 mock 股票曲线，只用于确认回测报告交互。" },
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
      "当前为本地 fallback mock 回测，不代表真实历史收益。",
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

function renderStockCard(stock) {
  const changeClass = stock.change >= 0 ? "up" : "down";
  const sign = stock.change >= 0 ? "+" : "";
  return `
    <article class="stock-card ${stock.symbol === selectedSymbol ? "selected" : ""}" data-symbol="${stock.symbol}">
      <div class="card-head">
        <div>
          <p class="symbol">${stock.symbol}</p>
          <p class="company">${stock.name} · ${stock.marketLabel}</p>
        </div>
        <div class="card-actions">
          ${renderStockBadges(stock)}
          <div class="score-ring" style="--score: ${stock.score}%"><span>${stock.score}</span></div>
        </div>
      </div>
      <div class="price-row">
        <span class="price">${formatPrice(stock)}</span>
        <strong class="change ${changeClass}">${sign}${stock.change.toFixed(1)}%</strong>
      </div>
      <canvas class="sparkline" width="440" height="128" data-spark="${stock.spark.join(",")}"></canvas>
      <div class="meta-row">
        <span class="freshness-badge ${stock.freshnessStatus}">数据 ${statusText(stock.freshnessStatus)}</span>
        <span class="confidence">证据 ${stock.truthScore}%</span>
      </div>
      <div class="mini-metrics">
        <span>成交额 ${formatCnyAmount(stock.metrics.avgAmountCny)}</span>
        <span>换手 ${stock.metrics.turnoverRate.toFixed(2)}%</span>
        <span>价差 ${stock.metrics.spreadBps}bp</span>
      </div>
      <div class="factor-list">
        ${Object.entries(stock.factors).map(([name, value]) => renderFactor(name, value)).join("")}
      </div>
      <ul class="reason-list">
        ${stock.reasons.slice(0, 2).map((reason) => `<li>${reason}</li>`).join("")}
      </ul>
      <button class="ghost-action" data-analyze="${stock.symbol}" type="button">查看分析</button>
    </article>
  `;
}

function renderFactor(name, value) {
  return `
    <div class="factor-row">
      <span>${name}</span>
      <div class="bar"><span style="width: ${value}%"></span></div>
      <strong>${value}</strong>
    </div>
  `;
}

function drawAllSparklines() {
  document.querySelectorAll(".sparkline").forEach((canvas) => {
    const points = canvas.dataset.spark.split(",").map(Number);
    drawSparkline(canvas, points);
  });
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
  const raw = String(symbol ?? "").trim();
  const normalized = raw.toUpperCase();
  let stock = stockByQuery(raw);
  if (!stock && raw && apiState.connected) {
    try {
      const params = new URLSearchParams({
        q: raw,
        market: activeMarket,
        account_id: apiState.accountId
      });
      const payload = await apiRequest(`/api/stocks/search?${params.toString()}`);
      const apiStocks = Array.isArray(payload.stocks) ? payload.stocks : [];
      apiStocks.map(normalizeApiStock).map((item) => enrichStock(item)).forEach((item) => {
        const index = stocks.findIndex((existing) => existing.symbol === item.symbol);
        if (index >= 0) stocks[index] = item;
        else stocks.push(item);
      });
      stock = apiStocks.length ? stockByQuery(apiStocks[0].symbol) : null;
      await loadSearchHistory();
    } catch (error) {
      apiState.lastError = `股票搜索失败：${error.message}`;
      updateBackendStatus(apiState.lastError);
    }
  }
  selectedSymbol = stock ? stock.symbol : normalized;
  renderCandidates();
  renderFavoriteRows();
  if (!stock) {
    renderUnknown(normalized);
    if (shouldOpenDrawer) openSingleDrawer();
    return;
  }
  renderDetails(stock);
  if (shouldOpenDrawer) openSingleDrawer();
}

function openSingleDrawer() {
  singleDrawer.hidden = false;
  document.body.classList.add("drawer-open");
}

function closeSingleDrawer() {
  singleDrawer.hidden = true;
  document.body.classList.remove("drawer-open");
}

function renderDetails(stock) {
  detailTitle.textContent = `${stock.symbol} · ${stock.name}`;
  detailAction.textContent = stock.action;
  detailAction.className = `action-pill drawer-action-pill ${stock.freshnessStatus}`;
  detailBody.innerHTML = `
    <div class="detail-grid">
      <div class="metric-box"><span>综合评分</span><strong>${stock.score}</strong></div>
      <div class="metric-box"><span>证据可信度</span><strong>${stock.truthScore}%</strong></div>
      <div class="metric-box"><span>数据时间</span><strong>${formatAsOf(stock.lagMinutes)}</strong></div>
    </div>
    ${renderPositionPanel(stock)}
    <p class="thesis">${stock.thesis}</p>
    <div class="uncertainty-list">
      ${renderUncertainty(stock)}
    </div>
    <div class="factor-detail-grid">
      ${Object.entries(stock.factors).map(([name, value]) => renderFactorTile(stock, name, value)).join("")}
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

function renderFactorTile(stock, name, value) {
  const detail = factorDetail(stock, name);
  return `
    <article class="factor-tile">
      <div class="factor-tile-top">
        <strong>${name}</strong>
        <span>${value}</span>
      </div>
      <p>${detail.summary}</p>
      <button class="mini-action" data-factor="${name}" type="button">详情</button>
    </article>
  `;
}

function factorDetail(stock, name) {
  const m = stock.metrics;
  const map = {
    基本面: {
      summary: `ROE ${m.roe.toFixed(1)}%，收入增速 ${m.revenueGrowth.toFixed(1)}%，自由现金流率 ${m.fcfMargin.toFixed(1)}%。`,
      source: "财务报表 / 结构化基本面 Mock",
      values: [
        ["ROE", `${m.roe.toFixed(1)}%`],
        ["收入增速", `${m.revenueGrowth.toFixed(1)}%`],
        ["自由现金流率", `${m.fcfMargin.toFixed(1)}%`],
        ["资产负债率", `${m.debtRatio.toFixed(1)}%`]
      ],
      process: "先按最新完整财报归一化，再与行业中位数和自身三年分位比较；缺财报时不能用记忆替代。"
    },
    估值: {
      summary: `PE ${m.pe.toFixed(1)}，PE历史分位 ${m.pePercentile}%，PB ${m.pb.toFixed(1)}。`,
      source: "最新价格 + 最新财务口径 Mock",
      values: [
        ["PE", m.pe.toFixed(1)],
        ["PE历史分位", `${m.pePercentile}%`],
        ["PB", m.pb.toFixed(1)],
        ["评分", stock.factors.估值]
      ],
      process: "价格必须取最新行情，盈利口径取最新可追溯财报；旧记忆只能提供上次估值分位作为对比。"
    },
    技术: {
      summary: `20日线偏离 ${m.ma20GapPct.toFixed(1)}%，量能 ${m.volumeRatio.toFixed(2)}倍，ATR ${m.atrPct.toFixed(1)}%。`,
      source: "K线 / 成交量 / 波动率 Mock",
      values: [
        ["20日线偏离", `${m.ma20GapPct.toFixed(1)}%`],
        ["量能倍数", `${m.volumeRatio.toFixed(2)}x`],
        ["ATR", `${m.atrPct.toFixed(1)}%`],
        ["60日最大回撤", `${m.maxDrawdown60d}%`]
      ],
      process: "必须重新读取历史K线和成交量，不能复用旧趋势结论；只复用上次关键价位作为比较点。"
    },
    催化: {
      summary: `催化评分 ${m.catalystScore}，72小时新闻 ${m.newsCount72h} 条，已验证比例 ${(m.verifiedCatalystRatio * 100).toFixed(0)}%。`,
      source: "公告 / 新闻 / 事件抽取 Mock",
      values: [
        ["催化评分", m.catalystScore],
        ["72小时新闻数", m.newsCount72h],
        ["已验证比例", `${(m.verifiedCatalystRatio * 100).toFixed(0)}%`],
        ["未证实比例", `${(m.unverifiedRatio * 100).toFixed(0)}%`]
      ],
      process: "先从公告和新闻抽 claim，再按来源等级、实体匹配和时效降权；C级来源不能单独触发买入。"
    },
    情绪: {
      summary: `情绪分 ${m.sentimentScore}，未证实比例 ${(m.unverifiedRatio * 100).toFixed(0)}%，72小时热度 ${m.newsCount72h}。`,
      source: "新闻情绪 / 社媒热度 Mock",
      values: [
        ["情绪分", m.sentimentScore],
        ["未证实比例", `${(m.unverifiedRatio * 100).toFixed(0)}%`],
        ["热度", m.newsCount72h],
        ["已验证催化", `${(m.verifiedCatalystRatio * 100).toFixed(0)}%`]
      ],
      process: "情绪只作为辅助。若未证实比例高，会降低结论强度，并要求补公告或公司来源。"
    },
    风险: {
      summary: `20日波动 ${m.volatility20d}%，60日最大回撤 ${m.maxDrawdown60d}%，ATR ${m.atrPct.toFixed(1)}%。`,
      source: "风险模型 / K线 / 公告风险 Mock",
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
  detailAction.textContent = "无法判断";
  detailAction.className = "action-pill drawer-action-pill stale";
  detailBody.innerHTML = `
    <div class="detail-grid">
      <div class="metric-box"><span>综合评分</span><strong>N/A</strong></div>
      <div class="metric-box"><span>证据可信度</span><strong>0%</strong></div>
      <div class="metric-box"><span>数据时间</span><strong>无数据</strong></div>
    </div>
    <p class="thesis">本地 mock 数据没有找到 ${escapeHTML(normalized)}。真实接口未接入时，系统拒绝生成买入或卖出结论。</p>
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
  requestAnimationFrame(drawPortfolioCurve);
  requestAnimationFrame(drawPositionKline);
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
  const favorites = [...favoriteSymbols].map(stockBySymbol).filter(Boolean);
  favoriteCount.textContent = `${favorites.length} 只`;
  favoriteGrid.innerHTML = favorites.length
    ? favorites.map(renderStockCard).join("")
    : `<div class="empty-state">还没有加入关注的股票。</div>`;
  requestAnimationFrame(drawAllSparklines);
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

function renderHealth() {
  healthGrid.innerHTML = healthSources.map((item) => `
    <article class="health-card">
      <div class="health-top">
        <strong>${item.name}</strong>
        <span class="freshness-badge ${item.status}">${statusText(item.status)}</span>
      </div>
      <p class="confidence">${escapeHTML(displayText(item.source))}</p>
      <p>${escapeHTML(displayText(item.text))}</p>
    </article>
  `).join("");
}

function renderDataSources() {
  if (!dataSourceGrid) return;
  const sources = dataSources.length ? dataSources : fallbackDataSources;
  const grouped = sources.reduce((map, source) => {
    const market = source.market;
    if (!map.has(market)) map.set(market, []);
    map.get(market).push(source);
    return map;
  }, new Map());
  const activeCount = sources.filter((source) => source.active).length;
  if (sourceSettingsStatus) {
    sourceSettingsStatus.textContent = apiState.connected
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
    <article class="source-card ${cardClass}" data-source-card="${source.id}">
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
        ${["tushare", "finnhub"].includes(source.provider) ? `<button class="ghost-action small" data-source-refresh="${source.provider}" type="button">刷新数据</button>` : ""}
      </div>
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

  const tests = sourceTestCatalog.tests ?? [];
  const activeCount = tests.filter((item) => item.active).length;
  sourceTestStatus.textContent = `${activeCount}/${tests.length} 可测试`;

  sourceTestSelect.innerHTML = tests.map((test) => `
    <option value="${escapeHTML(test.id)}" ${test.id === selectedSourceTestId ? "selected" : ""}>
      ${escapeHTML(displayText(test.label))}
    </option>
  `).join("");

  const grouped = tests.reduce((map, test) => {
    const group = test.source_kind_label || test.source_kind || "其他";
    if (!map.has(group)) map.set(group, []);
    map.get(group).push(test);
    return map;
  }, new Map());
  sourceTestList.innerHTML = [...grouped.entries()].map(([group, items]) => `
    <section class="source-test-group">
      <h4>${escapeHTML(displayText(group))}</h4>
      ${items.map(renderSourceTestItem).join("")}
    </section>
  `).join("");

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
              <tr>${visibleColumns.map((column) => renderResultCell(row?.[column], column)).join("")}</tr>
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

function renderResultCell(value, column = "") {
  const text = value === null || value === undefined ? "" : String(value);
  const href = text.startsWith("http://") || text.startsWith("https://");
  const display = displayCellValue(value, column);
  return href
    ? `<td><a class="source-link" href="${escapeHTML(text)}" target="_blank" rel="noreferrer">打开</a></td>`
    : `<td><div class="result-cell-clamp" title="${escapeHTML(display)}">${escapeHTML(display)}</div></td>`;
}

function selectedSourceTest() {
  return (sourceTestCatalog?.tests ?? []).find((item) => item.id === selectedSourceTestId);
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
      ${visibleColumns.map((column) => renderResultCell(row?.[column], column)).join("")}
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
      ${visibleColumns.map((column) => renderResultCell(row?.[column], column)).join("")}
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
    const label = provider === "finnhub" ? "Finnhub" : provider === "tushare" ? "Tushare" : provider;
    updateBackendStatus(`${label} 数据刷新中`);
    const payload = await apiRequest("/api/data/refresh", {
      method: "POST",
      body: JSON.stringify({ provider, scope: provider, account_id: apiState.accountId })
    });
    await loadAccountFromApi(apiState.accountId);
    const counts = payload.counts ?? {};
    updateBackendStatus(`${label} 已刷新：行情 ${counts.market_snapshots ?? 0}，财务 ${counts.financial_snapshots ?? 0}，新闻 ${counts.news_items ?? 0}`);
  } catch (error) {
    apiState.lastError = `真实数据刷新失败：${error.message}`;
    updateBackendStatus(apiState.lastError);
  }
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
  const nextFavorite = !favoriteSymbols.has(symbol);
  if (nextFavorite) favoriteSymbols.add(symbol);
  else favoriteSymbols.delete(symbol);
  renderCandidates();
  renderWatchlist();
  const stock = selectedStock();
  if (stock) renderDetails(stock);
  await persistFavorite(symbol, nextFavorite);
  renderCandidates();
  renderWatchlist();
  if (stock) renderDetails(stock);
}

function syncActiveNav() {
  const hashTarget = location.hash.slice(1);
  setActiveTab(navSectionIds.includes(hashTarget) ? hashTarget : activeTab, false);
}

function setActiveTab(current, shouldUpdateHash = true) {
  const next = navSectionIds.includes(current) ? current : "filters";
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
  requestAnimationFrame(() => {
    drawAllSparklines();
    drawPortfolioCurve();
    drawPositionKline();
    drawBacktestCurve();
  });
}

function setActiveNav(current) {
  document.querySelectorAll(".nav-item").forEach((link) => {
    link.classList.toggle("active", link.getAttribute("href") === `#${current}`);
  });
}

document.querySelectorAll(".segment").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".segment").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    activeMarket = button.dataset.market;
    renderCandidates();
  });
});

document.querySelectorAll("[data-filter-mode]").forEach((button) => {
  button.addEventListener("click", () => {
    filterMode = button.dataset.filterMode;
    syncFilterModeButtons();
    renderCandidates();
  });
});

filterGroups.addEventListener("change", (event) => {
  const checkbox = event.target.closest("[data-filter-id]");
  if (!checkbox) return;
  if (checkbox.checked) activeFilterIds.add(checkbox.dataset.filterId);
  else activeFilterIds.delete(checkbox.dataset.filterId);
  renderActiveRules();
  renderCandidates();
});

function handleStockGridClick(event) {
  const favoriteButton = event.target.closest("[data-favorite]");
  const button = event.target.closest("[data-analyze]");
  const card = event.target.closest(".stock-card");
  if (favoriteButton) toggleFavorite(favoriteButton.dataset.favorite);
  else if (button) selectStock(button.dataset.analyze);
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

detailBody.addEventListener("click", (event) => {
  const claimButton = event.target.closest("[data-claim-index]");
  const factorButton = event.target.closest("[data-factor]");
  const refreshButton = event.target.closest("[data-refresh-source]");
  const supplementButton = event.target.closest("[data-focus-supplement]");
  const addEvidenceButton = event.target.closest("#addEvidence");

  if (claimButton) openClaimDetail(Number(claimButton.dataset.claimIndex));
  else if (factorButton) openFactorDetail(factorButton.dataset.factor);
  else if (refreshButton) refreshStockData(refreshButton.dataset.refreshSource);
  else if (supplementButton) document.querySelector("#supplementText")?.focus();
  else if (addEvidenceButton) addSupplementEvidence();
});

document.querySelector("#runAnalysis").addEventListener("click", () => {
  void saveSearchHistory("stock_analysis", symbolInput.value);
  selectStock(symbolInput.value);
});

symbolInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    void saveSearchHistory("stock_analysis", symbolInput.value);
    selectStock(symbolInput.value);
  }
});

document.querySelector("#applyPromptFilter").addEventListener("click", applyNaturalLanguageFilter);

filterPrompt.addEventListener("keydown", (event) => {
  if (event.key === "Enter") applyNaturalLanguageFilter();
});

document.querySelector("#resetFilters").addEventListener("click", () => {
  activeFilterIds = new Set();
  filterPrompt.value = "";
  renderFilterGroups();
  renderCandidates();
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
  requestAnimationFrame(drawPositionKline);
});

toggleTradeDetails.addEventListener("click", () => {
  tradeDetailsOpen = !tradeDetailsOpen;
  tradeDetails.hidden = !tradeDetailsOpen;
  toggleTradeDetails.textContent = tradeDetailsOpen ? "收起流水和K线" : "展开流水和K线";
  toggleTradeDetails.setAttribute("aria-expanded", String(tradeDetailsOpen));
  if (tradeDetailsOpen) requestAnimationFrame(drawPositionKline);
});

tradeSymbol.addEventListener("change", syncTradePrice);
tradeForm.addEventListener("submit", handleTradeSubmit);

portfolioSummary.addEventListener("click", (event) => {
  if (event.target.closest("[data-refresh-profit]")) refreshPortfolioPrices();
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
  if (event.target.closest("[data-close-drawer]")) closeSingleDrawer();
});

document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  if (!modalShell.hidden) closeModal();
  else if (!singleDrawer.hidden) closeSingleDrawer();
});

document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-history-value]");
  if (!button) return;
  event.preventDefault();
  event.stopPropagation();
  applySearchHistoryValue(button.dataset.historySurface, button.dataset.historyValue);
});

window.addEventListener("hashchange", syncActiveNav);
window.addEventListener("load", () => {
  const hashTarget = location.hash.slice(1);
  setActiveTab(navSectionIds.includes(hashTarget) ? hashTarget : "filters", false);
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
renderFilterGroups();
syncFilterModeButtons();
populateTradeForm();
renderCandidates();
renderDetails(stocks[0]);
renderWatchlist();
renderHealth();
renderStockAnomalyReport(selectedAnomalySymbol);
renderBacktestResult();
setActiveTab(navSectionIds.includes(location.hash.slice(1)) ? location.hash.slice(1) : "filters", false);
updateBackendStatus();
loadAccountFromApi();

if ("serviceWorker" in navigator && location.protocol !== "file:") {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/service-worker.js").catch((error) => {
      apiState.lastError = `PWA 缓存注册失败：${error.message}`;
      updateBackendStatus(apiState.lastError);
    });
  });
}
