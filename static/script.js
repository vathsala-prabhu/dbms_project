// ── Elements ──────────────────────────────────
const analyzeBtn   = document.getElementById('analyzeBtn');
const btnText      = document.getElementById('btnText');
const btnLoader    = document.getElementById('btnLoader');
const loadSample   = document.getElementById('loadSample');
const clearBtn     = document.getElementById('clearBtn');
const dnaInput     = document.getElementById('dnaSequence');
const patientInput = document.getElementById('patientName');
const isFastaChk   = document.getElementById('isFasta');
const resultsPanel = document.getElementById('results-panel');
const inputPanel   = document.getElementById('input-panel');
const errorMsg     = document.getElementById('error-msg');

const summaryBlock = document.getElementById('summary-block');
const statsBlock   = document.getElementById('stats-block');
const matchesBlock = document.getElementById('matches-block');

// ── Load Sample Sequence ──────────────────────
loadSample.addEventListener('click', async () => {
  try {
    const res  = await fetch('/sample');
    const data = await res.json();
    dnaInput.value       = data.sample_sequence;
    patientInput.value   = 'Sample Patient';
    isFastaChk.checked   = false;
  } catch {
    showError('Could not load sample sequence.');
  }
});

// ── Analyze ───────────────────────────────────
analyzeBtn.addEventListener('click', async () => {
  const sequence = dnaInput.value.trim();
  const patient  = patientInput.value.trim() || 'Anonymous';

  if (!sequence) {
    showError('Please enter a DNA sequence.');
    return;
  }

  setLoading(true);
  hideError();

  const payload = {
    patient_name: patient,
    dna_sequence: sequence,
    is_fasta: isFastaChk.checked
  };
  lastAnalysisPayload = payload;

  try {
    const res = await fetch('/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await res.json();

    if (data.error) {
      showError(data.error);
    } else {
      renderResults(data);
    }
  } catch (err) {
    showError('Server error. Make sure Flask is running on port 5000.');
  } finally {
    setLoading(false);
  }
});

// ── Clear Results ─────────────────────────────
clearBtn.addEventListener('click', () => {
  resultsPanel.classList.add('hidden');
  summaryBlock.innerHTML = '';
  statsBlock.innerHTML   = '';
  matchesBlock.innerHTML = '';
});

// ── Download PDF Report ───────────────────────
const downloadPdfBtn = document.getElementById('downloadPdf');
let lastAnalysisPayload = null;   // store payload for PDF re-use

downloadPdfBtn.addEventListener('click', async () => {
  if (!lastAnalysisPayload) { showError('Run an analysis first.'); return; }

  downloadPdfBtn.disabled    = true;
  downloadPdfBtn.textContent = 'Generating PDF…';

  try {
    const res = await fetch('/report', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(lastAnalysisPayload)
    });

    if (!res.ok) { throw new Error('PDF generation failed.'); }

    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;

    const cd   = res.headers.get('Content-Disposition') || '';
    const match = cd.match(/filename="?([^"]+)"?/);
    a.download = match ? match[1] : 'DNA_Report.pdf';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  } catch (err) {
    showError(err.message || 'Could not generate PDF.');
  } finally {
    downloadPdfBtn.disabled    = false;
    downloadPdfBtn.textContent = '⬇ Download PDF Report';
  }
});

// ── Render Results ────────────────────────────
function renderResults(data) {
  const { patient_name, sequence_stats, matches, risk_summary } = data;

  // Summary
  const overallRisk = risk_summary.overall_risk;
  const riskClass   = overallRisk === 'None Detected' ? 'risk-None' : `risk-${overallRisk}`;

  summaryBlock.innerHTML = `
    <div class="summary-card">
      <div class="summary-left">
        <h3>${escHtml(patient_name)}</h3>
        <p>Sequence length: ${sequence_stats.length.toLocaleString()} bp &nbsp;|&nbsp;
           Mutations found: ${data.total_matches}</p>
      </div>
      <div class="risk-badge ${riskClass}">
        ${overallRisk} Risk
      </div>
    </div>
    <div class="recommendation">${escHtml(risk_summary.recommendation)}</div>
  `;

  // Stats
  const bc = sequence_stats.base_counts;
  statsBlock.innerHTML = `
    <div class="stats-row">
      ${statBox(sequence_stats.gc_content + '%', 'GC Content')}
      ${statBox(bc.A.toLocaleString(), 'Adenine (A)')}
      ${statBox(bc.T.toLocaleString(), 'Thymine (T)')}
      ${statBox(bc.C.toLocaleString(), 'Cytosine (C)')}
      ${statBox(bc.G.toLocaleString(), 'Guanine (G)')}
    </div>
  `;

  // Matches
  if (matches.length === 0) {
    matchesBlock.innerHTML = `
      <div class="matches-title">Mutation Scan Results</div>
      <div class="no-match">✓ No known disease-associated mutations detected.</div>
    `;
  } else {
    const cards = matches.map(m => {
      const riskCls = `risk-${m.risk_level}`;
      return `
        <div class="match-card">
          <div class="match-top">
            <span class="match-disease">${escHtml(m.disease)}</span>
            <span class="risk-badge ${riskCls}">${m.risk_level}</span>
          </div>
          <div class="match-meta">
            <span>Gene: ${escHtml(m.gene)}</span>
            <span>SNP: ${escHtml(m.snp_id)}</span>
            <span>Strand: ${escHtml(m.strand)}</span>
            <span>Position: ${m.position}</span>
          </div>
          <div class="match-desc">${escHtml(m.description)}</div>
        </div>
      `;
    }).join('');

    matchesBlock.innerHTML = `
      <div class="matches-title">${matches.length} Mutation(s) Detected</div>
      ${cards}
    `;
  }

  resultsPanel.classList.remove('hidden');
  resultsPanel.scrollIntoView({ behavior: 'smooth' });
}

// ── Helpers ───────────────────────────────────
function statBox(value, label) {
  return `
    <div class="stat-box">
      <div class="stat-value">${value}</div>
      <div class="stat-label">${label}</div>
    </div>
  `;
}

function setLoading(state) {
  analyzeBtn.disabled = state;
  btnText.classList.toggle('hidden', state);
  btnLoader.classList.toggle('hidden', !state);
}

function showError(msg) {
  errorMsg.textContent = '⚠ ' + msg;
  errorMsg.classList.remove('hidden');
}

function hideError() {
  errorMsg.classList.add('hidden');
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}