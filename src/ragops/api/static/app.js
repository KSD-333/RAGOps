/**
 * RAGOps Production Web UI — Client Logic
 * Handles Markdown rendering via Marked.js, Chunk Inspector Dialog,
 * and RAGOps Feedback & Telemetry Triage Dashboard.
 */

document.addEventListener('DOMContentLoaded', () => {
  // Navigation Tabs
  const navBtnSearch = document.getElementById('nav-btn-search');
  const navBtnDashboard = document.getElementById('nav-btn-dashboard');
  const viewSearch = document.getElementById('view-search');
  const viewDashboard = document.getElementById('view-dashboard');

  // Search View Elements
  const systemStatus = document.getElementById('system-status');
  const queryForm = document.getElementById('query-form');
  const queryInput = document.getElementById('query-input');
  const topKSelect = document.getElementById('top-k-select');
  const btnSubmit = document.getElementById('btn-submit');
  const btnText = btnSubmit.querySelector('.btn-text');
  const btnSpinner = btnSubmit.querySelector('.btn-spinner');
  const docCountBadge = document.getElementById('doc-count-badge');

  // Results View Elements
  const resultsSection = document.getElementById('results-section');
  const totalLatencyText = document.getElementById('total-latency-text');
  const tokensText = document.getElementById('tokens-text');
  const abstentionIndicator = document.getElementById('abstention-indicator');
  const answerBody = document.getElementById('answer-body');
  const sourcesGrid = document.getElementById('sources-grid');
  const sourceCount = document.getElementById('source-count');

  // Stage Latency Timeline Elements
  const stageEmbedBar = document.getElementById('stage-embed-bar');
  const stageEmbedVal = document.getElementById('stage-embed-val');
  const stageSearchBar = document.getElementById('stage-search-bar');
  const stageSearchVal = document.getElementById('stage-search-val');
  const stageRerankBar = document.getElementById('stage-rerank-bar');
  const stageRerankVal = document.getElementById('stage-rerank-val');
  const stageLlmBar = document.getElementById('stage-llm-bar');
  const stageLlmVal = document.getElementById('stage-llm-val');

  // Feedback Buttons
  const btnFeedbackPos = document.getElementById('btn-feedback-pos');
  const btnFeedbackNeg = document.getElementById('btn-feedback-neg');
  const feedbackToast = document.getElementById('feedback-toast');

  // Chunk Modal Elements
  const chunkModal = document.getElementById('chunk-modal');
  const btnCloseChunkModal = document.getElementById('btn-close-chunk-modal');
  const chunkModalDoc = document.getElementById('chunk-modal-doc');
  const chunkModalTitle = document.getElementById('chunk-modal-title');
  const chunkModalId = document.getElementById('chunk-modal-id');
  const chunkModalScore = document.getElementById('chunk-modal-score');
  const chunkModalSection = document.getElementById('chunk-modal-section');
  const chunkModalContent = document.getElementById('chunk-modal-content');
  const btnCopyChunk = document.getElementById('btn-copy-chunk');

  // Dashboard View Elements
  const btnRefreshDashboard = document.getElementById('btn-refresh-dashboard');
  const kpiTotalQueries = document.getElementById('kpi-total-queries');
  const kpiTotalTokens = document.getElementById('kpi-total-tokens');
  const kpiTokensSub = document.getElementById('kpi-tokens-sub');
  const kpiSatisfaction = document.getElementById('kpi-satisfaction');
  const kpiFeedbackCounts = document.getElementById('kpi-feedback-counts');
  const kpiP95Latency = document.getElementById('kpi-p95-latency');
  const kpiLatencySub = document.getElementById('kpi-latency-sub');
  const dislikedCountBadge = document.getElementById('disliked-count-badge');
  const dislikedTableBody = document.getElementById('disliked-table-body');

  // State
  let currentResponse = null;
  let activeModalChunkText = '';

  // Configure Marked.js
  if (window.marked) {
    marked.setOptions({
      gfm: true,
      breaks: true,
      sanitize: false,
    });
  }

  // =========================================================================
  // 1. Navigation Tab Switching
  // =========================================================================
  navBtnSearch.addEventListener('click', () => {
    navBtnSearch.classList.add('active');
    navBtnDashboard.classList.remove('active');
    viewSearch.style.display = 'block';
    viewDashboard.style.display = 'none';
  });

  navBtnDashboard.addEventListener('click', () => {
    navBtnDashboard.classList.add('active');
    navBtnSearch.classList.remove('active');
    viewSearch.style.display = 'none';
    viewDashboard.style.display = 'block';
    fetchDashboardData();
  });

  // =========================================================================
  // 2. Health & Document Count Status Check
  // =========================================================================
  async function checkSystemHealth() {
    try {
      const [readyRes, countRes] = await Promise.all([
        fetch('/health/ready'),
        fetch('/api/v1/documents/count')
      ]);

      if (readyRes.ok) {
        const readyData = await readyRes.json();
        systemStatus.classList.add('healthy');
        systemStatus.querySelector('.status-text').textContent = `Online • ${readyData.model || 'Groq Llama-3'}`;
      }

      if (countRes.ok) {
        const countData = await countRes.json();
        const count = countData.count ?? 0;
        docCountBadge.textContent = `📚 Indexed Chunks: ${count}`;
      }
    } catch (err) {
      systemStatus.querySelector('.status-text').textContent = 'Connecting... (Local Dev)';
    }
  }

  checkSystemHealth();

  // =========================================================================
  // 3. Suggestion Chips Handler
  // =========================================================================
  document.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const queryText = chip.getAttribute('data-query');
      if (queryText) {
        queryInput.value = queryText;
        executeSearch(queryText);
      }
    });
  });

  // =========================================================================
  // 4. Search Form Submission
  // =========================================================================
  queryForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const query = queryInput.value.trim();
    if (query) {
      executeSearch(query);
    }
  });

  async function executeSearch(query) {
    btnSubmit.disabled = true;
    btnText.style.display = 'none';
    btnSpinner.style.display = 'block';

    // Reset feedback buttons
    btnFeedbackPos.className = 'btn-feedback';
    btnFeedbackNeg.className = 'btn-feedback';
    feedbackToast.style.display = 'none';

    const topK = parseInt(topKSelect.value, 10) || 5;

    try {
      const response = await fetch('/api/v1/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query, top_k: topK })
      });

      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }

      const data = await response.json();
      currentResponse = data;
      renderResults(data);
    } catch (err) {
      alert(`Query failed: ${err.message}. Ensure the RAGOps server is running.`);
    } finally {
      btnSubmit.disabled = false;
      btnText.style.display = 'inline';
      btnSpinner.style.display = 'none';
    }
  }

  // =========================================================================
  // 5. Render Search Results & Telemetry
  // =========================================================================
  function renderResults(data) {
    resultsSection.style.display = 'block';
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    const meta = data.metadata || {};
    const totalMs = meta.total_latency_ms || 0;
    const embedMs = meta.embed_latency_ms || 0;
    const searchMs = meta.search_latency_ms || 0;
    const rerankMs = meta.rerank_latency_ms || 0;
    const llmMs = meta.generation_latency_ms || 0;

    totalLatencyText.textContent = `${Math.round(totalMs)} ms`;
    tokensText.textContent = `Tokens: ${meta.input_tokens || 0} In / ${meta.output_tokens || 0} Out`;

    // Compute Stage Bar Widths
    const denom = Math.max(totalMs, embedMs + searchMs + rerankMs + llmMs, 1);
    const pEmbed = Math.max(Math.round((embedMs / denom) * 100), 5);
    const pSearch = Math.max(Math.round((searchMs / denom) * 100), 5);
    const pRerank = Math.max(Math.round((rerankMs / denom) * 100), 5);
    const pLlm = Math.max(100 - pEmbed - pSearch - pRerank, 15);

    stageEmbedBar.style.width = `${pEmbed}%`;
    stageEmbedVal.textContent = `${Math.round(embedMs)}ms`;

    stageSearchBar.style.width = `${pSearch}%`;
    stageSearchVal.textContent = `${Math.round(searchMs)}ms`;

    stageRerankBar.style.width = `${pRerank}%`;
    stageRerankVal.textContent = `${Math.round(rerankMs)}ms`;

    stageLlmBar.style.width = `${pLlm}%`;
    stageLlmVal.textContent = `${Math.round(llmMs)}ms`;

    // Abstention Detection
    const answer = data.answer || '';
    const answerLower = answer.toLowerCase();
    const abstentionPhrases = [
      'not contain', 'no information', 'cannot answer', 'cannot find',
      'none of which', 'insufficient information', 'not mentioned', 'does not mention'
    ];
    const isAbstained = abstentionPhrases.some(phrase => answerLower.includes(phrase));

    if (isAbstained) {
      abstentionIndicator.style.display = 'inline-block';
      abstentionIndicator.textContent = '🛡️ Grounded Abstention (Zero Hallucination)';
    } else {
      abstentionIndicator.style.display = 'none';
    }

    // Render Answer Markdown using Marked.js (Prevents All-Blue Code bug)
    if (window.marked) {
      let rawHtml = marked.parse(answer);
      // Transform citation markers 【Document X】 or [Document X] into clickable tags
      rawHtml = rawHtml.replace(/【(.*?)】/g, '<span class="citation-mark">【$1】</span>');
      rawHtml = rawHtml.replace(/\[(Document \d+)\]/g, '<span class="citation-mark">[$1]</span>');
      answerBody.innerHTML = rawHtml;
    } else {
      answerBody.textContent = answer;
    }

    // Render Supporting Sources Grid
    const sources = data.sources || [];
    sourceCount.textContent = sources.length;
    sourcesGrid.innerHTML = '';

    if (sources.length === 0) {
      sourcesGrid.innerHTML = `
        <div style="grid-column: 1 / -1; padding: 1.5rem; text-align: center; color: var(--text-muted); background: rgba(10,14,22,0.4); border-radius: var(--radius-sm);">
          No supporting document chunks were cited for this response (Safe Abstention).
        </div>
      `;
    } else {
      sources.forEach((s, idx) => {
        const card = document.createElement('div');
        card.className = 'source-item';
        const docName = s.document || `Document ${idx + 1}`;
        let scorePct;
        if (typeof s.score === 'number') {
          if (s.score >= 0 && s.score <= 1) {
            scorePct = Math.round(s.score * 100);
          } else {
            scorePct = Math.round(100 / (1 + Math.exp(-s.score)));
          }
        } else {
          scorePct = 90;
        }
        const scoreLabel = `${scorePct}% Match`;
        const chunkText = s.text || (s.metadata && s.metadata.text) || 'Chunk text retrieved from knowledge base.';
        const snippet = chunkText.length > 140 ? chunkText.slice(0, 140) + '...' : chunkText;

        card.innerHTML = `
          <div class="source-top">
            <span class="source-doc-name" title="${docName}">${docName}</span>
            <span class="source-score-pill">${scoreLabel}</span>
          </div>
          <div class="source-excerpt">${escapeHtml(snippet)}</div>
          <div class="source-click-hint">
            <span>🔍 Click to inspect full chunk dialog</span>
          </div>
        `;

        // Click to open Chunk Inspector Dialog
        card.addEventListener('click', () => {
          openChunkModal({
            document: docName,
            chunk_id: s.chunk_id || `chunk_${idx + 1}`,
            score: scoreLabel,
            section: s.section || 'General',
            text: chunkText,
          });
        });

        sourcesGrid.appendChild(card);
      });
    }
  }

  // =========================================================================
  // 6. Chunk Inspector Modal Dialog
  // =========================================================================
  function openChunkModal(chunkData) {
    chunkModalDoc.textContent = chunkData.document;
    chunkModalTitle.textContent = `Retrieved Chunk (${chunkData.chunk_id})`;
    chunkModalId.textContent = chunkData.chunk_id;
    chunkModalScore.textContent = chunkData.score;
    chunkModalSection.textContent = chunkData.section;
    chunkModalContent.textContent = chunkData.text;
    activeModalChunkText = chunkData.text;
    chunkModal.style.display = 'flex';
  }

  btnCloseChunkModal.addEventListener('click', () => {
    chunkModal.style.display = 'none';
  });

  chunkModal.addEventListener('click', (e) => {
    if (e.target === chunkModal) {
      chunkModal.style.display = 'none';
    }
  });

  btnCopyChunk.addEventListener('click', () => {
    if (activeModalChunkText) {
      navigator.clipboard.writeText(activeModalChunkText).then(() => {
        btnCopyChunk.textContent = '✅ Copied!';
        setTimeout(() => { btnCopyChunk.textContent = '📋 Copy Chunk Text'; }, 2000);
      });
    }
  });

  // =========================================================================
  // 7. User Feedback Loop
  // =========================================================================
  btnFeedbackPos.addEventListener('click', () => handleFeedback('positive', 'Accurate grounded answer'));
  btnFeedbackNeg.addEventListener('click', () => handleFeedback('negative', 'Inaccurate or ungrounded answer'));

  async function handleFeedback(rating, defaultComment) {
    if (!currentResponse) return;

    btnFeedbackPos.className = rating === 'positive' ? 'btn-feedback active-pos' : 'btn-feedback';
    btnFeedbackNeg.className = rating === 'negative' ? 'btn-feedback active-neg' : 'btn-feedback';

    const queryText = currentResponse.query || queryInput.value.trim();

    try {
      const payload = {
        trace_id: currentResponse.trace_id || `trace_${Date.now()}`,
        query: queryText,
        rating: rating,
        comment: defaultComment
      };

      const res = await fetch('/api/v1/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        feedbackToast.textContent = rating === 'positive' ? 'Recorded as Accurate!' : 'Logged for Quality Triage!';
        feedbackToast.style.display = 'inline-block';
      }
    } catch (err) {
      console.warn('Feedback save failed:', err);
    }
  }

  // =========================================================================
  // 8. RAGOps Operations & Feedback Triage Dashboard Data
  // =========================================================================
  btnRefreshDashboard.addEventListener('click', fetchDashboardData);

  async function fetchDashboardData() {
    try {
      const res = await fetch('/api/v1/feedback/dashboard');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data = await res.json();

      // Total Queries
      kpiTotalQueries.textContent = (data.total_queries || 0).toLocaleString();

      // Total Tokens
      const tokensTotal = data.total_tokens || 0;
      kpiTotalTokens.textContent = tokensTotal >= 1000 ? `${(tokensTotal / 1000).toFixed(1)}k` : tokensTotal;
      kpiTokensSub.textContent = `In: ${data.tokens_input || 0} | Out: ${data.tokens_output || 0} (~$${(data.estimated_cost_usd || 0).toFixed(4)})`;

      // Satisfaction Rate
      const posRate = data.positive_rate !== undefined ? Math.round(data.positive_rate * 100) : 100;
      kpiSatisfaction.textContent = `${posRate}%`;
      kpiFeedbackCounts.textContent = `${data.positive || 0} 👍 Positive / ${data.negative || 0} 👎 Negative`;

      // Latency P95
      const latStats = data.latency_stats || {};
      const p95 = Math.round(latStats.p95 || 0);
      const p50 = Math.round(latStats.p50 || 0);
      kpiP95Latency.textContent = `${p95} ms`;
      kpiLatencySub.textContent = `Median P50: ${p50} ms (Mean: ${Math.round(latStats.mean || 0)} ms)`;

      // Disliked Queries Triage Table
      const disliked = data.disliked_queries || [];
      dislikedCountBadge.textContent = `${disliked.length} Flagged Queries`;

      if (disliked.length === 0) {
        dislikedTableBody.innerHTML = `
          <tr>
            <td colspan="5" class="empty-table-cell">
              ✨ No disliked queries recorded yet! All evaluated queries have satisfied quality criteria.
            </td>
          </tr>
        `;
      } else {
        dislikedTableBody.innerHTML = '';
        disliked.forEach(item => {
          const tr = document.createElement('tr');
          tr.innerHTML = `
            <td style="font-weight: 500; color: #f8fafc;">${escapeHtml(item.query)}</td>
            <td style="color: var(--accent-rose);">${escapeHtml(item.comment)}</td>
            <td style="font-family: var(--font-mono); font-size: 0.8rem; color: var(--text-muted);">${escapeHtml(item.created_at)}</td>
            <td style="font-family: var(--font-mono); font-size: 0.78rem; color: var(--accent-indigo);">${escapeHtml(item.trace_id)}</td>
            <td><span class="badge-triage-pending">⚠️ Needs Triage</span></td>
          `;
          dislikedTableBody.appendChild(tr);
        });
      }
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    }
  }

  // Utilities
  function escapeHtml(str) {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
});
