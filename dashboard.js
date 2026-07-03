(function () {
  'use strict';

  // ── 카테고리/센티먼트 색상 팔레트 (Canvas는 CSS 변수를 못 읽어서 hex로 고정) ──
  const CATEGORY_COLORS = {
    '규제/인허가': '#2DD4BF',
    'M&A/투자': '#7B8FE0',
    임상시험: '#4FB0E0',
    신제품출시: '#3FBCAE',
    '리콜/이슈': '#E8735A',
    '실적/경영': '#E0A542',
    'R&D/기술': '#62C48C',
    기타: '#8FA8BD',
  };
  const DEFAULT_CATEGORY_COLOR = '#8FA8BD';
  const SENTIMENT_COLORS = {
    긍정: '#2DD4BF',
    부정: '#E8735A',
    중립: '#8FA8BD',
  };
  const NODE_TYPE_COLORS = {
    company: '#2DD4BF',
    technology: '#E0A542',
    indication: '#E8735A',
  };

  let rawData = [];
  let filteredData = [];
  let charts = { timeseries: null, keyword: null, donut: null };
  let state = { granularity: 'day', keywordType: 'companies' };

  // ── CSV 파싱 & 정규화 ──────────────────────────────────────────────
  function splitMultiValue(str) {
    if (!str) return [];
    return String(str)
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
  }

  function normalizeRow(row) {
    return {
      published_date: (row.published_date || '').trim(),
      source: (row.source || '').trim(),
      title: (row.title || '').trim(),
      url: (row.url || '').trim(),
      image_url: (row.image_url || '').trim(),
      category: (row.category || '기타').trim() || '기타',
      companies: splitMultiValue(row.companies),
      products: splitMultiValue(row.products),
      technologies: splitMultiValue(row.technologies),
      indications: splitMultiValue(row.indications),
      competitor_flag:
        String(row.competitor_flag).toLowerCase() === 'true' ||
        row.competitor_flag === '1',
      sentiment: (row.sentiment || '').trim(),
      summary: (row.summary || '').trim(),
    };
  }

  function parseCSV(text) {
    const result = Papa.parse(text, { header: true, skipEmptyLines: true });
    return result.data
      .map(normalizeRow)
      .filter((r) => r.published_date && r.title);
  }

  // ── 데이터 로드 ────────────────────────────────────────────────────
  function loadData(rows) {
    rawData = rows.filter((r) => r.published_date);
    if (rawData.length === 0) {
      alert(
        'CSV에서 유효한 기사를 찾지 못했습니다. trend_report.py 출력 형식을 확인해주세요.',
      );
      return;
    }
    document.getElementById('upload-zone').style.display = 'none';
    document.getElementById('dashboard-content').classList.add('visible');

    setupFilterOptions();
    applyFilters();

    const dates = rawData.map((r) => r.published_date).sort();
    document.getElementById('header-status').innerHTML =
      '<span class="status-dot live"></span>' +
      dates[0] +
      ' ~ ' +
      dates[dates.length - 1] +
      ' · 기사 ' +
      rawData.length +
      '건';
    document.getElementById('reload-upload-link').style.display = 'inline';
  }

  function setupFilterOptions() {
    const categories = Array.from(
      new Set(rawData.map((r) => r.category)),
    ).sort();
    const select = document.getElementById('category-filter');
    select.innerHTML = '<option value="">전체</option>';
    categories.forEach((c) => {
      const opt = document.createElement('option');
      opt.value = c;
      opt.textContent = c;
      select.appendChild(opt);
    });

    const dates = rawData.map((r) => r.published_date).sort();
    document.getElementById('date-start').value = dates[0];
    document.getElementById('date-end').value = dates[dates.length - 1];
    document.getElementById('date-start').min = dates[0];
    document.getElementById('date-start').max = dates[dates.length - 1];
    document.getElementById('date-end').min = dates[0];
    document.getElementById('date-end').max = dates[dates.length - 1];
  }

  // ── 필터 적용 ──────────────────────────────────────────────────────
  function applyFilters() {
    const start = document.getElementById('date-start').value;
    const end = document.getElementById('date-end').value;
    const category = document.getElementById('category-filter').value;
    const search = document
      .getElementById('search-input')
      .value.trim()
      .toLowerCase();

    filteredData = rawData.filter((r) => {
      if (start && r.published_date < start) return false;
      if (end && r.published_date > end) return false;
      if (category && r.category !== category) return false;
      if (search) {
        const haystack = [
          r.title,
          ...r.companies,
          ...r.technologies,
          ...r.indications,
          ...r.products,
        ]
          .join(' ')
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
    renderNetworkGraph();
  }

  // ── KPI 카드 ──────────────────────────────────────────────────────
  function renderKPIs() {
    const total = filteredData.length;
    const categoryCounts = countBy(filteredData, 'category');
    const topCategory = Object.entries(categoryCounts).sort(
      (a, b) => b[1] - a[1],
    )[0];
    const competitorCount = filteredData.filter(
      (r) => r.competitor_flag,
    ).length;
    const companyCounts = {};
    filteredData.forEach((r) =>
      r.companies.forEach(
        (c) => (companyCounts[c] = (companyCounts[c] || 0) + 1),
      ),
    );
    const topCompany = Object.entries(companyCounts).sort(
      (a, b) => b[1] - a[1],
    )[0];
    const negativeCount = filteredData.filter(
      (r) => r.sentiment === '부정',
    ).length;

    const cards = [
      { label: '총 기사 수', value: total, sub: '선택 기간 내' },
      {
        label: '최다 카테고리',
        value: topCategory ? topCategory[0] : '-',
        sub: topCategory ? topCategory[1] + '건' : '',
        accent: true,
      },
      {
        label: '최다 언급 회사',
        value: topCompany ? topCompany[0] : '-',
        sub: topCompany ? topCompany[1] + '회' : '',
      },
      {
        label: '최다 언급 기술',
        value: topTech ? topTech[0] : '-',
        sub: topTech ? topTech[1] + '회' : '',
      },
      {
        label: '최다 언급 적응증',
        value: topIndication ? topIndication[0] : '-',
        sub: topIndication ? topIndication[1] + '회' : '',
      },
    ];

    const row = document.getElementById('kpi-row');
    row.innerHTML = cards
      .map(
        (c) =>
          '<div class="kpi-card"><div class="label">' +
          c.label +
          '</div>' +
          '<div class="value' +
          (c.accent ? ' accent' : '') +
          (c.warn ? ' warn' : '') +
          '">' +
          c.value +
          '</div>' +
          '<div class="sub">' +
          (c.sub || '') +
          '</div></div>',
      )
      .join('');
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
    const d = new Date(dateStr + 'T00:00:00');
    const day = d.getDay();
    const diff = (day === 0 ? -6 : 1) - day; // 월요일 기준
    d.setDate(d.getDate() + diff);
    return d.toISOString().slice(0, 10);
  }

  function renderTimeSeries() {
    const bucketFn = state.granularity === 'week' ? getWeekStart : (d) => d;
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
      stack: 's1',
    }));

    // 범례 렌더링 (Chart.js 기본 범례 대신 커스텀)
    document.getElementById('category-legend').innerHTML = categories
      .map(
        (cat) =>
          '<span class="legend-item"><span class="legend-dot" style="background:' +
          (CATEGORY_COLORS[cat] || DEFAULT_CATEGORY_COLOR) +
          ';"></span>' +
          cat +
          '</span>',
      )
      .join('');

    if (charts.timeseries) charts.timeseries.destroy();
    const ctx = document.getElementById('timeseries-chart');
    charts.timeseries = new Chart(ctx, {
      type: 'bar',
      data: { labels: labels, datasets: datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { mode: 'index', intersect: false },
        },
        scales: {
          x: {
            stacked: true,
            ticks: { color: '#8FA8BD', font: { size: 11 } },
            grid: { color: 'rgba(242,239,230,0.06)' },
          },
          y: {
            stacked: true,
            ticks: { color: '#8FA8BD', precision: 0 },
            grid: { color: 'rgba(242,239,230,0.06)' },
          },
        },
      },
    });
  }

  // ── 02. 키워드 빈도 차트 ───────────────────────────────────────────
  function renderKeywordChart() {
    const field = state.keywordType;
    const counts = {};
    filteredData.forEach((r) =>
      r[field].forEach((v) => (counts[v] = (counts[v] || 0) + 1)),
    );
    const top = Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10);

    if (charts.keyword) charts.keyword.destroy();
    const ctx = document.getElementById('keyword-chart');

    if (top.length === 0) {
      ctx.getContext('2d').clearRect(0, 0, ctx.width, ctx.height);
      return;
    }

    charts.keyword = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: top.map((t) => t[0]),
        datasets: [
          {
            label: '언급 횟수',
            data: top.map((t) => t[1]),
            backgroundColor: '#2DD4BF',
            borderRadius: 3,
          },
        ],
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: {
            ticks: { color: '#8FA8BD', precision: 0 },
            grid: { color: 'rgba(242,239,230,0.06)' },
          },
          y: {
            ticks: { color: '#F2EFE6', font: { size: 12 } },
            grid: { display: false },
          },
        },
      },
    });
  }

  // ── 03. 카테고리 도넛 ──────────────────────────────────────────────
  function renderCategoryDonut() {
    const counts = countBy(filteredData, 'category');
    const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
    const total = filteredData.length || 1;

    if (charts.donut) charts.donut.destroy();
    const ctx = document.getElementById('category-donut');
    charts.donut = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: entries.map((e) => e[0]),
        datasets: [
          {
            data: entries.map((e) => e[1]),
            backgroundColor: entries.map(
              (e) => CATEGORY_COLORS[e[0]] || DEFAULT_CATEGORY_COLOR,
            ),
            borderColor: '#092538',
            borderWidth: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '62%',
        plugins: { legend: { display: false } },
      },
    });

    document.getElementById('category-legend-donut').innerHTML = entries
      .map(
        (e) =>
          '<div style="display:flex; justify-content:space-between; font-size:12px; padding:4px 0; color:var(--text-dim);">' +
          '<span><span class="legend-dot" style="background:' +
          (CATEGORY_COLORS[e[0]] || DEFAULT_CATEGORY_COLOR) +
          '; display:inline-block; margin-right:6px;"></span>' +
          e[0] +
          '</span>' +
          '<span>' +
          e[1] +
          '건 · ' +
          Math.round((e[1] / total) * 100) +
          '%</span></div>',
      )
      .join('');
  }

  // ── 04. 인텔리전스 맵 (D3 force network) ──────────────────────────
  function renderNetworkGraph() {
    const svg = d3.select('#network-svg');
    svg.selectAll('*').remove();

    const nodeMap = {};
    const linkCounts = {};

    function ensureNode(name, type) {
      const id = type + ':' + name;
      if (!nodeMap[id])
        nodeMap[id] = { id: id, name: name, type: type, count: 0 };
      nodeMap[id].count += 1;
      return id;
    }

    filteredData.forEach((r) => {
      const companyIds = r.companies.map((c) => ensureNode(c, 'company'));
      const techIds = r.technologies.map((t) => ensureNode(t, 'technology'));
      const indicationIds = r.indications.map((i) =>
        ensureNode(i, 'indication'),
      );

      const pairs = [];
      companyIds.forEach((c) => techIds.forEach((t) => pairs.push([c, t])));
      companyIds.forEach((c) =>
        indicationIds.forEach((i) => pairs.push([c, i])),
      );
      techIds.forEach((t) => indicationIds.forEach((i) => pairs.push([t, i])));

      pairs.forEach(([a, b]) => {
        const key = a < b ? a + '|' + b : b + '|' + a;
        linkCounts[key] = (linkCounts[key] || 0) + 1;
      });
    });

    const nodes = Object.values(nodeMap);
    const links = Object.entries(linkCounts).map(([key, weight]) => {
      const [source, target] = key.split('|');
      return { source, target, weight };
    });

    if (nodes.length === 0) return;

    const container = document.getElementById('network-svg');
    const width = container.clientWidth || 900;
    const height = 480;
    svg.attr('viewBox', '0 0 ' + width + ' ' + height);

    const maxCount = Math.max(...nodes.map((n) => n.count));
    const radiusScale = d3.scaleSqrt().domain([1, maxCount]).range([5, 26]);

    const simulation = d3
      .forceSimulation(nodes)
      .force(
        'link',
        d3
          .forceLink(links)
          .id((d) => d.id)
          .distance(70)
          .strength(0.3),
      )
      .force('charge', d3.forceManyBody().strength(-140))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force(
        'collision',
        d3.forceCollide().radius((d) => radiusScale(d.count) + 6),
      );

    const link = svg
      .append('g')
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('class', 'link-line')
      .attr('stroke-width', (d) => Math.min(1 + d.weight * 0.8, 6));

    const node = svg
      .append('g')
      .selectAll('circle')
      .data(nodes)
      .join('circle')
      .attr('class', 'node-circle')
      .attr('r', (d) => radiusScale(d.count))
      .attr('fill', (d) => NODE_TYPE_COLORS[d.type])
      .call(
        d3.drag().on('start', dragStart).on('drag', dragged).on('end', dragEnd),
      )
      .on('mouseenter', highlightNode)
      .on('mouseleave', clearHighlight);

    const label = svg
      .append('g')
      .selectAll('text')
      .data(nodes)
      .join('text')
      .attr('class', 'node-label')
      .attr('text-anchor', 'middle')
      .attr('dy', (d) => -radiusScale(d.count) - 6)
      .text((d) => d.name);

    simulation.on('tick', () => {
      link
        .attr('x1', (d) => d.source.x)
        .attr('y1', (d) => d.source.y)
        .attr('x2', (d) => d.target.x)
        .attr('y2', (d) => d.target.y);
      node.attr('cx', (d) => d.x).attr('cy', (d) => d.y);
      label.attr('x', (d) => d.x).attr('y', (d) => d.y);
    });

    function dragStart(event, d) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }
    function dragged(event, d) {
      d.fx = event.x;
      d.fy = event.y;
    }
    function dragEnd(event, d) {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }

    function highlightNode(event, d) {
      const connected = new Set([d.id]);
      links.forEach((l) => {
        if (l.source.id === d.id) connected.add(l.target.id);
        if (l.target.id === d.id) connected.add(l.source.id);
      });
      node.attr('opacity', (n) => (connected.has(n.id) ? 1 : 0.15));
      link.attr('opacity', (l) =>
        l.source.id === d.id || l.target.id === d.id ? 0.9 : 0.05,
      );
      label
        .attr(
          'class',
          (n) => 'node-label' + (connected.has(n.id) ? '' : ' node-label-dim'),
        )
        .attr('opacity', (n) => (connected.has(n.id) ? 1 : 0.15));
    }
    function clearHighlight() {
      node.attr('opacity', 1);
      link.attr('opacity', 1);
      label.attr('opacity', 1).attr('class', 'node-label');
    }
  }

  // ── 01. 최신 주요 기사 (카드뉴스 3x2 그리드) ──────────────────────
  function renderTopArticles() {
    const top6 = [...filteredData]
      .sort((a, b) =>
        a.published_date < b.published_date
          ? 1
          : a.published_date > b.published_date
            ? -1
            : 0,
      )
      .slice(0, 6);

    const grid = document.getElementById('top-articles-grid');

    if (top6.length === 0) {
      grid.innerHTML =
        '<div class="empty-state" style="grid-column:1/-1;">표시할 기사가 없습니다.</div>';
      return;
    }

    grid.innerHTML = top6
      .map((r) => {
        const hasImage = !!r.image_url;
        const catColor = CATEGORY_COLORS[r.category] || DEFAULT_CATEGORY_COLOR;
        const safeImageUrl = (r.image_url || '')
          .replace(/"/g, '%22')
          .replace(/'/g, '%27');
        const bgStyle = hasImage
          ? ' style="background-image:url(&quot;' + safeImageUrl + '&quot;);"'
          : '';
        return (
          '<a class="top-card' +
          (hasImage ? '' : ' no-image') +
          '"' +
          bgStyle +
          ' href="' +
          escapeHtml(r.url) +
          '" target="_blank" rel="noopener">' +
          '<div class="top-card-overlay"></div>' +
          '<div class="top-card-content">' +
          '<span class="top-card-eyebrow" style="color:' +
          catColor +
          '">| ' +
          escapeHtml(r.category) +
          '</span>' +
          '<h3 class="top-card-title">' +
          escapeHtml(r.title) +
          '</h3>' +
          '<span class="top-card-source">' +
          escapeHtml(r.source) +
          ' · ' +
          r.published_date +
          '</span>' +
          '</div></a>'
        );
      })
      .join('');
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str || '';
    return div.innerHTML;
  }

  // ── 이벤트 바인딩 ──────────────────────────────────────────────────
  function setupEvents() {
    const uploadZone = document.getElementById('upload-zone');
    const fileInput = document.getElementById('file-input');

    document
      .getElementById('pick-file-btn')
      .addEventListener('click', () => fileInput.click());
    uploadZone.addEventListener('click', (e) => {
      if (e.target.id === 'pick-file-btn' || e.target.id === 'sample-data-btn')
        return;
      fileInput.click();
    });

    fileInput.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (ev) => loadData(parseCSV(ev.target.result));
      reader.readAsText(file, 'utf-8');
    });

    ['dragover', 'dragenter'].forEach((evt) =>
      uploadZone.addEventListener(evt, (e) => {
        e.preventDefault();
        uploadZone.classList.add('dragover');
      }),
    );
    ['dragleave', 'drop'].forEach((evt) =>
      uploadZone.addEventListener(evt, (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
      }),
    );
    uploadZone.addEventListener('drop', (e) => {
      const file = e.dataTransfer.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (ev) => loadData(parseCSV(ev.target.result));
      reader.readAsText(file, 'utf-8');
    });

    document
      .getElementById('sample-data-btn')
      .addEventListener('click', (e) => {
        e.stopPropagation();
        loadData(parseCSV(SAMPLE_CSV));
      });

    ['date-start', 'date-end', 'category-filter'].forEach((id) =>
      document.getElementById(id).addEventListener('change', applyFilters),
    );
    document
      .getElementById('search-input')
      .addEventListener('input', debounce(applyFilters, 250));

    document.getElementById('reset-filters').addEventListener('click', () => {
      setupFilterOptions();
      document.getElementById('category-filter').value = '';
      document.getElementById('search-input').value = '';
      applyFilters();
    });

    document.querySelectorAll('[data-granularity]').forEach((btn) => {
      btn.addEventListener('click', () => {
        document
          .querySelectorAll('[data-granularity]')
          .forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        state.granularity = btn.dataset.granularity;
        renderTimeSeries();
      });
    });

    document.querySelectorAll('[data-keyword-type]').forEach((btn) => {
      btn.addEventListener('click', () => {
        document
          .querySelectorAll('[data-keyword-type]')
          .forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        state.keywordType = btn.dataset.keywordType;
        renderKeywordChart();
      });
    });

    window.addEventListener(
      'resize',
      debounce(() => {
        if (filteredData.length) renderNetworkGraph();
      }, 300),
    );

    document
      .getElementById('reload-upload-link')
      .addEventListener('click', () => {
        document
          .getElementById('dashboard-content')
          .classList.remove('visible');
        document.getElementById('upload-zone').style.display = 'block';
      });

    // ── 자동 로드: trend_report.py가 생성한 dashboard_data.js가 있으면 즉시 렌더링 ──
    if (typeof REPORT_DATA !== 'undefined' && REPORT_DATA.trim()) {
      const rows = parseCSV(REPORT_DATA);
      if (rows.length > 0) {
        loadData(rows);
        const genAt =
          typeof REPORT_GENERATED_AT !== 'undefined' ? REPORT_GENERATED_AT : '';
        if (genAt) {
          document.getElementById('header-status').innerHTML +=
            ' · 생성 ' + genAt;
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

  document.addEventListener('DOMContentLoaded', setupEvents);
})();
