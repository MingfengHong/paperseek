const form = document.getElementById("searchForm");
const workflow = document.getElementById("workflow");
const logOutput = document.getElementById("logOutput");
const runId = document.getElementById("runId");
const stateLabel = document.getElementById("stateLabel");
const stepLabel = document.getElementById("stepLabel");
const searchButton = document.getElementById("searchButton");
const stopButton = document.getElementById("stopButton");
const dataSourceSelect = document.getElementById("dataSource");
const providerSelect = document.getElementById("llmProvider");
const apiTypeSelect = document.getElementById("llmApiType");
const modelInput = document.getElementById("llmModel");
const baseUrlInput = document.getElementById("llmBaseUrl");
const exportLogButton = document.getElementById("exportLogButton");
const exportCsvButton = document.getElementById("exportCsvButton");
const checkConfigButton = document.getElementById("checkConfigButton");
const viewTabs = [...document.querySelectorAll(".mode-tabs .tab")];
const basicSourceName = document.getElementById("basicSourceName");
const basicSourceMeta = document.getElementById("basicSourceMeta");
const advancedSettings = document.getElementById("advancedSettings");
const configAlert = document.getElementById("configAlert");
const configAlertTitle = document.getElementById("configAlertTitle");
const configAlertMessage = document.getElementById("configAlertMessage");
const configAlertList = document.getElementById("configAlertList");
const configAlertCloseButton = document.getElementById("configAlertCloseButton");
const configAlertAdvancedButton = document.getElementById("configAlertAdvancedButton");
const languageButtons = [...document.querySelectorAll("[data-language]")];
const languageStorageKey = "paperseek.ui.language";

const translations = {
  zh: {
    "LLM based Literature Search Agent": "基于大模型的文献检索助手",
    "Search": "检索",
    "Results": "结果",
    "Citation Map": "引用图谱",
    "History": "历史",
    "Export Results CSV": "导出结果 CSV",
    "Export Log": "导出日志",
    "Ready": "就绪",
    "Processing": "处理中",
    "Searching": "检索中",
    "Stopping": "停止中",
    "Stopped": "已停止",
    "Error": "错误",
    "Research Question": "研究问题",
    "Paste a research question, gap paragraph, or plain language search intent.": "粘贴研究问题、研究空白段落，或用自然语言描述检索意图。",
    "Run Search": "开始检索",
    "Stop": "停止",
    "Check Config": "检查配置",
    "Configuration": "配置",
    "Model API and source": "模型 API 与数据源",
    "Session only": "仅本次会话",
    "Model API": "模型 API",
    "Provider": "服务商",
    "API Key": "API Key",
    "Model": "模型",
    "Source": "数据源",
    "OpenAlex": "OpenAlex",
    "OpenAlex (precise search)": "OpenAlex（精确检索）",
    "Crossref (metadata / DOI registry)": "Crossref（元数据 / DOI 注册库）",
    "Web of Science Starter (temporarily unavailable)": "Web of Science Starter（暂不可用）",
    "Optional source keys are in Advanced settings.": "可选数据源 Key 在高级设置中。",
    "Optional OpenAlex API key and email are in Advanced settings.": "可选 OpenAlex API Key 和邮箱在高级设置中。",
    "Crossref email is optional but recommended in Advanced settings.": "Crossref 邮箱可选，但建议在高级设置中填写。",
    "WoS requires an API key in Advanced settings.": "WoS 需要在高级设置中填写 API Key。",
    "Source details are in Advanced settings.": "数据源详情在高级设置中。",
    "Advanced settings": "高级设置",
    "Protocol, source keys, and run controls": "协议、数据源 Key 和运行控制",
    "Model protocol": "模型协议",
    "API Type": "API 类型",
    "OpenAI Responses API": "OpenAI Responses API",
    "OpenAI Chat Completions API": "OpenAI Chat Completions API",
    "Anthropic Messages API": "Anthropic Messages API",
    "Base URL": "Base URL",
    "Provider default, editable for compatible endpoints": "服务商默认地址，可为兼容端点修改",
    "Source settings": "数据源设置",
    "Data Source": "数据源",
    "OpenAlex API Key": "OpenAlex API Key",
    "Optional if anonymous access is available": "匿名访问可用时可选",
    "OpenAlex Email": "OpenAlex 邮箱",
    "Optional polite-pool email": "可选 polite-pool 邮箱",
    "Crossref Email": "Crossref 邮箱",
    "WoS API Key": "WoS API Key",
    "WoS DB": "WoS 数据库",
    "Field Hint": "领域提示",
    "Optional discipline": "可选学科领域",
    "Run controls": "运行控制",
    "Min Results": "最少结果",
    "Max Results": "最多结果",
    "Iterations": "迭代次数",
    "Try external abstracts": "尝试外部摘要",
    "Expand citations": "扩展引用",
    "System Dashboard": "系统面板",
    "idle": "空闲",
    "Configuration check": "配置检查",
    "Configuration failed": "配置失败",
    "Configuration check failed": "配置检查失败",
    "PaperSeek found a configuration issue.": "PaperSeek 发现配置问题。",
    "Open Advanced Settings": "打开高级设置",
    "Close": "关闭",
    "Query Generation": "查询生成",
    "LLM will translate the research question into a source-specific search query.": "LLM 会把研究问题转换成适配数据源的检索式。",
    "No query generated yet.": "尚未生成检索式。",
    "Source Request": "数据源请求",
    "The selected database will be queried and adjusted by result counts.": "系统会查询所选数据库，并根据结果数量调整检索式。",
    "No source request has run.": "尚未请求数据源。",
    "Metadata Ranking": "元数据排序",
    "Returned records will be ranked with available metadata and abstracts when present.": "返回记录会基于可用元数据和摘要进行排序。",
    "No ranking request has run.": "尚未执行排序。",
    "Literature Results": "文献结果",
    "Final ranked papers will appear here.": "最终排序后的论文会显示在这里。",
    "Run a search to populate the result list.": "运行检索后会填充结果列表。",
    "WAITING": "等待中",
    "PROCESSING": "处理中",
    "COMPLETE": "已完成",
    "READY": "就绪",
    "EMPTY": "空",
    "ERROR": "错误",
    "Calling the LLM to generate a source-specific query.": "正在调用 LLM 生成适配数据源的检索式。",
    "No query returned": "未返回检索式",
    "CANDIDATES": "候选",
    "RANKED RECORDS": "已排序记录",
    "RANKING STATUS": "排序状态",
    "SOURCE": "数据源",
    "TOTAL RECORDS": "总记录",
    "TOP SCORE": "最高分",
    "CANDIDATES SCORED": "已评分候选",
    "CITATION ADDS": "引用新增",
    "Review Results": "查看结果",
    "Open Citation Map": "打开引用图谱",
    "Input Required": "需要输入",
    "Fill the required field and run the search again.": "请填写必填字段后重新运行检索。",
    "Search Failed": "检索失败",
    "The local backend or upstream service returned an error.": "本地后端或上游服务返回错误。",
    "Search Stopped": "检索已停止",
    "The request was stopped before completion.": "请求在完成前已停止。",
    "No final result was produced for this run.": "本次运行没有生成最终结果。",
    "Research Question is required.": "请填写研究问题。",
    "WoS API Key is required for WoS searches.": "WoS 检索需要 WoS API Key。",
    "LLM API Key is required for this provider.": "当前服务商需要 LLM API Key。",
    "API Type is required.": "请填写 API 类型。",
    "Min Results and Max Results must be numbers.": "最少结果和最多结果必须是数字。",
    "Min Results cannot exceed Max Results.": "最少结果不能大于最多结果。",
    "Iterations must be at least 1.": "迭代次数至少为 1。",
    "Configuration check started.": "配置检查已开始。",
    "Fix the items below before running a search.": "请先修复以下项目，再运行检索。",
    "PaperSeek could not complete the configuration check.": "PaperSeek 无法完成配置检查。",
    "Configuration check failed.": "配置检查失败。",
    "Review the required model and source settings, then run Check Config again.": "检查必需的模型和数据源设置，然后再次运行检查配置。",
    "TARGET_MIN cannot exceed TARGET_MAX.": "TARGET_MIN 不能大于 TARGET_MAX。",
    "Lower TARGET_MIN or raise TARGET_MAX.": "降低 TARGET_MIN 或提高 TARGET_MAX。",
    "LLM_BASE_URL is empty; provider defaults will be used when available.": "LLM_BASE_URL 为空；可用时将使用服务商默认地址。",
    "Waiting for the first source response.": "正在等待首次数据源响应。",
    "Current query": "当前检索式",
    "Candidate preview": "候选预览",
    "No ranked papers returned.": "未返回排序论文。",
    "No author metadata": "无作者元数据",
    "Open source record": "打开来源记录",
    "Open PDF": "打开 PDF",
    "Keywords:": "关键词：",
    "Citations:": "引用数：",
    "Abstract:": "摘要：",
    "Reasoning:": "排序理由：",
    "Ranked literature": "排序文献",
    "Run a search before reviewing results.": "请先运行检索，再查看结果。",
    "Search title, author, abstract, DOI": "搜索题名、作者、摘要、DOI",
    "All scores": "全部分数",
    "Score >= 7": "分数 >= 7",
    "Score >= 8": "分数 >= 8",
    "Score >= 9": "分数 >= 9",
    "All metadata": "全部元数据",
    "Has abstract": "有摘要",
    "Has DOI": "有 DOI",
    "Has PDF": "有 PDF",
    "Sort by rank": "按排名排序",
    "Sort by score": "按分数排序",
    "Sort by citations": "按引用数排序",
    "Sort by year": "按年份排序",
    "Select all shown": "选择当前全部",
    "Clear": "清空",
    "No papers match the current filters.": "没有论文匹配当前筛选。",
    "Select paper": "选择论文",
    "Local history is disabled": "本地历史记录已禁用",
    "Loading saved runs.": "正在加载保存的运行。",
    "Loading saved runs...": "正在加载保存的运行...",
    "No saved search runs yet.": "还没有保存的检索运行。",
    "Local search records": "本地检索记录",
    "Refresh": "刷新",
    "Select a saved run to inspect query, events, and ranked papers.": "选择一个保存的运行，查看检索式、事件和排序论文。",
    "source pending": "数据源待定",
    "Final query": "最终检索式",
    "Open Results": "打开结果",
    "Delete": "删除",
    "Recent log events": "最近日志事件",
    "No event log was saved for this run.": "本次运行未保存事件日志。",
    "This run did not save ranked papers.": "本次运行未保存排序论文。",
    "No citation graph nodes are available for this run.": "本次运行没有可用的引用图谱节点。",
    "Citation expansion": "引用扩展",
    "INITIAL CANDIDATES": "初始候选",
    "SEED PAPERS": "种子论文",
    "ADDED CANDIDATES": "新增候选",
    "PROMOTED RESULTS": "提升为结果",
    "Result": "结果",
    "Seed": "种子",
    "Forward citation": "前向引用",
    "Backward reference": "后向参考文献",
    "Reset": "重置",
    "All seeds": "全部种子",
    "Seed papers": "种子论文",
    "Select a node to inspect its metadata.": "选择一个节点以查看元数据。",
    "No seed papers were recorded.": "没有记录种子论文。",
    "Run an OpenAlex search with citation expansion enabled before exploring citations.": "请先运行启用引用扩展的 OpenAlex 检索，再查看引用图谱。",
    "Citation expansion was disabled for this run.": "本次运行未启用引用扩展。",
    "Citation traversal is currently available for OpenAlex runs only.": "引用遍历目前仅适用于 OpenAlex 运行。",
    "Score:": "分数：",
    "Rank:": "排名：",
    "Open record": "打开记录",
    "Record": "记录",
    "PDF": "PDF",
    "Submitting request to local backend.": "正在向本地后端提交请求。",
    "Search stopped by user.": "检索已由用户停止。",
    "Stop requested.": "已请求停止。",
    "Unknown error": "未知错误",
    "Ready. Keys and endpoint settings are held only in this browser session.": "就绪。Key 和端点设置仅保存在本次浏览器会话中。",
    "Optional for local Ollama": "本地 Ollama 可选",
    "Configured via environment": "已通过环境变量配置",
  },
};

const providerDefaults = {
  openai: { model: "gpt-5.4-mini", apiType: "openai_responses", baseUrl: "https://api.openai.com/v1" },
  anthropic: { model: "claude-sonnet-4-6", apiType: "anthropic_messages", baseUrl: "https://api.anthropic.com" },
  google: { model: "gemini-3.5-flash", apiType: "openai_chat", baseUrl: "https://generativelanguage.googleapis.com/v1beta/openai" },
  deepseek: { model: "deepseek-v4-flash", apiType: "openai_chat", baseUrl: "https://api.deepseek.com" },
  cstcloud: { model: "DeepSeek-V4-Flash", apiType: "openai_chat", baseUrl: "https://uni-api.cstcloud.cn/v1" },
  dashscope: { model: "qwen3.6-plus", apiType: "openai_chat", baseUrl: "https://dashscope.aliyuncs.com/compatible-mode/v1" },
  moonshot: { model: "kimi-k2.6", apiType: "openai_chat", baseUrl: "https://api.moonshot.ai/v1" },
  zhipu: { model: "glm-5.1", apiType: "openai_chat", baseUrl: "https://open.bigmodel.cn/api/paas/v4" },
  siliconflow: { model: "deepseek-ai/DeepSeek-V4-Flash", apiType: "openai_chat", baseUrl: "https://api.siliconflow.cn/v1" },
  openrouter: { model: "openai/gpt-5.4-mini", apiType: "openai_chat", baseUrl: "https://openrouter.ai/api/v1" },
  volcengine: { model: "doubao-seed-2-0-mini-260428", apiType: "openai_chat", baseUrl: "https://ark.cn-beijing.volces.com/api/v3" },
  hunyuan: { model: "hunyuan-turbos-latest", apiType: "openai_chat", baseUrl: "https://tokenhub.tencentmaas.com/v1" },
  qianfan: { model: "ernie-5.0", apiType: "openai_chat", baseUrl: "https://qianfan.baidubce.com/v2" },
  modelscope: { model: "Qwen/Qwen3-235B-A22B-Instruct-2507", apiType: "openai_chat", baseUrl: "https://api-inference.modelscope.cn/v1" },
  ollama: { model: "qwen3:8b", apiType: "openai_chat", baseUrl: "http://127.0.0.1:11434/v1" },
  custom: { model: "", apiType: "openai_chat", baseUrl: "" },
};

const stageOrder = ["query", "search", "ranking", "results"];
const sourceLabels = {
  openalex: "OpenAlex (precise search)",
  crossref: "Crossref (metadata / DOI registry)",
  wos: "Web of Science Starter (temporarily unavailable)",
};
const compactSourceLabels = {
  openalex: "OpenAlex",
  crossref: "Crossref",
  wos: "Web of Science Starter",
};
const sourceMetaLabels = {
  openalex: "Optional OpenAlex API key and email are in Advanced settings.",
  crossref: "Crossref email is optional but recommended in Advanced settings.",
  wos: "WoS requires an API key in Advanced settings.",
};

let workflowState = createWorkflowState();
let latestPayload = null;
let latestResult = null;
let latestError = "";
let activeView = "search";
let selectedPaperIds = new Set();
let resultFilters = {
  query: "",
  minScore: "all",
  availability: "all",
  sort: "rank",
};
let selectedCitationNodeId = "";
let resultSearchTimer = null;
let citationGraphState = createCitationGraphState();
let historyRuns = [];
let historyDetail = null;
let historyStatus = { enabled: true, path: "" };
let historyLoading = false;
let historyError = "";
let activeSearchController = null;
let environmentConfig = {
  has_llm_api_key: false,
  has_wos_api_key: false,
  llm_provider: "",
};
let activeLanguage = loadLanguage();

function loadLanguage() {
  const saved = window.localStorage ? window.localStorage.getItem(languageStorageKey) : "";
  return saved === "zh" ? "zh" : "en";
}

function translatedText(text) {
  const value = String(text ?? "");
  if (activeLanguage !== "zh") {
    return value;
  }
  return translations.zh[value] || value;
}

function translateWithWhitespace(value) {
  const text = String(value ?? "");
  const match = text.match(/^(\s*)(.*?)(\s*)$/s);
  if (!match) {
    return translatedText(text);
  }
  return `${match[1]}${translatedText(match[2])}${match[3]}`;
}

function setTranslatedText(node, englishText) {
  if (!node) {
    return;
  }
  node.dataset.i18nText = englishText;
  node.textContent = translatedText(englishText);
}

function translatedAttrName(attribute) {
  return `data-i18n-${attribute}-original`;
}

function setTranslatedAttribute(node, attribute, englishText) {
  if (!node) {
    return;
  }
  node.setAttribute(translatedAttrName(attribute), englishText);
  node.setAttribute(attribute, translatedText(englishText));
}

function shouldSkipTranslationNode(node) {
  const parent = node.parentElement;
  return !parent || Boolean(parent.closest("script, style, pre, code, textarea, [data-no-i18n], [data-i18n-text]"));
}

function applyLanguage(root = document.body) {
  if (!root) {
    return;
  }
  document.documentElement.lang = activeLanguage === "zh" ? "zh-CN" : "en";
  document.body.dataset.uiLanguage = activeLanguage;
  languageButtons.forEach((button) => {
    const active = button.dataset.language === activeLanguage;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", active ? "true" : "false");
  });

  const elementRoot = root.nodeType === Node.ELEMENT_NODE ? root : document.body;
  const dynamicElements = [];
  if (elementRoot.matches && elementRoot.matches("[data-i18n-text]")) {
    dynamicElements.push(elementRoot);
  }
  if (elementRoot.querySelectorAll) {
    dynamicElements.push(...elementRoot.querySelectorAll("[data-i18n-text]"));
  }
  dynamicElements.forEach((node) => {
    node.textContent = translatedText(node.dataset.i18nText || "");
  });

  const attributes = ["placeholder", "title", "aria-label"];
  const attrElements = elementRoot.querySelectorAll ? [elementRoot, ...elementRoot.querySelectorAll("*")] : [];
  attrElements.forEach((node) => {
    attributes.forEach((attribute) => {
      if (!node.hasAttribute || !node.hasAttribute(attribute)) {
        return;
      }
      const originalName = translatedAttrName(attribute);
      if (!node.hasAttribute(originalName)) {
        node.setAttribute(originalName, node.getAttribute(attribute));
      }
      node.setAttribute(attribute, translatedText(node.getAttribute(originalName)));
    });
  });

  const walkerRoot = root.nodeType === Node.TEXT_NODE ? root.parentNode : root;
  if (!walkerRoot) {
    return;
  }
  const walker = document.createTreeWalker(walkerRoot, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const node = walker.currentNode;
    if (shouldSkipTranslationNode(node) || !node.nodeValue.trim()) {
      continue;
    }
    if (!node.__paperseekI18nOriginal) {
      node.__paperseekI18nOriginal = node.nodeValue;
    }
    node.nodeValue = translateWithWhitespace(node.__paperseekI18nOriginal);
  }
}

function setLanguage(language) {
  activeLanguage = language === "zh" ? "zh" : "en";
  if (window.localStorage) {
    window.localStorage.setItem(languageStorageKey, activeLanguage);
  }
  applyLanguage();
  if (activeView === "history") {
    setTranslatedText(stepLabel, "History");
  } else {
    renderStepLabel();
  }
  updateSourceSummary();
  updateCredentialPlaceholders();
}

function initLanguageControls() {
  languageButtons.forEach((button) => {
    button.addEventListener("click", () => setLanguage(button.dataset.language));
  });
  applyLanguage();
}

const fallbackTimeZone = "Asia/Shanghai";
const clientTimeZone = detectClientTimeZone();

function detectClientTimeZone() {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || fallbackTimeZone;
  } catch (_) {
    return fallbackTimeZone;
  }
}

function clientUtcOffsetMinutes() {
  if (clientTimeZone === fallbackTimeZone) {
    return 8 * 60;
  }
  try {
    return -new Date().getTimezoneOffset();
  } catch (_) {
    return 8 * 60;
  }
}

function zonedDateParts(date = new Date()) {
  try {
    const parts = new Intl.DateTimeFormat("en-GB", {
      timeZone: clientTimeZone,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    }).formatToParts(date);
    return Object.fromEntries(parts.map((part) => [part.type, part.value]));
  } catch (_) {
    const fallback = new Date(date.getTime() + 8 * 60 * 60 * 1000);
    return {
      year: String(fallback.getUTCFullYear()),
      month: String(fallback.getUTCMonth() + 1).padStart(2, "0"),
      day: String(fallback.getUTCDate()).padStart(2, "0"),
      hour: String(fallback.getUTCHours()).padStart(2, "0"),
      minute: String(fallback.getUTCMinutes()).padStart(2, "0"),
      second: String(fallback.getUTCSeconds()).padStart(2, "0"),
    };
  }
}

function nowStamp() {
  const parts = zonedDateParts();
  return `${parts.hour}:${parts.minute}:${parts.second}`;
}

function dateStamp() {
  const parts = zonedDateParts();
  return `${parts.year}${parts.month}${parts.day}-${parts.hour}${parts.minute}`;
}

function log(message) {
  logOutput.textContent += `${nowStamp()}  ${message}\n`;
  logOutput.scrollTop = logOutput.scrollHeight;
  updateExportButtons();
}

function setBusy(isBusy) {
  searchButton.disabled = isBusy;
  checkConfigButton.disabled = isBusy;
  if (stopButton) {
    stopButton.disabled = !isBusy;
  }
  setTranslatedText(searchButton.querySelector("span"), isBusy ? "Searching" : "Run Search");
  if (isBusy) {
    setTranslatedText(stateLabel, "Processing");
  } else if (!["Error", "Stopped"].includes(stateLabel.dataset.i18nText || stateLabel.textContent)) {
    setTranslatedText(stateLabel, "Ready");
  }
  document.body.classList.toggle("is-busy", isBusy);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function getValue(id) {
  return document.getElementById(id).value.trim();
}

function getNumber(id) {
  return Number(document.getElementById(id).value);
}

function updateSourceSummary() {
  const source = dataSourceSelect.value || "openalex";
  if (basicSourceName) {
    setTranslatedText(basicSourceName, compactSourceLabels[source] || source.toUpperCase());
  }
  if (basicSourceMeta) {
    setTranslatedText(basicSourceMeta, sourceMetaLabels[source] || "Source details are in Advanced settings.");
  }
}

function envLlmKeyApplies(provider = providerSelect.value) {
  return Boolean(environmentConfig.has_llm_api_key && (!environmentConfig.llm_provider || environmentConfig.llm_provider === provider));
}

function updateCredentialPlaceholders() {
  const llmKeyInput = document.getElementById("llmApiKey");
  const wosKeyInput = document.getElementById("wosApiKey");
  const openAlexKeyInput = document.getElementById("openAlexApiKey");
  if (llmKeyInput) {
    if (providerSelect.value === "ollama") {
      setTranslatedAttribute(llmKeyInput, "placeholder", "Optional for local Ollama");
    } else if (envLlmKeyApplies(providerSelect.value)) {
      setTranslatedAttribute(llmKeyInput, "placeholder", "Configured via environment");
    } else {
      setTranslatedAttribute(llmKeyInput, "placeholder", "");
    }
  }
  if (wosKeyInput && environmentConfig.has_wos_api_key) {
    setTranslatedAttribute(wosKeyInput, "placeholder", "Configured via environment");
  }
  if (openAlexKeyInput && environmentConfig.has_openalex_api_key) {
    setTranslatedAttribute(openAlexKeyInput, "placeholder", "Configured via environment");
  }
}

async function loadServerDefaults() {
  try {
    const response = await fetch("/api/config/defaults");
    if (!response.ok) {
      return;
    }
    const data = await response.json();
    environmentConfig = { ...environmentConfig, ...data };
    if (data.data_source) {
      dataSourceSelect.value = data.data_source;
    }
    if (data.llm_provider && providerDefaults[data.llm_provider]) {
      providerSelect.value = data.llm_provider;
    }
    if (data.llm_api_type) {
      apiTypeSelect.value = data.llm_api_type;
    }
    if (data.llm_model) {
      modelInput.value = data.llm_model;
    }
    if (data.llm_base_url) {
      baseUrlInput.value = data.llm_base_url;
    }
    if (Number.isFinite(Number(data.target_min))) {
      document.getElementById("targetMin").value = Number(data.target_min);
    }
    if (Number.isFinite(Number(data.target_max))) {
      document.getElementById("targetMax").value = Number(data.target_max);
    }
    if (Number.isFinite(Number(data.max_iterations))) {
      document.getElementById("maxIterations").value = Number(data.max_iterations);
    }
    document.getElementById("fetchAbstracts").checked = Boolean(data.fetch_abstracts);
    document.getElementById("expandCitations").checked = Boolean(data.expand_citations);
    updateSourceFields();
    updateCredentialPlaceholders();
    updateSourceSummary();
  } catch (_) {
    updateCredentialPlaceholders();
    updateSourceSummary();
  }
}

function createCitationGraphState() {
  return {
    scale: 1,
    panX: 0,
    panY: 0,
    positions: {},
    draggingNodeId: "",
    panning: false,
    lastX: 0,
    lastY: 0,
    dragOffsetX: 0,
    dragOffsetY: 0,
  };
}

function paperId(paper) {
  return String(paper.uid || paper.doi || paper.title || paper.rank || "");
}

function selectedPapers() {
  const papers = latestResult && latestResult.ranked ? latestResult.ranked : [];
  return papers.filter((paper) => selectedPaperIds.has(paperId(paper)));
}

function getFilteredPapers() {
  const papers = latestResult && latestResult.ranked ? [...latestResult.ranked] : [];
  const query = resultFilters.query.trim().toLowerCase();
  let filtered = papers.filter((paper) => {
    if (query) {
      const haystack = [
        paper.title,
        (paper.authors || []).join(" "),
        paper.abstract,
        paper.source,
        paper.doi,
        paper.keywords,
      ].join(" ").toLowerCase();
      if (!haystack.includes(query)) {
        return false;
      }
    }
    if (resultFilters.minScore !== "all" && Number(paper.score || 0) < Number(resultFilters.minScore)) {
      return false;
    }
    if (resultFilters.availability === "abstract" && !paper.abstract) {
      return false;
    }
    if (resultFilters.availability === "doi" && !paper.doi) {
      return false;
    }
    if (resultFilters.availability === "pdf" && !(paper.links && paper.links.pdf)) {
      return false;
    }
    return true;
  });

  const numeric = (value) => Number(value || 0);
  filtered.sort((a, b) => {
    if (resultFilters.sort === "score") {
      return numeric(b.score) - numeric(a.score);
    }
    if (resultFilters.sort === "citations") {
      return numeric(b.citations) - numeric(a.citations);
    }
    if (resultFilters.sort === "year") {
      return numeric(b.publish_year) - numeric(a.publish_year);
    }
    return numeric(a.rank) - numeric(b.rank);
  });
  return filtered;
}

function getExportPapers() {
  const selected = selectedPapers();
  return selected.length ? selected : getFilteredPapers();
}

function updateExportButtons() {
  if (exportLogButton) {
    exportLogButton.disabled = !logOutput.textContent.trim();
  }
  if (exportCsvButton) {
    exportCsvButton.disabled = getExportPapers().length === 0;
  }
}

function filenamePart(value, fallback = "literature-search") {
  const text = String(value || fallback);
  const raw = (typeof text.normalize === "function" ? text.normalize("NFKC") : text).trim();
  let cleaned = "";
  try {
    const nonWord = new RegExp("[^\\p{L}\\p{N}]+", "gu");
    cleaned = raw.replace(nonWord, "-").replace(/^-+|-+$/g, "");
  } catch (_) {
    cleaned = raw
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "");
  }
  return cleaned.slice(0, 64) || fallback;
}

function exportQuestionTheme() {
  return (latestPayload && latestPayload.question) ||
    (latestResult && latestResult.question) ||
    getValue("question") ||
    "literature-search";
}

function downloadText(filename, content, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function currentLogText() {
  const source = latestPayload && latestPayload.data_source ? latestPayload.data_source : "not started";
  return [
    `Exported at: ${new Date().toISOString()}`,
    `Run ID: ${runId.textContent}`,
    `Source: ${source}`,
    "",
    logOutput.textContent.trimEnd(),
    "",
  ].join("\n");
}

function csvCell(value) {
  const text = Array.isArray(value) ? value.join("; ") : String(value ?? "");
  return `"${text.replaceAll('"', '""')}"`;
}

function papersToCsv(papers) {
  const columns = [
    "rank",
    "score",
    "title",
    "authors",
    "publish_year",
    "source",
    "provider",
    "document_types",
    "citations",
    "doi",
    "keywords",
    "abstract",
    "reasoning",
    "record_url",
    "pdf_url",
  ];
  const rows = (papers || []).map((paper, index) => [
    index + 1,
    paper.score,
    paper.title,
    paper.authors || [],
    paper.publish_year,
    paper.source,
    paper.provider,
    paper.document_types || [],
    paper.citations,
    paper.doi,
    paper.keywords,
    paper.abstract,
    paper.reasoning,
    paper.links && paper.links.record,
    paper.links && paper.links.pdf,
  ].map(csvCell).join(","));
  return `\ufeff${[columns.join(","), ...rows].join("\r\n")}`;
}

function clearValidationState() {
  for (const node of document.querySelectorAll(".is-invalid")) {
    node.classList.remove("is-invalid");
  }
}

function createWorkflowState() {
  return {
    query: {
      number: "01",
      title: "Query Generation",
      status: "WAITING",
      description: "LLM will translate the research question into a source-specific search query.",
      body: emptyState("No query generated yet."),
    },
    search: {
      number: "02",
      title: "Source Request",
      status: "WAITING",
      description: "The selected database will be queried and adjusted by result counts.",
      body: emptyState("No source request has run."),
    },
    ranking: {
      number: "03",
      title: "Metadata Ranking",
      status: "WAITING",
      description: "Returned records will be ranked with available metadata and abstracts when present.",
      body: emptyState("No ranking request has run."),
    },
    results: {
      number: "04",
      title: "Literature Results",
      status: "WAITING",
      description: "Final ranked papers will appear here.",
      body: emptyState("Run a search to populate the result list."),
    },
  };
}

function workflowCard(number, title, status, description, body, extraClass = "") {
  return `
    <article class="workflow-card ${extraClass}">
      <div class="card-topline">
        <div class="card-title"><span>${number}</span><h3>${escapeHtml(title)}</h3></div>
        <span class="status-badge ${status.toLowerCase().replaceAll(" ", "-")}">${escapeHtml(status)}</span>
      </div>
      <p class="card-description">${escapeHtml(description)}</p>
      ${body}
    </article>
  `;
}

function renderWorkflow() {
  if (activeView === "results") {
    workflow.innerHTML = renderResultsView();
    applyLanguage(workflow);
    renderStepLabel();
    return;
  }
  if (activeView === "citations") {
    workflow.innerHTML = renderCitationView();
    applyLanguage(workflow);
    renderStepLabel();
    renderCitationGraph();
    return;
  }
  if (activeView === "history") {
    workflow.innerHTML = renderHistoryView();
    applyLanguage(workflow);
    setTranslatedText(stepLabel, "History");
    return;
  }

  workflow.innerHTML = stageOrder.map((key) => {
    const item = workflowState[key];
    const extra = item.status === "PROCESSING" ? "processing-card" : item.status === "ERROR" ? "error-card" : "";
    return workflowCard(item.number, item.title, item.status, item.description, item.body, extra);
  }).join("");

  applyLanguage(workflow);
  renderStepLabel();
}

function renderStepLabel() {
  const activeIndex = stageOrder.findIndex((key) => workflowState[key].status === "PROCESSING");
  if (activeIndex >= 0) {
    stepLabel.textContent = activeLanguage === "zh" ? `步骤 ${activeIndex + 1}/4` : `Step ${activeIndex + 1}/4`;
  } else if (workflowState.results.status === "READY" || workflowState.results.status === "EMPTY") {
    stepLabel.textContent = activeLanguage === "zh" ? "步骤 4/4" : "Step 4/4";
  } else {
    stepLabel.textContent = activeLanguage === "zh" ? "步骤 0/4" : "Step 0/4";
  }
}

function switchView(view) {
  activeView = view;
  document.body.dataset.view = view;
  viewTabs.forEach((tab) => {
    const isActive = tab.dataset.view === view;
    tab.classList.toggle("active", isActive);
    tab.classList.toggle("muted", !isActive);
  });
  renderWorkflow();
  if (view === "history") {
    loadHistoryRuns();
  }
}

function emptyState(text) {
  return `<div class="empty-state">${escapeHtml(text)}</div>`;
}

function chipList(items) {
  return `<div class="chip-list">${items.map((item) => `<span>${escapeHtml(item)}</span>`).join("")}</div>`;
}

function metricRow(items) {
  return `<div class="metric-row">${items.map((item) => `
    <div>
      <strong>${escapeHtml(item.value)}</strong>
      <span>${escapeHtml(item.label)}</span>
    </div>
  `).join("")}</div>`;
}

function renderHistory(history, finalQuery, preview) {
  const rows = history && history.length ? `
    <div class="iteration-list">
      ${history.map((row) => `
        <section class="iteration-row">
          <div class="iteration-meta">
            <strong>Iteration ${escapeHtml(row.iteration)}</strong>
            <span class="action-pill ${escapeHtml(row.action)}">${escapeHtml(row.action)}</span>
            <span>${row.total === null || row.total === undefined ? "No count" : `${escapeHtml(row.total)} records`}</span>
          </div>
          <code>${escapeHtml(row.query)}</code>
          <p>${escapeHtml(row.message || "")}</p>
          ${row.next_query ? `<div class="next-query"><span>Next query</span><code>${escapeHtml(row.next_query)}</code></div>` : ""}
        </section>
      `).join("")}
    </div>
  ` : emptyState("Waiting for the first source response.");

  const candidates = renderCandidatePreview(preview);
  const queryBlock = finalQuery ? `
    <div class="final-query">
      <span>Current query</span>
      <code>${escapeHtml(finalQuery)}</code>
    </div>
  ` : "";

  return `${rows}${queryBlock}${candidates}`;
}

function renderCandidatePreview(preview) {
  if (!preview || preview.length === 0) {
    return "";
  }
  return `
    <div class="candidate-preview">
      <span>Candidate preview</span>
      ${preview.map((paper) => `
        <div class="candidate-row">
          <strong>${escapeHtml(paper.title || "(no title)")}</strong>
          <small>${escapeHtml([paper.year, paper.source, paper.provider].filter(Boolean).join(" | "))}</small>
        </div>
      `).join("")}
    </div>
  `;
}

function renderPapers(papers) {
  if (!papers || papers.length === 0) {
    return emptyState("No ranked papers returned.");
  }
  return `
    <div class="paper-list">
      ${papers.map((paper) => {
        const authors = paper.authors && paper.authors.length ? paper.authors.slice(0, 6).join(", ") : "No author metadata";
        const meta = [
          paper.provider || "",
          paper.publish_year || "",
          paper.citations ? `${paper.citations} citations` : "",
          paper.source || "",
          paper.document_types && paper.document_types.length ? paper.document_types.join("; ") : "",
        ].filter(Boolean).join(" | ");
        const link = paper.links && paper.links.record ? `<a href="${escapeHtml(paper.links.record)}" target="_blank" rel="noreferrer">Open source record</a>` : "";
        const pdfLink = paper.links && paper.links.pdf ? `<a href="${escapeHtml(paper.links.pdf)}" target="_blank" rel="noreferrer">Open PDF</a>` : "";
        return `
          <details class="paper-row" open>
            <summary>
              <span class="score">${escapeHtml(paper.score ?? 0)}/10</span>
              <span class="paper-title">${escapeHtml(paper.title || "(no title)")}</span>
            </summary>
            <div class="paper-body">
              <p>${escapeHtml(authors)}</p>
              <p>${escapeHtml(meta)}</p>
              ${paper.keywords ? `<p><strong>Keywords:</strong> ${escapeHtml(paper.keywords)}</p>` : ""}
              ${paper.doi ? `<p><strong>DOI:</strong> ${escapeHtml(paper.doi)}</p>` : ""}
              ${paper.citations ? `<p><strong>Citations:</strong> ${escapeHtml(paper.citations)}</p>` : ""}
              ${paper.abstract ? `<p><strong>Abstract:</strong> ${escapeHtml(paper.abstract.slice(0, 900))}${paper.abstract.length > 900 ? "..." : ""}</p>` : ""}
              ${paper.reasoning ? `<p><strong>Reasoning:</strong> ${escapeHtml(paper.reasoning)}</p>` : ""}
              <div class="paper-links">${link} ${pdfLink}</div>
            </div>
          </details>
        `;
      }).join("")}
    </div>
  `;
}

function renderResultsView() {
  const allPapers = latestResult && latestResult.ranked ? latestResult.ranked : [];
  if (!latestResult) {
    return `
      <section class="workspace-view">
        <div class="workspace-header">
          <div>
            <div class="section-kicker">Results</div>
            <h2>Ranked literature</h2>
          </div>
        </div>
        ${emptyState("Run a search before reviewing results.")}
      </section>
    `;
  }

  const filtered = getFilteredPapers();
  const selectedCount = selectedPapers().length;
  return `
    <section class="workspace-view results-view">
      <div class="workspace-header">
        <div>
          <div class="section-kicker">Results</div>
          <h2>Ranked literature</h2>
        </div>
        <div class="view-actions">
          <span>${escapeHtml(filtered.length)} shown</span>
          <span>${escapeHtml(selectedCount)} selected</span>
        </div>
      </div>
      <div class="results-toolbar">
        <input id="resultSearch" type="search" value="${escapeHtml(resultFilters.query)}" placeholder="Search title, author, abstract, DOI">
        <select id="resultMinScore">
          <option value="all"${resultFilters.minScore === "all" ? " selected" : ""}>All scores</option>
          <option value="7"${resultFilters.minScore === "7" ? " selected" : ""}>Score >= 7</option>
          <option value="8"${resultFilters.minScore === "8" ? " selected" : ""}>Score >= 8</option>
          <option value="9"${resultFilters.minScore === "9" ? " selected" : ""}>Score >= 9</option>
        </select>
        <select id="resultAvailability">
          <option value="all"${resultFilters.availability === "all" ? " selected" : ""}>All metadata</option>
          <option value="abstract"${resultFilters.availability === "abstract" ? " selected" : ""}>Has abstract</option>
          <option value="doi"${resultFilters.availability === "doi" ? " selected" : ""}>Has DOI</option>
          <option value="pdf"${resultFilters.availability === "pdf" ? " selected" : ""}>Has PDF</option>
        </select>
        <select id="resultSort">
          <option value="rank"${resultFilters.sort === "rank" ? " selected" : ""}>Sort by rank</option>
          <option value="score"${resultFilters.sort === "score" ? " selected" : ""}>Sort by score</option>
          <option value="citations"${resultFilters.sort === "citations" ? " selected" : ""}>Sort by citations</option>
          <option value="year"${resultFilters.sort === "year" ? " selected" : ""}>Sort by year</option>
        </select>
        <button class="secondary-button" type="button" data-action="select-all-results">Select all shown</button>
        <button class="secondary-button" type="button" data-action="clear-result-selection">Clear</button>
      </div>
      ${filtered.length ? renderResultRows(filtered) : emptyState("No papers match the current filters.")}
    </section>
  `;
}

function renderResultRows(papers) {
  return `
    <div class="review-list">
      ${papers.map((paper) => {
        const id = paperId(paper);
        const checked = selectedPaperIds.has(id) ? " checked" : "";
        const authors = paper.authors && paper.authors.length ? paper.authors.slice(0, 8).join(", ") : "No author metadata";
        const meta = [
          `Rank ${paper.rank || ""}`,
          paper.score !== undefined ? `${paper.score}/10` : "",
          paper.publish_year || "",
          paper.citations ? `${paper.citations} citations` : "",
          paper.source || "",
        ].filter(Boolean).join(" | ");
        const record = paper.links && paper.links.record ? `<a href="${escapeHtml(paper.links.record)}" target="_blank" rel="noreferrer">Record</a>` : "";
        const pdf = paper.links && paper.links.pdf ? `<a href="${escapeHtml(paper.links.pdf)}" target="_blank" rel="noreferrer">PDF</a>` : "";
        return `
          <details class="review-row" open>
            <summary>
              <input class="paper-select" type="checkbox" value="${escapeHtml(id)}"${checked} aria-label="Select paper">
              <span class="score">${escapeHtml(paper.score ?? 0)}/10</span>
              <span class="paper-title">${escapeHtml(paper.title || "(no title)")}</span>
            </summary>
            <div class="paper-body">
              <p>${escapeHtml(authors)}</p>
              <p>${escapeHtml(meta)}</p>
              ${paper.doi ? `<p><strong>DOI:</strong> ${escapeHtml(paper.doi)}</p>` : ""}
              ${paper.keywords ? `<p><strong>Keywords:</strong> ${escapeHtml(paper.keywords)}</p>` : ""}
              ${paper.abstract ? `<p><strong>Abstract:</strong> ${escapeHtml(paper.abstract.slice(0, 1400))}${paper.abstract.length > 1400 ? "..." : ""}</p>` : ""}
              ${paper.reasoning ? `<p><strong>Reasoning:</strong> ${escapeHtml(paper.reasoning)}</p>` : ""}
              <div class="paper-links">${record} ${pdf}</div>
            </div>
          </details>
        `;
      }).join("")}
    </div>
  `;
}

function shortText(value, maxChars = 120) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  if (text.length <= maxChars) {
    return text;
  }
  return `${text.slice(0, maxChars - 3).trim()}...`;
}

function resultFromHistoryRun(run) {
  if (!run) {
    return null;
  }
  return {
    run_id: run.id,
    question: run.question || "",
    source: run.source || "",
    final_query: run.final_query || "",
    db: run.db || "",
    field: run.field || "",
    total: run.total || 0,
    iterations: run.iterations || 0,
    history: run.history || [],
    citation_map: run.citation_map || {},
    ranked: run.ranked || [],
  };
}

function renderHistoryView() {
  const statusText = historyStatus.enabled ? `Local SQLite: ${historyStatus.path || "default path"}` : "Local history is disabled";
  const selectedId = historyDetail && historyDetail.id ? historyDetail.id : "";
  const listBody = historyLoading ? emptyState("Loading saved runs.") : historyError ? `<div class="error-box">${escapeHtml(historyError)}</div>` : historyRuns.length ? `
    <div class="history-list">
      ${historyRuns.map((run) => {
        const active = run.id === selectedId ? " active" : "";
        const pieces = [
          run.status,
          run.source || "source pending",
          `${run.result_count || 0} papers`,
          run.created_at,
        ].filter(Boolean).join(" | ");
        return `
          <button class="history-run-button${active}" type="button" data-history-id="${escapeHtml(run.id)}">
            <strong>${escapeHtml(shortText(run.question || "(no question)", 96))}</strong>
            <span>${escapeHtml(pieces)}</span>
            ${run.final_query ? `<span>${escapeHtml(shortText(run.final_query, 110))}</span>` : ""}
          </button>
        `;
      }).join("")}
    </div>
  ` : emptyState("No saved search runs yet.");

  return `
    <section class="workspace-view history-view">
      <div class="workspace-header">
        <div>
          <div class="section-kicker">History</div>
          <h2>Local search records</h2>
        </div>
        <div class="view-actions">
          <span>${escapeHtml(statusText)}</span>
          <button class="secondary-button compact" type="button" data-history-action="refresh">Refresh</button>
        </div>
      </div>
      <div class="history-layout">
        <div>${listBody}</div>
        ${renderHistoryDetail()}
      </div>
    </section>
  `;
}

function renderHistoryDetail() {
  if (!historyDetail) {
    return `
      <div class="history-detail-panel">
        ${emptyState("Select a saved run to inspect query, events, and ranked papers.")}
      </div>
    `;
  }

  const run = historyDetail;
  const papers = run.ranked || [];
  const events = run.events || [];
  const meta = [
    run.status,
    run.source || "source pending",
    run.result_count !== undefined ? `${run.result_count} papers` : `${papers.length} papers`,
    run.iterations ? `${run.iterations} iteration(s)` : "",
    run.created_at,
  ].filter(Boolean);
  const eventRows = events.length ? `
    <div class="history-event-list">
      ${events.slice(-12).map((event) => `
        <div class="history-event-row">
          <span>${escapeHtml(String(event.created_at || "").slice(11, 19))}</span>
          <span>${escapeHtml(event.message || [event.type, event.stage, event.status].filter(Boolean).join(" "))}</span>
        </div>
      `).join("")}
    </div>
  ` : emptyState("No event log was saved for this run.");

  return `
    <div class="history-detail-panel">
      <div class="history-detail-head">
        <div class="section-kicker">${escapeHtml(run.id)}</div>
        <h3>${escapeHtml(run.question || "(no question)")}</h3>
        <div class="history-meta">${meta.map((item) => `<span>${escapeHtml(item)}</span>`).join("")}</div>
        <div class="result-jump-actions">
          <button class="primary-inline-button" type="button" data-history-action="open-results">Open Results</button>
          <button class="secondary-button" type="button" data-history-action="open-citations">Open Citation Map</button>
          <button class="secondary-button" type="button" data-history-action="delete" data-history-id="${escapeHtml(run.id)}">Delete</button>
        </div>
      </div>
      ${run.final_query ? `
        <div class="history-query">
          <span>Final query</span>
          <code>${escapeHtml(run.final_query)}</code>
        </div>
      ` : ""}
      ${run.error_message ? `<div class="error-box">${escapeHtml(run.error_message)}</div>` : ""}
      ${papers.length ? renderPapers(papers.slice(0, 8)) : emptyState("This run did not save ranked papers.")}
      <div class="history-query">
        <span>Recent log events</span>
        ${eventRows}
      </div>
    </div>
  `;
}

async function loadHistoryRuns() {
  historyLoading = true;
  historyError = "";
  renderWorkflow();
  try {
    const response = await fetch("/api/history?limit=80");
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(responseErrorMessage(data, response.status));
    }
    historyStatus = { enabled: data.enabled, path: data.path };
    historyRuns = data.history || [];
    if (historyDetail && !historyRuns.some((run) => run.id === historyDetail.id)) {
      historyDetail = null;
    }
  } catch (error) {
    historyError = error.message;
  } finally {
    historyLoading = false;
    renderWorkflow();
  }
}

async function loadHistoryDetail(runIdValue) {
  historyError = "";
  try {
    const response = await fetch(`/api/history/${encodeURIComponent(runIdValue)}`);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(responseErrorMessage(data, response.status));
    }
    historyDetail = data;
  } catch (error) {
    historyError = error.message;
  }
  renderWorkflow();
}

function citationMap() {
  return latestResult && latestResult.citation_map ? latestResult.citation_map : null;
}

function citationRole(node) {
  const roles = node.roles || [];
  if (roles.includes("result")) return "result";
  if (roles.includes("seed")) return "seed";
  if (roles.includes("forward")) return "forward";
  if (roles.includes("backward")) return "backward";
  return "candidate";
}

function renderCitationView() {
  const map = citationMap();
  if (!latestResult) {
    return `
      <section class="workspace-view citation-view">
        <div class="workspace-header">
          <div>
            <div class="section-kicker">Citation Map</div>
            <h2>Citation expansion</h2>
          </div>
        </div>
        ${emptyState("Run an OpenAlex search with citation expansion enabled before exploring citations.")}
      </section>
    `;
  }
  if (!map || !map.enabled) {
    return `
      <section class="workspace-view citation-view">
        <div class="workspace-header">
          <div>
            <div class="section-kicker">Citation Map</div>
            <h2>Citation expansion</h2>
          </div>
        </div>
        ${emptyState("Citation expansion was disabled for this run.")}
      </section>
    `;
  }
  if (!map.supported) {
    return `
      <section class="workspace-view citation-view">
        <div class="workspace-header">
          <div>
            <div class="section-kicker">Citation Map</div>
            <h2>Citation expansion</h2>
          </div>
        </div>
        ${emptyState("Citation traversal is currently available for OpenAlex runs only.")}
      </section>
    `;
  }

  const nodes = map.nodes || [];
  const edges = map.edges || [];
  const seeds = nodes.filter((node) => (node.roles || []).includes("seed"));
  const promoted = nodes.filter((node) => (node.roles || []).includes("result") && !((node.roles || []).includes("seed")));
  return `
    <section class="workspace-view citation-view">
      <div class="workspace-header">
        <div>
          <div class="section-kicker">Citation Map</div>
          <h2>Citation expansion</h2>
        </div>
        <div class="view-actions">
          <span>${escapeHtml(nodes.length)} nodes</span>
          <span>${escapeHtml(edges.length)} edges</span>
        </div>
      </div>
      <div class="citation-summary-grid">
        ${metricRow([
          { value: map.initial_candidates || 0, label: "INITIAL CANDIDATES" },
          { value: map.seed_count || seeds.length || 0, label: "SEED PAPERS" },
          { value: map.added_candidates || 0, label: "ADDED CANDIDATES" },
          { value: promoted.length, label: "PROMOTED RESULTS" },
        ])}
      </div>
      <div class="citation-layout">
        <div class="citation-map-panel">
          <div class="citation-toolbar">
            <div class="citation-legend">
              <span><i class="legend-dot result"></i>Result</span>
              <span><i class="legend-dot seed"></i>Seed</span>
              <span><i class="legend-dot forward"></i>Forward citation</span>
              <span><i class="legend-dot backward"></i>Backward reference</span>
            </div>
            <div class="citation-controls">
              <button class="secondary-button compact" type="button" data-graph-action="zoom-out">-</button>
              <button class="secondary-button compact" type="button" data-graph-action="reset">Reset</button>
              <button class="secondary-button compact" type="button" data-graph-action="zoom-in">+</button>
              <select id="citationFocus">
                <option value="">All seeds</option>
                ${seeds.map((seed) => `<option value="${escapeHtml(seed.id)}">${escapeHtml((seed.title || seed.id).slice(0, 80))}</option>`).join("")}
              </select>
            </div>
          </div>
          <div id="citationGraph" class="citation-graph" aria-label="Citation network graph"></div>
        </div>
        <aside id="citationNodeDetail" class="citation-detail">
          ${renderCitationNodeDetail(nodes.find((node) => node.id === selectedCitationNodeId) || seeds[0] || nodes[0])}
        </aside>
      </div>
      <div class="seed-list">
        <h3>Seed papers</h3>
        ${seeds.length ? seeds.map((seed) => `
          <button type="button" class="seed-row" data-citation-node="${escapeHtml(seed.id)}">
            <strong>${escapeHtml(seed.title || seed.id)}</strong>
            <span>${escapeHtml([seed.year, seed.citations ? `${seed.citations} citations` : "", seed.score ? `${seed.score}/10` : ""].filter(Boolean).join(" | "))}</span>
          </button>
        `).join("") : emptyState("No seed papers were recorded.")}
      </div>
    </section>
  `;
}

function renderCitationNodeDetail(node) {
  if (!node) {
    return emptyState("Select a node to inspect its metadata.");
  }
  const roles = (node.roles || []).join(", ");
  return `
    <div class="detail-kicker">${escapeHtml(roles || "node")}</div>
    <h3>${escapeHtml(node.title || node.id)}</h3>
    <p>${escapeHtml([node.year, node.source, node.citations ? `${node.citations} citations` : ""].filter(Boolean).join(" | "))}</p>
    ${node.score !== undefined ? `<p><strong>Score:</strong> ${escapeHtml(node.score)}/10</p>` : ""}
    ${node.rank ? `<p><strong>Rank:</strong> ${escapeHtml(node.rank)}</p>` : ""}
    ${node.reasoning ? `<p><strong>Reasoning:</strong> ${escapeHtml(node.reasoning)}</p>` : ""}
    <div class="paper-links"><a href="${escapeHtml(node.id)}" target="_blank" rel="noreferrer">Open record</a></div>
  `;
}

function filteredCitationGraph() {
  const map = citationMap();
  const allNodes = map && map.nodes ? map.nodes : [];
  const allEdges = map && map.edges ? map.edges : [];
  const focus = document.getElementById("citationFocus") ? document.getElementById("citationFocus").value : "";
  if (!focus) {
    return { nodes: allNodes, edges: allEdges };
  }
  const keep = new Set([focus]);
  allEdges.forEach((edge) => {
    if (edge.seed === focus || edge.source === focus || edge.target === focus) {
      keep.add(edge.source);
      keep.add(edge.target);
    }
  });
  return {
    nodes: allNodes.filter((node) => keep.has(node.id)),
    edges: allEdges.filter((edge) => keep.has(edge.source) && keep.has(edge.target)),
  };
}

function renderCitationGraph() {
  const container = document.getElementById("citationGraph");
  if (!container) return;
  const { nodes, edges } = filteredCitationGraph();
  if (!nodes.length) {
    container.innerHTML = emptyState("No citation graph nodes are available for this run.");
    applyLanguage(container);
    return;
  }

  const width = Math.max(container.clientWidth || 760, 520);
  const height = Math.max(container.clientHeight || 460, 360);
  const nodeMap = new Map(nodes.map((node, i) => {
    const saved = citationGraphState.positions[node.id];
    return [node.id, {
      ...node,
      x: saved ? saved.x : width / 2 + Math.cos(i * 2.2) * width * 0.25,
      y: saved ? saved.y : height / 2 + Math.sin(i * 2.2) * height * 0.25,
      vx: 0,
      vy: 0,
    }];
  }));
  const graphEdges = edges.filter((edge) => nodeMap.has(edge.source) && nodeMap.has(edge.target));

  if (Object.keys(citationGraphState.positions).length === 0) {
    for (let tick = 0; tick < 90; tick += 1) {
      const values = [...nodeMap.values()];
      for (let i = 0; i < values.length; i += 1) {
        for (let j = i + 1; j < values.length; j += 1) {
          const a = values[i];
          const b = values[j];
          const dx = a.x - b.x || 0.01;
          const dy = a.y - b.y || 0.01;
          const distance = Math.max(Math.sqrt(dx * dx + dy * dy), 16);
          const force = 720 / (distance * distance);
          a.vx += (dx / distance) * force;
          a.vy += (dy / distance) * force;
          b.vx -= (dx / distance) * force;
          b.vy -= (dy / distance) * force;
        }
      }
      graphEdges.forEach((edge) => {
        const a = nodeMap.get(edge.source);
        const b = nodeMap.get(edge.target);
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const distance = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
        const desired = 150;
        const force = (distance - desired) * 0.012;
        a.vx += (dx / distance) * force;
        a.vy += (dy / distance) * force;
        b.vx -= (dx / distance) * force;
        b.vy -= (dy / distance) * force;
      });
      values.forEach((node) => {
        node.vx += (width / 2 - node.x) * 0.002;
        node.vy += (height / 2 - node.y) * 0.002;
        node.x = Math.min(width - 60, Math.max(60, node.x + node.vx));
        node.y = Math.min(height - 46, Math.max(46, node.y + node.vy));
        node.vx *= 0.82;
        node.vy *= 0.82;
      });
    }
  }

  nodeMap.forEach((node) => {
    node.radius = Math.min(18, 7 + Math.sqrt(Number(node.citations || 0)) / 12 + (node.score ? 2 : 0));
    citationGraphState.positions[node.id] = { x: node.x, y: node.y };
  });

  const svgEdges = graphEdges.map((edge) => {
    const a = nodeMap.get(edge.source);
    const b = nodeMap.get(edge.target);
    const points = citationEdgePoints(a, b, a.radius, b.radius);
    return `<line class="citation-edge" data-source="${escapeHtml(edge.source)}" data-target="${escapeHtml(edge.target)}" data-source-radius="${a.radius.toFixed(1)}" data-target-radius="${b.radius.toFixed(1)}" x1="${points.x1.toFixed(1)}" y1="${points.y1.toFixed(1)}" x2="${points.x2.toFixed(1)}" y2="${points.y2.toFixed(1)}"></line>`;
  }).join("");
  const svgNodes = [...nodeMap.values()].map((node) => {
    const role = citationRole(node);
    const radius = node.radius;
    const selected = node.id === selectedCitationNodeId ? " selected" : "";
    return `
      <g class="citation-node ${escapeHtml(role)}${selected}" data-citation-node="${escapeHtml(node.id)}" transform="translate(${node.x.toFixed(1)} ${node.y.toFixed(1)})">
        <circle r="${radius.toFixed(1)}"></circle>
        <text y="${(radius + 13).toFixed(1)}">${escapeHtml((node.title || node.id).slice(0, 28))}</text>
        <title>${escapeHtml(node.title || node.id)}</title>
      </g>
    `;
  }).join("");

  container.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" role="img">
      <defs>
        <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
          <path d="M 0 0 L 10 5 L 0 10 z"></path>
        </marker>
      </defs>
      <g id="citationGraphViewport" transform="translate(${citationGraphState.panX} ${citationGraphState.panY}) scale(${citationGraphState.scale})">
        <g>${svgEdges}</g>
        <g>${svgNodes}</g>
      </g>
    </svg>
  `;
  bindCitationGraphInteractions(container);
}

function clampGraphScale(value) {
  return Math.min(3.2, Math.max(0.45, value));
}

function applyCitationTransform() {
  const viewport = document.getElementById("citationGraphViewport");
  if (viewport) {
    viewport.setAttribute("transform", `translate(${citationGraphState.panX} ${citationGraphState.panY}) scale(${citationGraphState.scale})`);
  }
}

function citationEdgePoints(source, target, sourceRadius = 10, targetRadius = 10) {
  const dx = target.x - source.x;
  const dy = target.y - source.y;
  const distance = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
  const ux = dx / distance;
  const uy = dy / distance;
  const sourceGap = Math.min(sourceRadius + 4, distance * 0.35);
  const targetGap = Math.min(targetRadius + 8, distance * 0.45);
  return {
    x1: source.x + ux * sourceGap,
    y1: source.y + uy * sourceGap,
    x2: target.x - ux * targetGap,
    y2: target.y - uy * targetGap,
  };
}

function updateCitationGraphDom() {
  const container = document.getElementById("citationGraph");
  if (!container) return;
  container.querySelectorAll(".citation-node").forEach((nodeEl) => {
    const id = nodeEl.dataset.citationNode;
    const pos = citationGraphState.positions[id];
    if (pos) {
      nodeEl.setAttribute("transform", `translate(${pos.x.toFixed(1)} ${pos.y.toFixed(1)})`);
    }
  });
  container.querySelectorAll(".citation-edge").forEach((edgeEl) => {
    const source = citationGraphState.positions[edgeEl.dataset.source];
    const target = citationGraphState.positions[edgeEl.dataset.target];
    if (source && target) {
      const points = citationEdgePoints(
        source,
        target,
        Number(edgeEl.dataset.sourceRadius || 10),
        Number(edgeEl.dataset.targetRadius || 10),
      );
      edgeEl.setAttribute("x1", points.x1.toFixed(1));
      edgeEl.setAttribute("y1", points.y1.toFixed(1));
      edgeEl.setAttribute("x2", points.x2.toFixed(1));
      edgeEl.setAttribute("y2", points.y2.toFixed(1));
    }
  });
}

function svgPoint(event, svg) {
  const point = svg.createSVGPoint();
  point.x = event.clientX;
  point.y = event.clientY;
  const transformed = point.matrixTransform(svg.getScreenCTM().inverse());
  return {
    x: (transformed.x - citationGraphState.panX) / citationGraphState.scale,
    y: (transformed.y - citationGraphState.panY) / citationGraphState.scale,
  };
}

function zoomCitationGraph(factor) {
  citationGraphState.scale = clampGraphScale(citationGraphState.scale * factor);
  applyCitationTransform();
}

function resetCitationGraphView() {
  citationGraphState.scale = 1;
  citationGraphState.panX = 0;
  citationGraphState.panY = 0;
  applyCitationTransform();
}

function bindCitationGraphInteractions(container) {
  const svg = container.querySelector("svg");
  if (!svg) return;

  container.onwheel = (event) => {
    event.preventDefault();
    zoomCitationGraph(event.deltaY < 0 ? 1.12 : 0.89);
  };

  svg.addEventListener("pointerdown", (event) => {
    const nodeEl = event.target.closest(".citation-node");
    if (nodeEl) {
      const id = nodeEl.dataset.citationNode;
      const pos = citationGraphState.positions[id] || { x: 0, y: 0 };
      const point = svgPoint(event, svg);
      citationGraphState.draggingNodeId = id;
      citationGraphState.dragOffsetX = point.x - pos.x;
      citationGraphState.dragOffsetY = point.y - pos.y;
      selectedCitationNodeId = id;
      const map = citationMap();
      const node = map && map.nodes ? map.nodes.find((item) => item.id === id) : null;
      const detail = document.getElementById("citationNodeDetail");
      if (detail) {
        detail.innerHTML = renderCitationNodeDetail(node);
      }
      svg.setPointerCapture(event.pointerId);
      event.preventDefault();
      return;
    }
    citationGraphState.panning = true;
    citationGraphState.lastX = event.clientX;
    citationGraphState.lastY = event.clientY;
    svg.setPointerCapture(event.pointerId);
    event.preventDefault();
  });

  svg.addEventListener("pointermove", (event) => {
    if (citationGraphState.draggingNodeId) {
      const point = svgPoint(event, svg);
      citationGraphState.positions[citationGraphState.draggingNodeId] = {
        x: point.x - citationGraphState.dragOffsetX,
        y: point.y - citationGraphState.dragOffsetY,
      };
      updateCitationGraphDom();
      return;
    }
    if (citationGraphState.panning) {
      citationGraphState.panX += event.clientX - citationGraphState.lastX;
      citationGraphState.panY += event.clientY - citationGraphState.lastY;
      citationGraphState.lastX = event.clientX;
      citationGraphState.lastY = event.clientY;
      applyCitationTransform();
    }
  });

  const endDrag = (event) => {
    citationGraphState.draggingNodeId = "";
    citationGraphState.panning = false;
    if (event && svg.hasPointerCapture(event.pointerId)) {
      svg.releasePointerCapture(event.pointerId);
    }
  };
  svg.addEventListener("pointerup", endDrag);
  svg.addEventListener("pointercancel", endDrag);
}

function applyStageEvent(event) {
  const stage = workflowState[event.stage];
  if (!stage) {
    return;
  }
  const data = event.data || {};
  const status = (event.status || "processing").toUpperCase();
  stage.status = status;

  if (event.stage === "query") {
    if (status === "PROCESSING") {
      stage.body = emptyState("Calling the LLM to generate a source-specific query.");
    } else {
      stage.body = chipList([
        sourceLabels[data.source] || data.source || getValue("dataSource"),
        data.query || "No query returned",
      ]);
    }
  }

  if (event.stage === "search") {
    stage.body = renderHistory(data.history || [], data.final_query || data.query || "", data.preview || []);
    if (data.total !== undefined && data.total !== null) {
      stage.description = `Latest source response returned ${data.total} records.`;
    }
  }

  if (event.stage === "ranking") {
    const candidateCount = data.candidate_count ?? "";
    const rankedCount = data.ranked_count ?? "";
    stage.body = metricRow([
      { value: candidateCount || rankedCount || 0, label: status === "PROCESSING" ? "CANDIDATES" : "RANKED RECORDS" },
      { value: status, label: "RANKING STATUS" },
      { value: getValue("dataSource").toUpperCase(), label: "SOURCE" },
    ]);
  }

  if (event.stage === "results") {
    stage.body = metricRow([
      { value: data.total ?? 0, label: "TOTAL RECORDS" },
      { value: data.ranked_count ?? 0, label: "RANKED RECORDS" },
      { value: getValue("dataSource").toUpperCase(), label: "SOURCE" },
    ]);
  }

  renderWorkflow();
}

function applyFinalResult(data) {
  latestResult = data;
  latestError = "";
  selectedPaperIds = new Set();
  selectedCitationNodeId = "";
  citationGraphState = createCitationGraphState();
  updateExportButtons();
  const hasResults = data.ranked && data.ranked.length > 0;
  workflowState.query.status = "COMPLETE";
  workflowState.query.body = chipList([
    data.source || data.db || "source",
    data.db || "",
    data.field || "No field hint",
    `${data.iterations} iteration(s)`,
  ].filter(Boolean));

  workflowState.search.status = "COMPLETE";
  workflowState.search.body = renderHistory(data.history, data.final_query, []);
  workflowState.search.description = `Accepted query returned ${data.total} total records.`;

  workflowState.ranking.status = "COMPLETE";
  workflowState.ranking.body = metricRow([
    { value: data.total, label: "TOTAL RECORDS" },
    { value: data.ranked.length, label: "RANKED RECORDS" },
    { value: hasResults ? Math.max(...data.ranked.map((p) => Number(p.score || 0))) : 0, label: "TOP SCORE" },
  ]);

  workflowState.results.status = hasResults ? "READY" : "EMPTY";
  const citationMap = data.citation_map || {};
  workflowState.results.body = `
    ${metricRow([
      { value: data.total ?? 0, label: "TOTAL RECORDS" },
      { value: data.ranked ? data.ranked.length : 0, label: "RANKED RECORDS" },
      { value: citationMap.candidate_pool || data.ranked.length || 0, label: "CANDIDATES SCORED" },
      { value: citationMap.added_candidates || 0, label: "CITATION ADDS" },
    ])}
    <div class="result-jump-actions">
      <button class="primary-inline-button" type="button" data-switch-view="results">Review Results</button>
      <button class="secondary-button" type="button" data-switch-view="citations">Open Citation Map</button>
    </div>
  `;
  renderWorkflow();
}

function showClientError(message, fieldId) {
  workflowState = createWorkflowState();
  workflowState.query.status = "ERROR";
  workflowState.query.title = "Input Required";
  workflowState.query.description = "Fill the required field and run the search again.";
  workflowState.query.body = `<div class="error-box">${escapeHtml(message)}</div>`;
  renderWorkflow();
  log(`Input required: ${message}`);
  if (fieldId) {
    const field = document.getElementById(fieldId);
    if (field) {
      field.classList.add("is-invalid");
      field.focus();
    }
  }
}

function showRunError(message) {
  latestError = message;
  updateExportButtons();
  setTranslatedText(stateLabel, "Error");
  workflowState.results.status = "ERROR";
  workflowState.results.title = "Search Failed";
  workflowState.results.description = "The local backend or upstream service returned an error.";
  workflowState.results.body = `<div class="error-box">${escapeHtml(message)}</div>`;
  renderWorkflow();
  log(`Error: ${message}`);
}

function hideConfigAlert() {
  if (configAlert) {
    configAlert.classList.add("is-hidden");
  }
}

function showConfigAlert(title, message, checks = []) {
  if (!configAlert || !configAlertTitle || !configAlertMessage || !configAlertList) {
    return;
  }
  setTranslatedText(configAlertTitle, title);
  setTranslatedText(configAlertMessage, message);
  configAlertList.textContent = "";
  const displayChecks = checks.length ? checks : [{ summary: message, actions: [] }];
  displayChecks.slice(0, 6).forEach((check) => {
    const item = document.createElement("li");
    const summary = document.createElement("strong");
    setTranslatedText(summary, check.summary || check.id || "Configuration check failed.");
    item.appendChild(summary);
    const actions = Array.isArray(check.actions) ? check.actions : [];
    actions.slice(0, 4).forEach((action) => {
      const actionNode = document.createElement("span");
      setTranslatedText(actionNode, action);
      item.appendChild(actionNode);
    });
    configAlertList.appendChild(item);
  });
  applyLanguage(configAlert);
  configAlert.classList.remove("is-hidden");
  if (configAlertCloseButton) {
    configAlertCloseButton.focus();
  }
}

function showRunStopped() {
  latestError = "Search stopped by user.";
  updateExportButtons();
  setTranslatedText(stateLabel, "Stopped");
  workflowState.results.status = "EMPTY";
  workflowState.results.title = "Search Stopped";
  workflowState.results.description = "The request was stopped before completion.";
  workflowState.results.body = emptyState("No final result was produced for this run.");
  renderWorkflow();
  log("Search stopped by user.");
}

function validatePayload(payload) {
  const required = [
    ["question", "Research Question", "question"],
  ];
  for (const [key, label, fieldId] of required) {
    if (!String(payload[key] || "").trim()) {
      return { ok: false, message: `${label} is required.`, fieldId };
    }
  }
  if (payload.data_source === "wos" && !String(payload.wos_api_key || "").trim() && !environmentConfig.has_wos_api_key) {
    return { ok: false, message: "WoS API Key is required for WoS searches.", fieldId: "wosApiKey" };
  }
  if (payload.llm_provider !== "ollama" && !String(payload.llm_api_key || "").trim() && !envLlmKeyApplies(payload.llm_provider)) {
    return { ok: false, message: "LLM API Key is required for this provider.", fieldId: "llmApiKey" };
  }
  if (!String(payload.llm_api_type || "").trim()) {
    return { ok: false, message: "API Type is required.", fieldId: "llmApiType" };
  }
  if (!Number.isFinite(payload.target_min) || !Number.isFinite(payload.target_max)) {
    return { ok: false, message: "Min Results and Max Results must be numbers.", fieldId: "targetMin" };
  }
  if (payload.target_min > payload.target_max) {
    return { ok: false, message: "Min Results cannot exceed Max Results.", fieldId: "targetMin" };
  }
  if (!Number.isFinite(payload.max_iterations) || payload.max_iterations < 1) {
    return { ok: false, message: "Iterations must be at least 1.", fieldId: "maxIterations" };
  }
  return { ok: true };
}

function responseErrorMessage(data, status) {
  const detail = data && data.detail;
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || JSON.stringify(item)).join(" ");
  }
  if (detail && typeof detail === "object") {
    return detail.msg || JSON.stringify(detail);
  }
  return `HTTP ${status}`;
}

function buildPayload() {
  return {
    question: getValue("question"),
    data_source: getValue("dataSource"),
    wos_api_key: getValue("wosApiKey"),
    openalex_api_key: getValue("openAlexApiKey"),
    openalex_email: getValue("openAlexEmail"),
    crossref_email: getValue("crossrefEmail"),
    llm_api_key: getValue("llmApiKey"),
    llm_provider: getValue("llmProvider"),
    llm_api_type: getValue("llmApiType"),
    llm_model: getValue("llmModel"),
    llm_base_url: getValue("llmBaseUrl"),
    wos_db: getValue("wosDb") || "WOS",
    search_field: getValue("searchField"),
    client_timezone: clientTimeZone,
    client_utc_offset_minutes: clientUtcOffsetMinutes(),
    target_min: getNumber("targetMin"),
    target_max: getNumber("targetMax"),
    max_iterations: getNumber("maxIterations"),
    fetch_abstracts: document.getElementById("fetchAbstracts").checked,
    expand_citations: document.getElementById("expandCitations").checked,
  };
}

async function checkConfiguration() {
  clearValidationState();
  hideConfigAlert();
  const payload = buildPayload();
  if (!String(payload.question || "").trim()) {
    payload.question = "machine learning";
  }
  log("Configuration check started.");
  checkConfigButton.disabled = true;
  try {
    const response = await fetch("/api/diagnostics", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    log(`Backend POST /api/diagnostics -> HTTP ${response.status} ${response.ok ? "OK" : "ERROR"}.`);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(responseErrorMessage(data, response.status));
    }
    log(`Doctor status: ${String(data.status || "unknown").toUpperCase()}.`);
    (data.checks || []).forEach((check) => {
      const label = String(check.status || "info").toUpperCase();
      log(`[${label}] ${check.summary || check.id || "diagnostic check"}`);
      (check.actions || []).forEach((action) => log(`  - ${action}`));
    });
    if (String(data.status || "").toLowerCase() === "fail") {
      const failedChecks = (data.checks || []).filter((check) => String(check.status || "").toLowerCase() === "fail");
      showConfigAlert(
        "Configuration failed",
        "Fix the items below before running a search.",
        failedChecks,
      );
    }
  } catch (error) {
    log(`Configuration check error: ${error.message}`);
    showConfigAlert(
      "Configuration check failed",
      "PaperSeek could not complete the configuration check.",
      [{ summary: error.message, actions: ["Review the required model and source settings, then run Check Config again."] }],
    );
  } finally {
    checkConfigButton.disabled = false;
  }
}

function updateSourceFields() {
  const source = dataSourceSelect.value;
  document.querySelectorAll(".source-field").forEach((node) => node.classList.add("is-hidden"));
  document.querySelectorAll(`.source-${source}`).forEach((node) => node.classList.remove("is-hidden"));
  updateSourceSummary();
}

async function readNdjsonStream(response) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";
    for (const line of lines) {
      if (!line.trim()) {
        continue;
      }
      handleStreamEvent(JSON.parse(line));
    }
  }
  if (buffer.trim()) {
    handleStreamEvent(JSON.parse(buffer));
  }
}

function handleStreamEvent(event) {
  if (event.type === "log") {
    log(event.message || "");
  } else if (event.type === "run") {
    if (event.run_id) {
      runId.textContent = event.run_id;
      log(`Local history run: ${event.run_id}.`);
    }
  } else if (event.type === "stage") {
    applyStageEvent(event);
  } else if (event.type === "result") {
    applyFinalResult(event.data);
  } else if (event.type === "error") {
    showRunError(event.message || "Unknown error");
  }
}

function applyProviderDefaults() {
  const defaults = providerDefaults[providerSelect.value] || providerDefaults.custom;
  apiTypeSelect.value = defaults.apiType;
  modelInput.value = defaults.model;
  baseUrlInput.value = defaults.baseUrl;
  updateCredentialPlaceholders();
}

providerSelect.addEventListener("change", applyProviderDefaults);

if (stopButton) {
  stopButton.addEventListener("click", () => {
    if (!activeSearchController) {
      return;
    }
    setTranslatedText(stateLabel, "Stopping");
    log("Stop requested.");
    activeSearchController.abort();
  });
}

if (configAlertCloseButton) {
  configAlertCloseButton.addEventListener("click", hideConfigAlert);
}

if (configAlertAdvancedButton) {
  configAlertAdvancedButton.addEventListener("click", () => {
    if (advancedSettings) {
      advancedSettings.open = true;
    }
    hideConfigAlert();
  });
}

if (configAlert) {
  configAlert.addEventListener("click", (event) => {
    if (event.target === configAlert) {
      hideConfigAlert();
    }
  });
}

viewTabs.forEach((tab) => {
  tab.addEventListener("click", () => switchView(tab.dataset.view || "search"));
});

workflow.addEventListener("click", (event) => {
  const switchTarget = event.target.closest("[data-switch-view]");
  if (switchTarget) {
    switchView(switchTarget.dataset.switchView);
    return;
  }

  const historyRun = event.target.closest("[data-history-id]");
  if (historyRun && historyRun.classList.contains("history-run-button")) {
    loadHistoryDetail(historyRun.dataset.historyId);
    return;
  }

  const historyAction = event.target.closest("[data-history-action]");
  if (historyAction) {
    const action = historyAction.dataset.historyAction;
    if (action === "refresh") {
      loadHistoryRuns();
    } else if (action === "open-results" || action === "open-citations") {
      const restored = resultFromHistoryRun(historyDetail);
      if (restored) {
        latestResult = restored;
        selectedPaperIds = new Set();
        selectedCitationNodeId = "";
        citationGraphState = createCitationGraphState();
        updateExportButtons();
        switchView(action === "open-results" ? "results" : "citations");
      }
    } else if (action === "delete") {
      const targetId = historyAction.dataset.historyId || (historyDetail && historyDetail.id);
      if (targetId && window.confirm(`Delete local history run ${targetId}?`)) {
        fetch(`/api/history/${encodeURIComponent(targetId)}`, { method: "DELETE" })
          .then((response) => {
            if (!response.ok) {
              throw new Error(`HTTP ${response.status}`);
            }
            if (historyDetail && historyDetail.id === targetId) {
              historyDetail = null;
            }
            return loadHistoryRuns();
          })
          .catch((error) => {
            historyError = error.message;
            renderWorkflow();
          });
      }
    }
    return;
  }

  const graphAction = event.target.closest("[data-graph-action]");
  if (graphAction) {
    const action = graphAction.dataset.graphAction;
    if (action === "zoom-in") {
      zoomCitationGraph(1.18);
    } else if (action === "zoom-out") {
      zoomCitationGraph(0.85);
    } else {
      resetCitationGraphView();
    }
    return;
  }

  if (event.target.classList.contains("paper-select")) {
    event.stopPropagation();
    return;
  }

  const selectAll = event.target.closest("[data-action='select-all-results']");
  if (selectAll) {
    getFilteredPapers().forEach((paper) => selectedPaperIds.add(paperId(paper)));
    updateExportButtons();
    renderWorkflow();
    return;
  }

  const clearSelection = event.target.closest("[data-action='clear-result-selection']");
  if (clearSelection) {
    selectedPaperIds.clear();
    updateExportButtons();
    renderWorkflow();
    return;
  }

  const citationNode = event.target.closest("[data-citation-node]");
  if (citationNode) {
    selectedCitationNodeId = citationNode.dataset.citationNode;
    const detail = document.getElementById("citationNodeDetail");
    const map = citationMap();
    const node = map && map.nodes ? map.nodes.find((item) => item.id === selectedCitationNodeId) : null;
    if (detail) {
      detail.innerHTML = renderCitationNodeDetail(node);
      applyLanguage(detail);
    }
    renderCitationGraph();
  }
});

workflow.addEventListener("change", (event) => {
  if (event.target.classList.contains("paper-select")) {
    const id = event.target.value;
    if (event.target.checked) {
      selectedPaperIds.add(id);
    } else {
      selectedPaperIds.delete(id);
    }
    updateExportButtons();
    renderWorkflow();
    return;
  }

  if (event.target.id === "resultMinScore") {
    resultFilters.minScore = event.target.value;
    renderWorkflow();
  } else if (event.target.id === "resultAvailability") {
    resultFilters.availability = event.target.value;
    renderWorkflow();
  } else if (event.target.id === "resultSort") {
    resultFilters.sort = event.target.value;
    renderWorkflow();
  } else if (event.target.id === "citationFocus") {
    citationGraphState = createCitationGraphState();
    renderCitationGraph();
  }
  updateExportButtons();
});

workflow.addEventListener("input", (event) => {
  if (event.target.id === "resultSearch") {
    resultFilters.query = event.target.value;
    clearTimeout(resultSearchTimer);
    resultSearchTimer = setTimeout(() => {
      renderWorkflow();
      const input = document.getElementById("resultSearch");
      if (input) {
        input.focus();
        input.setSelectionRange(input.value.length, input.value.length);
      }
      updateExportButtons();
    }, 180);
  }
});

exportLogButton.addEventListener("click", () => {
  const filename = `${filenamePart(exportQuestionTheme())}-${dateStamp()}-system-log.txt`;
  downloadText(filename, currentLogText(), "text/plain;charset=utf-8");
});

exportCsvButton.addEventListener("click", () => {
  const filename = `${filenamePart(exportQuestionTheme())}-${dateStamp()}-papers.csv`;
  downloadText(filename, papersToCsv(getExportPapers()), "text/csv;charset=utf-8");
});

checkConfigButton.addEventListener("click", checkConfiguration);

dataSourceSelect.addEventListener("change", () => {
  updateSourceFields();
  workflowState = createWorkflowState();
  renderWorkflow();
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearValidationState();
  logOutput.textContent = "";
  const payload = buildPayload();
  latestPayload = null;
  latestResult = null;
  latestError = "";
  selectedPaperIds = new Set();
  selectedCitationNodeId = "";
  citationGraphState = createCitationGraphState();
  resultFilters = { query: "", minScore: "all", availability: "all", sort: "rank" };
  updateExportButtons();
  const validation = validatePayload(payload);
  if (!validation.ok) {
    showClientError(validation.message, validation.fieldId);
    return;
  }
  latestPayload = payload;
  updateExportButtons();

  const id = `run_${Date.now().toString(36)}`;
  runId.textContent = id;
  workflowState = createWorkflowState();
  workflowState.query.status = "PROCESSING";
  workflowState.query.body = emptyState("Submitting request to local backend.");
  renderWorkflow();
  setBusy(true);
  activeSearchController = new AbortController();
  log(`Run ${id} started.`);
  log(`Source: ${payload.data_source}; provider: ${payload.llm_provider}; api type: ${payload.llm_api_type}; model: ${payload.llm_model || "provider default"}.`);
  log(`Target range: ${payload.target_min}-${payload.target_max}; max iterations: ${payload.max_iterations}.`);

  try {
    const response = await fetch("/api/search/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: activeSearchController.signal,
    });
    log(`Backend POST /api/search/stream -> HTTP ${response.status} ${response.ok ? "OK" : "ERROR"}.`);
    if (!response.ok || !response.body) {
      const data = await response.json().catch(() => ({}));
      throw new Error(responseErrorMessage(data, response.status));
    }
    await readNdjsonStream(response);
  } catch (error) {
    if (error.name === "AbortError") {
      showRunStopped();
    } else {
      showRunError(error.message);
    }
  } finally {
    activeSearchController = null;
    setBusy(false);
    updateExportButtons();
  }
});

async function initializeApp() {
  initLanguageControls();
  if (advancedSettings) {
    advancedSettings.open = false;
  }
  updateSourceFields();
  applyProviderDefaults();
  await loadServerDefaults();
  updateSourceSummary();
  updateExportButtons();
  document.body.dataset.view = activeView;
  renderWorkflow();
  log("Ready. Keys and endpoint settings are held only in this browser session.");
  applyLanguage();
}

initializeApp();
