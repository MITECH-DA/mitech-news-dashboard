(function () {
  "use strict";

  // Chart.js는 캔버스라서 CSS 변수(--font-body 등)를 못 읽는다. 전역 기본 폰트를 명시적으로 지정.
  if (typeof Chart !== "undefined") {
    Chart.defaults.font.family = "'Pretendard', 'Malgun Gothic', sans-serif";
  }

  // ── 카테고리/센티먼트 색상 팔레트 (Canvas는 CSS 변수를 못 읽어서 hex로 고정) ──
  const CATEGORY_COLORS = {
    "규제/인허가": "#2DD4BF",
    "M&A/투자": "#7B8FE0",
    "임상시험": "#4FB0E0",
    "신제품출시": "#3FBCAE",
    "리콜/이슈": "#E8735A",
    "실적/경영": "#E0A542",
    "R&D/기술": "#62C48C",
    "기타": "#8FA8BD",
  };
  const DEFAULT_CATEGORY_COLOR = "#8FA8BD";
  const SENTIMENT_COLORS = { "긍정": "#2DD4BF", "부정": "#E8735A", "중립": "#8FA8BD" };
  const NODE_TYPE_COLORS = { company: "#2DD4BF", technology: "#E0A542", indication: "#E8735A" };

  let rawData = [];
  let filteredData = [];
  let charts = { timeseries: null, keyword: null, donut: null };
  let state = { granularity: "day", keywordType: "companies" };

  // ── CSV 파싱 & 정규화 ──────────────────────────────────────────────
  function splitMultiValue(str) {
    if (!str) return [];
    return String(str).split(",").map((s) => s.trim()).filter(Boolean);
  }

  function normalizeRow(row) {
    return {
      published_date: (row.published_date || "").trim(),
      source: (row.source || "").trim(),
      title: (row.title || "").trim(),
      url: (row.url || "").trim(),
      image_url: (row.image_url || "").trim(),
      category: (row.category || "기타").trim() || "기타",
      companies: splitMultiValue(row.companies),
      products: splitMultiValue(row.products),
      technologies: splitMultiValue(row.technologies),
      indications: splitMultiValue(row.indications),
      competitor_flag: String(row.competitor_flag).toLowerCase() === "true" || row.competitor_flag === "1",
      sentiment: (row.sentiment || "").trim(),
      summary: (row.summary || "").trim(),
    };
  }

  function parseCSV(text) {
    const result = Papa.parse(text, { header: true, skipEmptyLines: true });
    return result.data.map(normalizeRow).filter((r) => r.published_date && r.title);
  }

  // ── 데이터 로드 ────────────────────────────────────────────────────
  function loadData(rows) {
    rawData = rows.filter((r) => r.published_date);
    if (rawData.length === 0) {
      alert("CSV에서 유효한 기사를 찾지 못했습니다. trend_report.py 출력 형식을 확인해주세요.");
      return;
    }
    document.getElementById("upload-zone").style.display = "none";
    document.getElementById("dashboard-content").classList.add("visible");

    setupFilterOptions();
    applyFilters();

    const dates = rawData.map((r) => r.published_date).sort();
    document.getElementById("header-status").innerHTML =
      '<span class="status-dot live"></span>' + dates[0] + " ~ " + dates[dates.length - 1] +
      " · 기사 " + rawData.length + "건";
    document.getElementById("reload-upload-link").style.display = "inline";
  }

  function setupFilterOptions() {
    const categories = Array.from(new Set(rawData.map((r) => r.category))).sort();
    const select = document.getElementById("category-filter");
    select.innerHTML = '<option value="">전체</option>';
    categories.forEach((c) => {
      const opt = document.createElement("option");
      opt.value = c;
      opt.textContent = c;
      select.appendChild(opt);
    });

    const dates = rawData.map((r) => r.published_date).sort();
    document.getElementById("date-start").value = dates[0];
    document.getElementById("date-end").value = dates[dates.length - 1];
    document.getElementById("date-start").min = dates[0];
    document.getElementById("date-start").max = dates[dates.length - 1];
    document.getElementById("date-end").min = dates[0];
    document.getElementById("date-end").max = dates[dates.length - 1];
  }

  // ── 필터 적용 ──────────────────────────────────────────────────────
  function applyFilters() {
    const start = document.getElementById("date-start").value;
    const end = document.getElementById("date-end").value;
    const category = document.getElementById("category-filter").value;
    const search = document.getElementById("search-input").value.trim().toLowerCase();

    filteredData = rawData.filter((r) => {
      if (start && r.published_date < start) return false;
      if (end && r.published_date > end) return false;
      if (category && r.category !== category) return false;
      if (search) {
        const haystack = [r.title, ...r.companies, ...r.technologies, ...r.indications, ...r.products]
          .join(" ")
          .toLowerCase();
        if (!haystack.includes(search)) return false;
      }
      return true;
    });

    renderAll();
  }

  function renderAll() {
    renderKPIs();
    renderTopArticles();
    renderTimeSeries();
    renderKeywordChart();
    renderCategoryDonut();
    renderWordCloud();
  }

  // ── KPI 카드 ──────────────────────────────────────────────────────
  function renderKPIs() {
    const total = filteredData.length;
    const categoryCounts = countBy(filteredData, "category");
    const topCategory = Object.entries(categoryCounts).sort((a, b) => b[1] - a[1])[0];

    const companyCounts = {};
    filteredData.forEach((r) => r.companies.forEach((c) => (companyCounts[c] = (companyCounts[c] || 0) + 1)));
    const topCompany = Object.entries(companyCounts).sort((a, b) => b[1] - a[1])[0];

    const techCounts = {};
    filteredData.forEach((r) => r.technologies.forEach((t) => (techCounts[t] = (techCounts[t] || 0) + 1)));
    const topTech = Object.entries(techCounts).sort((a, b) => b[1] - a[1])[0];

    const indicationCounts = {};
    filteredData.forEach((r) => r.indications.forEach((i) => (indicationCounts[i] = (indicationCounts[i] || 0) + 1)));
    const topIndication = Object.entries(indicationCounts).sort((a, b) => b[1] - a[1])[0];

    const cards = [
      { label: "총 기사 수", value: total, sub: "선택 기간 내" },
      { label: "최다 카테고리", value: topCategory ? topCategory[0] : "-", sub: topCategory ? topCategory[1] + "건" : "", accent: true },
      { label: "최다 언급 회사", value: topCompany ? topCompany[0] : "-", sub: topCompany ? topCompany[1] + "회" : "" },
      { label: "최다 언급 기술", value: topTech ? topTech[0] : "-", sub: topTech ? topTech[1] + "회" : "" },
      { label: "최다 언급 적응증", value: topIndication ? topIndication[0] : "-", sub: topIndication ? topIndication[1] + "회" : "" },
    ];

    const row = document.getElementById("kpi-row");
    row.innerHTML = cards
      .map(
        (c) =>
          '<div class="kpi-card"><div class="label">' + c.label + '</div>' +
          '<div class="value' + (c.accent ? " accent" : "") + (c.warn ? " warn" : "") + '">' + c.value + "</div>" +
          '<div class="sub">' + (c.sub || "") + "</div></div>"
      )
      .join("");
  }

  function countBy(data, field) {
    const counts = {};
    data.forEach((r) => {
      const key = r[field];
      counts[key] = (counts[key] || 0) + 1;
    });
    return counts;
  }

  // ── 01. 시계열 차트 ────────────────────────────────────────────────
  function getWeekStart(dateStr) {
    const d = new Date(dateStr + "T00:00:00");
    const day = d.getDay();
    const diff = (day === 0 ? -6 : 1) - day; // 월요일 기준
    d.setDate(d.getDate() + diff);
    return d.toISOString().slice(0, 10);
  }

  function renderTimeSeries() {
    const bucketFn = state.granularity === "week" ? getWeekStart : (d) => d;
    const buckets = {};
    const categories = Array.from(new Set(filteredData.map((r) => r.category)));

    filteredData.forEach((r) => {
      const bucket = bucketFn(r.published_date);
      if (!buckets[bucket]) buckets[bucket] = {};
      buckets[bucket][r.category] = (buckets[bucket][r.category] || 0) + 1;
    });

    const labels = Object.keys(buckets).sort();
    const datasets = categories.map((cat) => ({
      label: cat,
      data: labels.map((l) => buckets[l][cat] || 0),
      backgroundColor: CATEGORY_COLORS[cat] || DEFAULT_CATEGORY_COLOR,
      stack: "s1",
    }));

    // 범례 렌더링 (Chart.js 기본 범례 대신 커스텀)
    document.getElementById("category-legend").innerHTML = categories
      .map(
        (cat) =>
          '<span class="legend-item"><span class="legend-dot" style="background:' +
          (CATEGORY_COLORS[cat] || DEFAULT_CATEGORY_COLOR) + ';"></span>' + cat + "</span>"
      )
      .join("");

    if (charts.timeseries) charts.timeseries.destroy();
    const ctx = document.getElementById("timeseries-chart");
    charts.timeseries = new Chart(ctx, {
      type: "bar",
      data: { labels: labels, datasets: datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { mode: "index", intersect: false } },
        scales: {
          x: { stacked: true, ticks: { color: "#8FA8BD", font: { size: 11 } }, grid: { color: "rgba(242,239,230,0.06)" } },
          y: { stacked: true, ticks: { color: "#8FA8BD", precision: 0 }, grid: { color: "rgba(242,239,230,0.06)" } },
        },
      },
    });
  }

  // ── 02. 키워드 빈도 차트 ───────────────────────────────────────────
  function renderKeywordChart() {
    const field = state.keywordType;
    const counts = {};
    filteredData.forEach((r) => r[field].forEach((v) => (counts[v] = (counts[v] || 0) + 1)));
    const top = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 10);

    if (charts.keyword) charts.keyword.destroy();
    const ctx = document.getElementById("keyword-chart");

    if (top.length === 0) {
      ctx.getContext("2d").clearRect(0, 0, ctx.width, ctx.height);
      return;
    }

    charts.keyword = new Chart(ctx, {
      type: "bar",
      data: {
        labels: top.map((t) => t[0]),
        datasets: [{ label: "언급 횟수", data: top.map((t) => t[1]), backgroundColor: "#2DD4BF", borderRadius: 3 }],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: "#8FA8BD", precision: 0 }, grid: { color: "rgba(242,239,230,0.06)" } },
          y: { ticks: { color: "#F2EFE6", font: { size: 12 } }, grid: { display: false } },
        },
      },
    });
  }

  // ── 03. 카테고리 도넛 ──────────────────────────────────────────────
  function renderCategoryDonut() {
    const counts = countBy(filteredData, "category");
    const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
    const total = filteredData.length || 1;

    if (charts.donut) charts.donut.destroy();
    const ctx = document.getElementById("category-donut");
    charts.donut = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: entries.map((e) => e[0]),
        datasets: [
          {
            data: entries.map((e) => e[1]),
            backgroundColor: entries.map((e) => CATEGORY_COLORS[e[0]] || DEFAULT_CATEGORY_COLOR),
            borderColor: "#092538",
            borderWidth: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "62%",
        plugins: { legend: { display: false } },
      },
    });

    document.getElementById("category-legend-donut").innerHTML = entries
      .map(
        (e) =>
          '<div style="display:flex; justify-content:space-between; font-size:12px; padding:4px 0; color:var(--text-dim);">' +
          '<span><span class="legend-dot" style="background:' + (CATEGORY_COLORS[e[0]] || DEFAULT_CATEGORY_COLOR) +
          '; display:inline-block; margin-right:6px;"></span>' + e[0] + "</span>" +
          "<span>" + e[1] + "건 · " + Math.round((e[1] / total) * 100) + "%</span></div>"
      )
      .join("");
  }

  // ── 05. 키워드 워드클라우드 (d3-cloud) ─────────────────────────────
  function renderWordCloud() {
    const svg = d3.select("#wordcloud-svg");
    svg.selectAll("*").remove();

    // 회사/기술/적응증 언급 빈도 집계 (co-mention 관계는 더 이상 필요 없음 - 단순 빈도만)
    const counts = {};
    function addCount(type, name) {
      const id = type + ":" + name;
      if (!counts[id]) counts[id] = { name, type, count: 0 };
      counts[id].count += 1;
    }
    filteredData.forEach((r) => {
      r.companies.forEach((c) => addCount("company", c));
      r.technologies.forEach((t) => addCount("technology", t));
      r.indications.forEach((i) => addCount("indication", i));
    });

    // 너무 많으면 워드클라우드가 안 읽히므로 상위 60개로 제한
    const words = Object.values(counts)
      .sort((a, b) => b.count - a.count)
      .slice(0, 60);

    if (words.length === 0) return;

    const container = document.getElementById("wordcloud-svg");
    const width = container.clientWidth || 900;
    const height = 460;
    svg.attr("viewBox", "0 0 " + width + " " + height);

    const maxCount = Math.max(...words.map((w) => w.count));
    const sizeScale =
      maxCount <= 1 ? () => 22 : d3.scaleSqrt().domain([1, maxCount]).range([14, 56]);

    const layout = d3.layout
      .cloud()
      .size([width, height])
      .words(words.map((w) => ({ ...w, text: w.name, size: sizeScale(w.count) })))
      .padding(7)
      .rotate(0) // 한글은 회전시키면 가독성이 크게 떨어져서 항상 가로로 고정
      .font("Pretendard")
      .fontWeight(600)
      .fontSize((d) => d.size)
      .on("end", draw);

    layout.start();

    function draw(placedWords) {
      const g = svg.append("g").attr("transform", "translate(" + width / 2 + "," + height / 2 + ")");

      g.selectAll("text")
        .data(placedWords)
        .join("text")
        .attr("class", "wordcloud-text")
        .style("font-size", (d) => d.size + "px")
        .style("fill", (d) => NODE_TYPE_COLORS[d.type])
        .attr("text-anchor", "middle")
        .attr("transform", (d) => "translate(" + [d.x, d.y] + ")")
        .text((d) => d.text)
        .append("title")
        .text((d) => d.name + " · " + d.count + "회 언급");
    }
  }

  // 제목 유사도(overlap coefficient) - 짧은 제목 기준으로 단어가 얼마나 겹치는지 판단.
  // Jaccard(합집합 기준)는 제목 길이 차이가 크면 과소평가되는 경향이 있어(실측 0.27~0.40),
  // "작은 집합 대비 겹치는 비율"인 overlap coefficient가 실제 중복 판별에 더 안정적이었음(실측 0.44~0.67).
  const TITLE_SIMILARITY_THRESHOLD = 0.4;

  function titleTokens(title) {
    return new Set(
      (title || "")
        .toLowerCase()
        .replace(/[^\w\s가-힣]/g, " ")
        .split(/\s+/)
        .filter((t) => t.length > 1) // 한 글자 조사/기호 등 노이즈 제외
    );
  }

  function titleSimilarity(a, b) {
    const setA = titleTokens(a);
    const setB = titleTokens(b);
    if (setA.size === 0 || setB.size === 0) return 0;
    let intersection = 0;
    setA.forEach((t) => { if (setB.has(t)) intersection++; });
    return intersection / Math.min(setA.size, setB.size);
  }

  function isDuplicateTheme(article, selected) {
    // (a) 제목 유사도가 높으면 같은 사건
    const titleDup = selected.some((s) => titleSimilarity(article.title, s.article.title) >= TITLE_SIMILARITY_THRESHOLD);
    if (titleDup) return true;
    // (b) 표현이 달라도 같은 회사를 다루는 기사면(대웅제약 실적 vs 대웅제약 나보타 성장 등) 같은 테마로 취급.
    //     제목 단어 겹침만으로는 못 잡는 "같은 회사, 다른 기사"를 걸러내는 더 확실한 기준.
    if (article.companies.length > 0) {
      const companySet = new Set(article.companies);
      const companyDup = selected.some((s) => s.article.companies.some((c) => companySet.has(c)));
      if (companyDup) return true;
    }
    return false;
  }

  // ── 01. 최신 주요 기사 (언급 많은 제품 Top6, 제품별 대표 기사, 유사 테마 제외) ──
  function renderTopArticles() {
    const grid = document.getElementById("top-articles-grid");

    // 1. 선택 기간 내 products 언급 빈도 집계 -> 빈도순 전체 목록
    const productCounts = {};
    filteredData.forEach((r) => r.products.forEach((p) => (productCounts[p] = (productCounts[p] || 0) + 1)));
    const rankedProducts = Object.entries(productCounts)
      .sort((a, b) => b[1] - a[1])
      .map((e) => e[0]);

    const byRecency = (a, b) => (a.published_date < b.published_date ? 1 : a.published_date > b.published_date ? -1 : 0);

    // 2. 제품별 대표 기사 선정. 순위가 높은 제품부터 훑되, 이미 뽑힌 카드와
    //    제목이 비슷하거나 같은 회사를 다루는 기사는 건너뛰고 다음 순위 제품으로 넘어간다.
    //    -> "상위 6개 제품"이 아니라 "6개를 채울 때까지 순위를 따라 내려가며" 선정.
    const usedUrls = new Set();
    const selected = [];
    for (const product of rankedProducts) {
      if (selected.length >= 6) break;
      const candidates = filteredData.filter((r) => r.products.includes(product)).sort(byRecency);
      const rep = candidates.find((r) => !usedUrls.has(r.url) && !isDuplicateTheme(r, selected));
      if (rep) {
        selected.push({ article: rep, label: product, count: productCounts[product] });
        usedUrls.add(rep.url);
      }
    }

    // 3. 제품 태깅이 부족해 6개를 못 채우면, 최신 기사로 보완 (역시 같은 기준으로 중복 제외)
    if (selected.length < 6) {
      const remaining = [...filteredData].filter((r) => !usedUrls.has(r.url)).sort(byRecency);
      for (const r of remaining) {
        if (selected.length >= 6) break;
        if (isDuplicateTheme(r, selected)) continue;
        selected.push({ article: r, label: r.category, count: null });
        usedUrls.add(r.url);
      }
    }

    if (selected.length === 0) {
      grid.innerHTML = '<div class="empty-state" style="grid-column:1/-1;">표시할 기사가 없습니다.</div>';
      return;
    }

    grid.innerHTML = selected
      .map(({ article: r, label, count }) => {
        const hasImage = !!r.image_url;
        const catColor = CATEGORY_COLORS[r.category] || DEFAULT_CATEGORY_COLOR;
        const safeImageUrl = (r.image_url || "").replace(/"/g, "%22").replace(/'/g, "%27");
        const bgStyle = hasImage ? ' style="background-image:url(&quot;' + safeImageUrl + '&quot;);"' : "";
        const eyebrowText = count ? label + " · " + count + "회 언급" : label;
        return (
          '<a class="top-card' + (hasImage ? "" : " no-image") + '"' + bgStyle +
          ' href="' + escapeHtml(r.url) + '" target="_blank" rel="noopener">' +
          '<div class="top-card-overlay"></div>' +
          '<div class="top-card-content">' +
          '<span class="top-card-eyebrow" style="color:' + catColor + '">| ' + escapeHtml(eyebrowText) + "</span>" +
          '<h3 class="top-card-title">' + escapeHtml(r.title) + "</h3>" +
          '<span class="top-card-source">' + escapeHtml(r.source) + " · " + r.published_date + "</span>" +
          "</div></a>"
        );
      })
      .join("");
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str || "";
    return div.innerHTML;
  }

  // ── 이벤트 바인딩 ──────────────────────────────────────────────────
  function setupEvents() {
    const uploadZone = document.getElementById("upload-zone");
    const fileInput = document.getElementById("file-input");

    document.getElementById("pick-file-btn").addEventListener("click", () => fileInput.click());
    uploadZone.addEventListener("click", (e) => {
      if (e.target.id === "pick-file-btn" || e.target.id === "sample-data-btn") return;
      fileInput.click();
    });

    fileInput.addEventListener("change", (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (ev) => loadData(parseCSV(ev.target.result));
      reader.readAsText(file, "utf-8");
    });

    ["dragover", "dragenter"].forEach((evt) =>
      uploadZone.addEventListener(evt, (e) => {
        e.preventDefault();
        uploadZone.classList.add("dragover");
      })
    );
    ["dragleave", "drop"].forEach((evt) =>
      uploadZone.addEventListener(evt, (e) => {
        e.preventDefault();
        uploadZone.classList.remove("dragover");
      })
    );
    uploadZone.addEventListener("drop", (e) => {
      const file = e.dataTransfer.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (ev) => loadData(parseCSV(ev.target.result));
      reader.readAsText(file, "utf-8");
    });

    document.getElementById("sample-data-btn").addEventListener("click", (e) => {
      e.stopPropagation();
      loadData(parseCSV(SAMPLE_CSV));
    });

    ["date-start", "date-end", "category-filter"].forEach((id) =>
      document.getElementById(id).addEventListener("change", applyFilters)
    );
    document.getElementById("search-input").addEventListener("input", debounce(applyFilters, 250));

    document.getElementById("reset-filters").addEventListener("click", () => {
      setupFilterOptions();
      document.getElementById("category-filter").value = "";
      document.getElementById("search-input").value = "";
      applyFilters();
    });

    document.querySelectorAll("[data-granularity]").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll("[data-granularity]").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        state.granularity = btn.dataset.granularity;
        renderTimeSeries();
      });
    });

    document.querySelectorAll("[data-keyword-type]").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll("[data-keyword-type]").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        state.keywordType = btn.dataset.keywordType;
        renderKeywordChart();
      });
    });

    window.addEventListener("resize", debounce(() => {
      if (filteredData.length) renderWordCloud();
    }, 300));

    document.getElementById("reload-upload-link").addEventListener("click", () => {
      document.getElementById("dashboard-content").classList.remove("visible");
      document.getElementById("upload-zone").style.display = "block";
    });

    // ── 자동 로드: trend_report.py가 생성한 dashboard_data.js가 있으면 즉시 렌더링 ──
    if (typeof REPORT_DATA !== "undefined" && REPORT_DATA.trim()) {
      const rows = parseCSV(REPORT_DATA);
      if (rows.length > 0) {
        loadData(rows);
        const genAt = typeof REPORT_GENERATED_AT !== "undefined" ? REPORT_GENERATED_AT : "";
        if (genAt) {
          document.getElementById("header-status").innerHTML += " · 생성 " + genAt;
        }
      }
    }
  }

  function debounce(fn, wait) {
    let t;
    return function (...args) {
      clearTimeout(t);
      t = setTimeout(() => fn.apply(this, args), wait);
    };
  }

  document.addEventListener("DOMContentLoaded", setupEvents);
})();
