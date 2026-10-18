/**
 * RAGOps Production Web UI — Client Logic
 */

document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements
  const systemStatus = document.getElementById('system-status');
  const queryForm = document.getElementById('query-form');
  const queryInput = document.getElementById('query-input');
  const topKSelect = document.getElementById('top-k-select');
  const btnSubmit = document.getElementById('btn-submit');
  const btnText = btnSubmit.querySelector('.btn-text');
  const btnSpinner = btnSubmit.querySelector('.btn-spinner');
  
  const resultsSection = document.getElementById('results-section');
  const totalLatencyText = document.getElementById('total-latency-text');
  const tokensText = document.getElementById('tokens-text');
  const abstentionIndicator = document.getElementById('abstention-indicator');
  const answerBody = document.getElementById('answer-body');
  const sourcesGrid = document.getElementById('sources-grid');
  const sourceCount = document.getElementById('source-count');
  const docCountBadge = document.getElementById('doc-count-badge');

  // Timeline Segments
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

  // Metrics Modal
  const btnMetrics = document.getElementById('btn-metrics');
  const metricsModal = document.getElementById('metrics-modal');
  const btnCloseModal = document.getElementById('btn-close-modal');
  const metricModel = document.getElementById('metric-model');
  const metricDocs = document.getElementById('metric-docs');
  const metricsRawOutput = document.getElementById('metrics-raw-output');

  // State
  let currentResponse = null;

  // 1. Initial Health & Doc Count Check
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
        if (metricModel && readyData.model) {
          metricModel.textContent = readyData.model;
        }
      }

      if (countRes.ok) {
        const countData = await countRes.json();
        const count = countData.count ?? 0;
        docCountBadge.textContent = `📚 Indexed Chunks: ${count}`;
        if (metricDocs) {
          metricDocs.textContent = `${count} Chunks`;
        }
      }
    } catch (err) {
      systemStatus.querySelector('.status-text').textContent = 'Connecting... (Local Dev)';
    }
  }

  checkSystemHealth();

  // 2. Chip Click Handler
  document.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const queryText = chip.getAttribute('data-query');
      if (queryText) {
        queryInput.value = queryText;
        executeSearch(queryText);
      }
    });
  });

  // 3. Search Form Submit
  queryForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const query = queryInput.value.trim();
    if (query) {
      executeSearch(query);
    }
  });

  // 4. Execute Search
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
      const t0 = performance.now();
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

  // 5. Render Results
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

    // Format Markdown in Answer
    answerBody.innerHTML = formatMarkdown(answer);

    // Render Sources
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
        const score = s.score !== undefined ? `${Math.round(s.score * 100)}% Match` : `Chunk #${idx + 1}`;
        const text = s.text || '';

        card.innerHTML = `
          <div class="source-top">
            <span class="source-doc-name" title="${docName}">${docName}</span>
            <span class="source-score-pill">${score}</span>
          </div>
          <div class="source-excerpt">${escapeHtml(text)}</div>
        `;

        card.addEventListener('click', () => {
          card.classList.toggle('expanded');
        });

        sourcesGrid.appendChild(card);
      });
    }
  }

  // 6. Simple Markdown Formatter
  function formatMarkdown(text) {
    if (!text) return '';

    let formatted = escapeHtml(text);

    // Bold **text**
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Inline code `code`
    formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Citation markers 【Document X】 or [Document X]
    formatted = formatted.replace(/【(.*?)】/g, '<span class="citation-mark">【$1】</span>');
    formatted = formatted.replace(/\[(Document \d+)\]/g, '<span class="citation-mark">[$1]</span>');

    // Convert newlines to paragraphs
    const paragraphs = formatted.split(/\n\s*\n/);
    return paragraphs.map(p => `<p>${p.replace(/\n/g, '<br>')}</p>`).join('');
  }

  function escapeHtml(str) {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // 7. Feedback Submission
  btnFeedbackPos.addEventListener('click', () => handleFeedback(1, true));
  btnFeedbackNeg.addEventListener('click', () => handleFeedback(-1, false));

  async function handleFeedback(rating, isRelevant) {
    if (!currentResponse) return;

    btnFeedbackPos.className = rating > 0 ? 'btn-feedback active-pos' : 'btn-feedback';
    btnFeedbackNeg.className = rating < 0 ? 'btn-feedback active-neg' : 'btn-feedback';

    try {
      const payload = {
        query_id: currentResponse.query_id || `q_${Date.now()}`,
        rating: rating,
        is_relevant: isRelevant,
        comment: rating > 0 ? 'Accurate grounded answer' : 'Inaccurate or ungrounded'
      };

      const res = await fetch('/api/v1/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        feedbackToast.textContent = 'Feedback recorded in telemetry loop!';
        feedbackToast.style.display = 'inline-block';
      }
    } catch (err) {
      console.warn('Feedback save failed:', err);
    }
  }

  // 8. Telemetry Modal Handlers
  btnMetrics.addEventListener('click', async () => {
    metricsModal.style.display = 'flex';
    metricsRawOutput.textContent = 'Fetching live Prometheus metrics...';

    try {
      const res = await fetch('/metrics');
      if (res.ok) {
        const metrics = await res.json();
        metricsRawOutput.textContent = JSON.stringify(metrics, null, 2);
      } else {
        metricsRawOutput.textContent = `Metrics endpoint returned HTTP ${res.status}`;
      }
    } catch (e) {
      metricsRawOutput.textContent = `Failed to load metrics: ${e.message}`;
    }
  });

  btnCloseModal.addEventListener('click', () => {
    metricsModal.style.display = 'none';
  });

  metricsModal.addEventListener('click', (e) => {
    if (e.target === metricsModal) {
      metricsModal.style.display = 'none';
    }
  });
});
