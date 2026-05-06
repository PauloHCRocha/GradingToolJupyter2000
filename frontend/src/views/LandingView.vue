<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { runtimeStage } from '../runtime/pyodide'

const router = useRouter()

const ctaLabel = computed(() => {
  switch (runtimeStage.value) {
    case 'ready':
      return 'Start grading →'
    case 'loading-runtime':
      return 'Loading runtime…  Start grading'
    case 'loading-modules':
      return 'Loading modules…  Start grading'
    case 'error':
      return 'Runtime failed — retry'
    default:
      return 'Start grading →'
  }
})

function go() {
  router.push('/setup')
}
</script>

<template>
  <div class="landing">
    <!-- Hero -->
    <header class="hero">
      <nav class="topnav">
        <span class="logo">📋 GradingToolJupyter2000</span>
        <a class="nav-link" href="https://github.com/PauloHCRocha/GradingToolJupyter2000" target="_blank" rel="noopener">
          <svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z"/></svg>
          GitHub
        </a>
      </nav>

      <div class="hero-inner">
        <div class="hero-text">
          <div class="badge">
            <span class="dot" />
            100% in-browser · no uploads · open source
          </div>
          <h1>
            Grade Jupyter notebooks<br>
            <span class="accent">without uploading anything.</span>
          </h1>
          <p class="lead">
            A simple, private grading workspace for Python and Jupyter assignments.
            Your students' files never leave your browser. There is no server.
          </p>
          <div class="cta-row">
            <button class="btn btn-primary big" @click="go">{{ ctaLabel }}</button>
            <a class="btn ghost big" href="https://github.com/PauloHCRocha/GradingToolJupyter2000"
               target="_blank" rel="noopener">★ View on GitHub</a>
          </div>
          <p class="micro">
            <span v-if="runtimeStage === 'ready'" class="ok">✓ Runtime ready — opens instantly.</span>
            <span v-else-if="runtimeStage === 'error'" class="warn">Runtime failed to load. Reload the page.</span>
            <span v-else>Python runtime is loading in the background while you read…</span>
          </p>
        </div>

        <div class="hero-art" aria-hidden="true">
          <div class="window">
            <div class="win-bar">
              <span class="dot r" />
              <span class="dot y" />
              <span class="dot g" />
              <span class="win-title">grading.ipynb</span>
            </div>
            <div class="win-body">
              <div class="cell md">
                <div class="hl">Question 1 (2 points)</div>
                <div class="muted">Count digits in a number using a while loop.</div>
              </div>
              <div class="cell code">
                <span class="kw">def</span> <span class="fn">count_digits</span>(n):<br>
                &nbsp;&nbsp;count = <span class="num">0</span><br>
                &nbsp;&nbsp;<span class="kw">while</span> n > <span class="num">0</span>:<br>
                &nbsp;&nbsp;&nbsp;&nbsp;n //= <span class="num">10</span><br>
                &nbsp;&nbsp;&nbsp;&nbsp;count += <span class="num">1</span><br>
                &nbsp;&nbsp;<span class="kw">return</span> count
              </div>
              <div class="grade-strip">
                <span class="qchip on">Q1-1</span>
                <span class="qchip on">Q1-2</span>
                <span class="qchip">Q2</span>
                <span class="qchip">Q3</span>
                <span class="qchip">Q4</span>
                <span class="grade-score">11.5 / 20</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </header>

    <!-- Features -->
    <section class="features">
      <header class="section-head">
        <h2>Everything in one page, nothing uploaded</h2>
        <p>The whole grading pipeline runs as Python in your browser via Pyodide.</p>
      </header>
      <div class="grid">
        <article>
          <div class="ico">🔒</div>
          <h3>Privacy by design</h3>
          <p>There's no backend. Student files are read in the browser and stay there. Closing the tab clears everything.</p>
        </article>
        <article>
          <div class="ico">🔍</div>
          <h3>Dynamic question detection</h3>
          <p>Drop your solution and the questions, sub-questions and points are extracted from the markdown automatically.</p>
        </article>
        <article>
          <div class="ico">⚖️</div>
          <h3>AI-free grade suggestions</h3>
          <p>A transparent multi-criteria heuristic compares student code with your reference — imports, structures, output, and completeness.</p>
        </article>
        <article>
          <div class="ico">🛡️</div>
          <h3>Plagiarism detection</h3>
          <p>Hybrid similarity (TF-IDF + AST + token Jaccard) surfaces suspicious pairs and a full similarity matrix.</p>
        </article>
        <article>
          <div class="ico">▶️</div>
          <h3>Run student code safely</h3>
          <p>Execute submissions inside the browser sandbox. No subprocess on a server, no risk to your machine.</p>
        </article>
        <article>
          <div class="ico">📋</div>
          <h3>Side-by-side review</h3>
          <p>Your reference and the student's notebook are shown next to each other — drag the splitter to give either side more room.</p>
        </article>
      </div>
    </section>

    <!-- How it works -->
    <section class="how">
      <header class="section-head">
        <h2>Three steps to a graded class</h2>
      </header>
      <ol class="steps">
        <li>
          <span class="num">1</span>
          <h3>Upload your solution</h3>
          <p>A <code>.ipynb</code> or <code>.py</code> with the reference answers. Questions and points are detected automatically.</p>
        </li>
        <li>
          <span class="num">2</span>
          <h3>Drop the submissions zip</h3>
          <p>Moodle-style folders are recognized by name and number. Empty or broken files are flagged but don't break the run.</p>
        </li>
        <li>
          <span class="num">3</span>
          <h3>Grade, suggest, export</h3>
          <p>Review side-by-side, accept the suggested grade or override, leave a comment, and export the gradebook as CSV.</p>
        </li>
      </ol>
    </section>

    <!-- Privacy block -->
    <section class="privacy">
      <div class="privacy-card">
        <div class="ico">🔐</div>
        <div>
          <h3>What "no uploads" actually means</h3>
          <p>
            The page you're reading is fully static. When you pick a file with the file
            picker, the browser hands the bytes to Pyodide — a Python runtime compiled to
            WebAssembly — that lives in this same tab. There is no API call, no cookie,
            no analytics, and no copy of your students' work outside your machine.
          </p>
          <p class="micro">
            We don't <em>promise</em> not to upload your files — we made sure we
            <em>cannot</em>.
          </p>
        </div>
      </div>
    </section>

    <!-- Final CTA -->
    <section class="final-cta">
      <h2>Ready?</h2>
      <p>Open the workspace — your files don't go anywhere they shouldn't.</p>
      <button class="btn btn-primary big" @click="go">{{ ctaLabel }}</button>
    </section>

    <footer class="foot">
      <p>
        Built with Vue 3, Vite and Pyodide. Open source under MIT.
        <a href="https://github.com/PauloHCRocha/GradingToolJupyter2000" target="_blank" rel="noopener">
          github.com/PauloHCRocha/GradingToolJupyter2000
        </a>
      </p>
    </footer>
  </div>
</template>

<style scoped>
.landing {
  background: var(--bg-page);
  color: var(--text);
  min-height: 100vh;
}

/* ---------- HERO ---------- */
.hero {
  background:
    radial-gradient(circle at 80% 20%, rgba(37, 99, 235, 0.18), transparent 55%),
    radial-gradient(circle at 10% 80%, rgba(99, 102, 241, 0.12), transparent 55%),
    linear-gradient(135deg, #1e3a5f 0%, #2c4a72 100%);
  color: white;
  padding: 1rem 1.5rem 5rem;
  position: relative;
  overflow: hidden;
}
.hero::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image:
    radial-gradient(rgba(255,255,255,0.08) 1px, transparent 1px);
  background-size: 32px 32px;
  pointer-events: none;
  mask-image: linear-gradient(to bottom, black 60%, transparent);
}

.topnav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: 1200px;
  margin: 0 auto 3rem;
  position: relative;
  z-index: 1;
}
.topnav .logo { font-size: 1rem; font-weight: 600; }
.topnav .nav-link {
  display: inline-flex; align-items: center; gap: 0.4rem;
  color: rgba(255,255,255,0.85);
  font-size: 0.88rem;
  padding: 0.45rem 0.85rem;
  border: 1px solid rgba(255,255,255,0.25);
  border-radius: 6px;
  text-decoration: none;
  transition: background 0.15s;
}
.topnav .nav-link:hover { background: rgba(255,255,255,0.1); text-decoration: none; }

.hero-inner {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1.1fr 1fr;
  gap: 3rem;
  align-items: center;
  position: relative;
  z-index: 1;
}

.hero-text .badge {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  background: rgba(255,255,255,0.1);
  border: 1px solid rgba(255,255,255,0.2);
  border-radius: 999px;
  padding: 0.3rem 0.85rem;
  font-size: 0.78rem;
  color: rgba(255,255,255,0.92);
  margin-bottom: 1.4rem;
}
.hero-text .badge .dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #6ee7b7;
  box-shadow: 0 0 10px #6ee7b7;
  animation: pulse 2s ease-in-out infinite;
}
@keyframes pulse {
  50% { opacity: 0.4; transform: scale(0.8); }
}

.hero-text h1 {
  font-size: clamp(2rem, 4.5vw, 3.4rem);
  line-height: 1.1;
  margin: 0 0 1.2rem;
  color: white;
  letter-spacing: -0.02em;
  font-weight: 700;
}
.hero-text h1 .accent {
  background: linear-gradient(120deg, #93c5fd 0%, #c4b5fd 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.hero-text .lead {
  font-size: 1.1rem;
  line-height: 1.55;
  color: rgba(255,255,255,0.85);
  margin: 0 0 1.8rem;
  max-width: 540px;
}

.cta-row {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-bottom: 1rem;
}
.btn.big {
  padding: 0.75rem 1.4rem;
  font-size: 1rem;
  border-radius: 8px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}
.btn.big.btn-primary {
  background: #ffffff;
  color: #1e3a5f;
  border: none;
  box-shadow: 0 4px 14px rgba(0,0,0,0.18);
}
.btn.big.btn-primary:hover { background: #f1f5f9; }
.btn.big.ghost {
  background: rgba(255,255,255,0.08);
  color: white;
  border: 1px solid rgba(255,255,255,0.25);
  text-decoration: none;
}
.btn.big.ghost:hover { background: rgba(255,255,255,0.16); text-decoration: none; }

.micro {
  font-size: 0.82rem;
  color: rgba(255,255,255,0.65);
  margin: 0.4rem 0 0;
}
.micro .ok { color: #6ee7b7; }
.micro .warn { color: #fca5a5; }

/* hero art (decorative window) */
.hero-art { display: flex; justify-content: center; }
.window {
  width: 100%;
  max-width: 460px;
  background: #0f1d31;
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,0.12);
  box-shadow: 0 25px 50px rgba(0,0,0,0.35);
  overflow: hidden;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  transform: rotate(-1deg);
}
.win-bar {
  display: flex; align-items: center; gap: 0.45rem;
  padding: 0.55rem 0.75rem;
  background: #1a2942;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.win-bar .dot { width: 11px; height: 11px; border-radius: 50%; }
.win-bar .dot.r { background: #ef4444; }
.win-bar .dot.y { background: #f59e0b; }
.win-bar .dot.g { background: #22c55e; }
.win-bar .win-title {
  margin-left: auto; margin-right: auto;
  font-size: 0.78rem; color: rgba(255,255,255,0.55);
}
.win-body { padding: 0.85rem; font-size: 0.82rem; color: #e2e8f0; }
.cell { padding: 0.65rem 0.85rem; border-radius: 6px; margin-bottom: 0.55rem; }
.cell.md {
  background: rgba(167, 139, 250, 0.08);
  border-left: 3px solid #a78bfa;
  font-family: system-ui;
  font-size: 0.85rem;
}
.cell.md .hl { color: #ddd6fe; font-weight: 600; }
.cell.md .muted { color: rgba(255,255,255,0.55); margin-top: 0.2rem; font-size: 0.8rem; }
.cell.code {
  background: rgba(34, 197, 94, 0.06);
  border-left: 3px solid #22c55e;
  line-height: 1.55;
  font-size: 0.79rem;
}
.cell.code .kw { color: #c084fc; }
.cell.code .fn { color: #fbbf24; }
.cell.code .num { color: #5eead4; }
.grade-strip {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.55rem 0.6rem;
  background: rgba(255,255,255,0.04);
  border-radius: 6px;
  font-family: ui-monospace, monospace;
  font-size: 0.75rem;
}
.qchip {
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  background: rgba(255,255,255,0.08);
  color: rgba(255,255,255,0.7);
}
.qchip.on { background: #2563eb; color: white; }
.grade-score { margin-left: auto; color: #6ee7b7; font-weight: 600; }

/* ---------- SECTIONS ---------- */
.section-head {
  max-width: 720px;
  margin: 0 auto 2.5rem;
  text-align: center;
}
.section-head h2 {
  font-size: clamp(1.5rem, 3vw, 2.1rem);
  letter-spacing: -0.01em;
  color: var(--text-strong);
  margin: 0 0 0.6rem;
}
.section-head p {
  color: var(--text-muted);
  font-size: 1rem;
  margin: 0;
}

.features {
  padding: 5rem 1.5rem;
  background: var(--bg-page);
}
.features .grid {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}
.features article {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1.4rem 1.4rem 1.5rem;
  transition: transform 0.15s, box-shadow 0.15s, border-color 0.15s;
}
.features article:hover {
  transform: translateY(-2px);
  border-color: var(--accent);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
}
.features article .ico {
  font-size: 1.6rem;
  display: inline-flex;
  width: 48px; height: 48px;
  align-items: center; justify-content: center;
  background: var(--accent-soft);
  border-radius: 10px;
  margin-bottom: 0.85rem;
}
.features article h3 {
  margin: 0 0 0.4rem;
  font-size: 1.05rem;
  color: var(--text-strong);
}
.features article p {
  margin: 0;
  color: var(--text);
  font-size: 0.92rem;
  line-height: 1.55;
}

/* How */
.how {
  padding: 5rem 1.5rem;
  background: var(--bg-card);
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
}
.how .steps {
  list-style: none;
  padding: 0;
  margin: 0;
  max-width: 1100px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
}
.how .steps li {
  position: relative;
  padding: 1.4rem;
  background: var(--bg-page);
  border-radius: 10px;
  border: 1px solid var(--border);
}
.how .steps .num {
  display: inline-flex;
  align-items: center; justify-content: center;
  width: 32px; height: 32px;
  background: var(--accent);
  color: white;
  border-radius: 50%;
  font-weight: 700;
  margin-bottom: 0.7rem;
}
.how .steps h3 {
  margin: 0 0 0.4rem;
  font-size: 1.05rem;
  color: var(--text-strong);
}
.how .steps p {
  margin: 0;
  color: var(--text);
  font-size: 0.92rem;
  line-height: 1.55;
}
.how .steps code {
  background: var(--accent-soft);
  color: #1e40af;
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 0.85em;
  border: 1px solid #bfdbfe;
}

/* Privacy block */
.privacy { padding: 4rem 1.5rem; background: var(--bg-page); }
.privacy-card {
  max-width: 900px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 1.5rem;
  padding: 2rem;
  background: linear-gradient(135deg, var(--bg-card) 0%, #f0f9ff 100%);
  border: 1px solid #bfdbfe;
  border-radius: 14px;
}
.privacy-card .ico {
  font-size: 2.4rem;
  width: 64px; height: 64px;
  display: flex; align-items: center; justify-content: center;
  background: white;
  border-radius: 14px;
  border: 1px solid #bfdbfe;
}
.privacy-card h3 {
  margin: 0 0 0.5rem;
  color: var(--text-strong);
  font-size: 1.15rem;
}
.privacy-card p {
  margin: 0 0 0.7rem;
  color: var(--text);
  font-size: 0.95rem;
  line-height: 1.6;
}
.privacy-card .micro {
  color: var(--text-muted);
  font-size: 0.85rem;
  margin-bottom: 0;
}
.privacy-card em {
  color: var(--accent);
  font-style: normal;
  font-weight: 600;
}

/* Final CTA */
.final-cta {
  padding: 5rem 1.5rem;
  text-align: center;
  background:
    radial-gradient(circle at 50% 50%, rgba(37, 99, 235, 0.12), transparent 70%),
    var(--bg-page);
}
.final-cta h2 {
  font-size: clamp(1.6rem, 3.5vw, 2.4rem);
  margin: 0 0 0.6rem;
  color: var(--text-strong);
}
.final-cta p {
  color: var(--text-muted);
  margin: 0 0 1.5rem;
  font-size: 1.05rem;
}
.final-cta .btn.big.btn-primary {
  background: var(--accent);
  color: white;
  border: none;
  padding: 0.8rem 1.6rem;
  font-size: 1.05rem;
}
.final-cta .btn.big.btn-primary:hover { background: var(--accent-hover); }

/* Footer */
.foot {
  padding: 2rem 1.5rem 3rem;
  background: var(--header-bg);
  color: rgba(255, 255, 255, 0.75);
  text-align: center;
  font-size: 0.85rem;
}
.foot p { margin: 0; }
.foot a { color: #93c5fd; }
.foot a:hover { color: white; }

/* ---------- responsive ---------- */
@media (max-width: 900px) {
  .hero { padding: 1rem 1.25rem 3rem; }
  .hero-inner { grid-template-columns: 1fr; gap: 2rem; }
  .hero-art { order: -1; }
  .window { transform: none; max-width: 380px; }
  .features .grid { grid-template-columns: 1fr; }
  .how .steps { grid-template-columns: 1fr; }
  .privacy-card { grid-template-columns: 1fr; }
}
</style>
