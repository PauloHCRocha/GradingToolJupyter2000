<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { runtimeStage } from '../runtime/pyodide'
import LandingIcon from '../components/LandingIcon.vue'
import ThemeToggle from '../components/ThemeToggle.vue'

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

// --- Reveal-on-scroll ----------------------------------------------------
// IntersectionObserver toggles the `in-view` class once a section enters
// the viewport. Single observer instance, disconnected on unmount.
let io: IntersectionObserver | null = null
onMounted(() => {
  if (typeof window === 'undefined' || !('IntersectionObserver' in window)) return
  io = new IntersectionObserver(
    (entries) => {
      for (const e of entries) {
        if (e.isIntersecting) {
          e.target.classList.add('in-view')
          io?.unobserve(e.target)
        }
      }
    },
    { threshold: 0.12, rootMargin: '0px 0px -50px 0px' },
  )
  for (const el of document.querySelectorAll('.reveal')) {
    io.observe(el)
  }
})
onBeforeUnmount(() => {
  io?.disconnect()
  io = null
})
</script>

<template>
  <div class="landing">
    <!-- ==================== HERO ==================== -->
    <header class="hero">
      <nav class="topnav">
        <span class="logo">Granymede</span>
        <div class="topnav-actions">
          <ThemeToggle />
        </div>
      </nav>

      <div class="hero-inner">
        <div class="hero-text">
          <div class="badge">
            <span class="dot" />
            100% in-browser · no uploads · zero accounts
          </div>
          <h1>
            Grade Jupyter notebooks<br>
            <span class="accent">3× faster.</span>
          </h1>
          <p class="lead">
            A focused grading workspace for Python and Jupyter assignments.
            Question detection, side-by-side review, grade suggestions and
            plagiarism analysis — fast enough to grade a class in an afternoon.
          </p>
          <div class="cta-row">
            <button class="btn btn-primary big" @click="go">{{ ctaLabel }}</button>
          </div>
          <p class="micro">
            <span v-if="runtimeStage === 'ready'" class="ok">✓ Runtime ready — opens instantly.</span>
            <span v-else-if="runtimeStage === 'error'" class="warn">Runtime failed to load. Reload the page.</span>
            <span v-else>Python runtime is loading in the background while you read…</span>
          </p>
        </div>

        <div class="hero-art" aria-hidden="true">
          <div class="window float">
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

    <!-- ==================== SPEED CLAIM ==================== -->
    <section class="testimonial reveal">
      <div class="quote-card">
        <div class="stat">
          <strong>3×</strong>
          <span>faster grading</span>
        </div>
        <div class="claim">
          <h2>Notebook grading, compressed.</h2>
          <p>
            Question detection, grade suggestions and side-by-side review
            handle the mechanical parts of marking — the
            <span class="hl">potential to grade roughly 3× faster</span>
            on a typical Python or Jupyter assignment, leaving you with
            just the judgment calls.
          </p>
        </div>
      </div>
    </section>

    <!-- ==================== WORKFLOW PREVIEW ==================== -->
    <section class="workflow reveal">
      <header class="section-head">
        <h2>Inside the workspace</h2>
        <p>Three views handle the whole flow — drop the solution, grade student-by-student, then surface suspicious pairs.</p>
      </header>

      <div class="screens">
        <!-- Screen 1: Setup -->
        <article class="screen reveal">
          <div class="screen-tag">①  Setup</div>
          <div class="mock">
            <div class="mock-bar">
              <span class="dot r" /><span class="dot y" /><span class="dot g" />
              <span class="mock-title">Setup</span>
            </div>
            <div class="mock-body setup-mock">
              <div class="filebox">
                <span class="ico">📄</span>
                <span class="fname">assignment_2_solution.ipynb</span>
                <span class="ftag">analyzed</span>
              </div>
              <div class="meta-row">
                <span class="pill ok">8 detected</span>
                <span class="pill">20 pts total</span>
                <span class="pill">7 to grade</span>
              </div>
              <div class="qrow"><span class="check on">✓</span><code>Q1-1</code><span class="bar"><i style="width: 40%" /></span><span class="pts">2 pt</span></div>
              <div class="qrow"><span class="check on">✓</span><code>Q1-2</code><span class="bar"><i style="width: 40%" /></span><span class="pts">2 pt</span></div>
              <div class="qrow"><span class="check on">✓</span><code>Q2</code><span class="bar"><i style="width: 70%" /></span><span class="pts">8 pt</span></div>
              <div class="qrow off"><span class="check">✗</span><code>Q4</code><span class="bar"><i style="width: 30%" /></span><span class="pts">3 pt</span></div>
              <div class="dropzone">⬆  Drop submissions.zip</div>
            </div>
          </div>
        </article>

        <!-- Screen 2: Grading -->
        <article class="screen reveal">
          <div class="screen-tag">②  Grading</div>
          <div class="mock">
            <div class="mock-bar navy">
              <span class="dot r" /><span class="dot y" /><span class="dot g" />
              <span class="mock-title">Grading workspace</span>
            </div>
            <div class="mock-body grading-mock">
              <div class="g-top">
                <button class="g-nav">‹</button>
                <div class="g-name">
                  <strong>Alice Martin</strong>
                  <span>#10001 · 14 / 20</span>
                </div>
                <button class="g-nav">›</button>
              </div>
              <div class="g-chips">
                <span class="qchip done">Q1-1</span>
                <span class="qchip done">Q1-2</span>
                <span class="qchip active">Q2</span>
                <span class="qchip">Q3</span>
                <span class="qchip">Q4</span>
              </div>
              <div class="g-pane">
                <div class="g-col solution">
                  <div class="lbl">📘 Solution</div>
                  <div class="g-line"><span class="kw">def</span> <span class="fn">approximate_pi</span>(n):</div>
                  <div class="g-line">  inside = <span class="num">0</span></div>
                  <div class="g-line">  <span class="kw">for</span> _ <span class="kw">in</span> <span class="fn">range</span>(n):</div>
                </div>
                <div class="g-col student">
                  <div class="lbl">📝 Student</div>
                  <div class="g-line"><span class="kw">def</span> <span class="fn">approximate_pi</span>(N):</div>
                  <div class="g-line">  hit = <span class="num">0</span></div>
                  <div class="g-line">  <span class="kw">for</span> i <span class="kw">in</span> <span class="fn">range</span>(N):</div>
                </div>
              </div>
              <div class="g-actions">
                <span class="suggest-pill">✨ Suggest 1.75 / 2</span>
                <span class="comment-mini">"Use _ as loop var"</span>
                <span class="btn-mini">Save</span>
              </div>
            </div>
          </div>
        </article>

        <!-- Screen 3: Pair comparison -->
        <article class="screen reveal">
          <div class="screen-tag">③  Compare</div>
          <div class="mock">
            <div class="mock-bar navy">
              <span class="dot r" /><span class="dot y" /><span class="dot g" />
              <span class="mock-title">Compare pair</span>
            </div>
            <div class="mock-body compare-mock">
              <div class="cmp-head">
                <div class="cmp-pair">
                  <strong>Adam F.</strong>
                  <span class="cmp-arrow">↔</span>
                  <strong>Bruno S.</strong>
                </div>
                <span class="cmp-score danger">96%</span>
              </div>
              <div class="cmp-q">
                <code>Q4</code> <span class="cmp-q-sim">94%</span>
                <span class="cmp-tag">⚠ Identical block</span>
              </div>
              <div class="cmp-codes">
                <div class="cmp-col">
                  <div class="cmp-line dim"><span class="kw">def</span> <span class="fn">approximate_pi</span>(N):</div>
                  <div class="cmp-line dim">  inside = <span class="num">0</span></div>
                  <div class="cmp-block exact">
                    <span class="cmp-tag-mini">⚠</span>
                    <div class="cmp-line"><span class="kw">for</span> _ <span class="kw">in</span> <span class="fn">range</span>(N):</div>
                    <div class="cmp-line">  x = random()</div>
                    <div class="cmp-line">  y = random()</div>
                  </div>
                  <div class="cmp-line dim">    inside += <span class="num">1</span></div>
                </div>
                <div class="cmp-col">
                  <div class="cmp-line dim"><span class="kw">def</span> <span class="fn">approx_pi</span>(N):</div>
                  <div class="cmp-line dim">  cnt = <span class="num">0</span></div>
                  <div class="cmp-block exact">
                    <span class="cmp-tag-mini">⚠</span>
                    <div class="cmp-line"><span class="kw">for</span> _ <span class="kw">in</span> <span class="fn">range</span>(N):</div>
                    <div class="cmp-line">  x = random()</div>
                    <div class="cmp-line">  y = random()</div>
                  </div>
                  <div class="cmp-line dim">    cnt += <span class="num">1</span></div>
                </div>
              </div>
            </div>
          </div>
        </article>
      </div>
    </section>

    <!-- ==================== FEATURES ==================== -->
    <section class="features reveal">
      <header class="section-head">
        <h2>Built for the way you actually grade</h2>
        <p>Six things you'd hand-roll if you had the time. They're already here.</p>
      </header>
      <div class="grid">
        <article>
          <div class="ico"><LandingIcon name="privacy" /></div>
          <h3>Privacy by design</h3>
          <p>There's no backend. Student files are read in the browser and stay there. Closing the tab clears everything.</p>
        </article>
        <article>
          <div class="ico"><LandingIcon name="detect" /></div>
          <h3>Dynamic question detection</h3>
          <p>Drop your solution and the questions, sub-questions and points are extracted from the markdown automatically.</p>
        </article>
        <article>
          <div class="ico"><LandingIcon name="scale" /></div>
          <h3>AI-free grade suggestions</h3>
          <p>A transparent multi-criteria heuristic compares student code with your reference — imports, structures, output, and completeness.</p>
        </article>
        <article>
          <div class="ico"><LandingIcon name="shield" /></div>
          <h3>Plagiarism detection</h3>
          <p>Hybrid similarity (TF-IDF + AST + token Jaccard) surfaces suspicious pairs, clusters and a full similarity matrix.</p>
        </article>
        <article>
          <div class="ico"><LandingIcon name="play" /></div>
          <h3>Run student code safely</h3>
          <p>Execute submissions inside the browser sandbox. No subprocess on a server, no risk to your machine.</p>
        </article>
        <article>
          <div class="ico"><LandingIcon name="split" /></div>
          <h3>Side-by-side review</h3>
          <p>Your reference and the student's notebook are shown next to each other — drag the splitter to give either side more room.</p>
        </article>
      </div>
    </section>

    <!-- ==================== HOW IT WORKS ==================== -->
    <section class="how reveal">
      <header class="section-head">
        <h2>Three steps to a graded class</h2>
      </header>
      <ol class="steps">
        <li>
          <span class="num">1</span>
          <h3>Upload your solution</h3>
          <p>A <code>.ipynb</code> or <code>.py</code> with the reference answers. Questions and points are detected automatically. Untick the ones you're not grading this round.</p>
        </li>
        <li>
          <span class="num">2</span>
          <h3>Drop the submissions zip</h3>
          <p>Moodle-style folders are recognized by name and number. Empty or broken files are flagged but don't break the run.</p>
        </li>
        <li>
          <span class="num">3</span>
          <h3>Grade, suggest, export</h3>
          <p>Review side-by-side, accept the suggested grade or override, leave a comment, run the student's code in a sandbox, and export the gradebook as CSV.</p>
        </li>
      </ol>
    </section>

    <!-- ==================== WHO IT'S FOR ==================== -->
    <section class="audience reveal">
      <header class="section-head">
        <h2>Built for the realities of teaching</h2>
        <p>Three kinds of instructors keep us honest about what this tool needs to do.</p>
      </header>
      <div class="personas">
        <article>
          <div class="ico"><LandingIcon name="cap" /></div>
          <h3>University professors</h3>
          <p>Got a class of 80 Jupyter notebooks every assignment? Don't ship them through someone else's cloud. Run the whole grading workflow in your laptop's browser.</p>
        </article>
        <article>
          <div class="ico"><LandingIcon name="bolt" /></div>
          <h3>Bootcamp instructors</h3>
          <p>Tight turnarounds, lots of submissions. The dynamic question detector and the multi-criteria suggester get you 60% of the grade in 0% of the time.</p>
        </article>
        <article>
          <div class="ico"><LandingIcon name="users" /></div>
          <h3>Teaching assistants</h3>
          <p>You probably can't put student data on a third-party SaaS even if you wanted to. With this tool you don't have to ask — files literally cannot leave your machine.</p>
        </article>
      </div>
    </section>

    <!-- ==================== FAQ ==================== -->
    <section class="faq reveal">
      <header class="section-head">
        <h2>Frequently asked, briefly answered</h2>
      </header>
      <div class="faq-grid">
        <details>
          <summary>Is my students' data really private?</summary>
          <p>
            Yes. The page is static; the only network requests it makes are to load
            Pyodide (the Python runtime) from a CDN once, and to load this page itself
            from this site. Nothing about your files is ever sent anywhere. You can
            verify this in your browser's Network tab.
          </p>
        </details>
        <details>
          <summary>How big can the submissions zip be?</summary>
          <p>
            Whatever your browser can hold in RAM. ~80 student notebooks (a few MB of
            zip) work comfortably on any modern laptop. Multiple hundreds get sluggish
            on the plagiarism step because the similarity matrix grows quadratically.
          </p>
        </details>
        <details>
          <summary>Can I run the student's code? Is that safe?</summary>
          <p>
            Yes — the runner uses Pyodide's WebAssembly sandbox, which is the same
            isolation the browser gives every page. The student's code can't touch
            your filesystem, your microphone, or anything else outside the tab.
          </p>
        </details>
        <details>
          <summary>What if my solution doesn't follow the "Question N" pattern?</summary>
          <p>
            The detector picks up <code>Question N</code>, <code>QN</code>,
            <code>QN-M</code> with optional points like <code>(2 points)</code>. If
            your file doesn't, you'll see no questions detected — adjust your markdown
            or paste a renamed copy. You can also untick auto-detected ones you don't
            want to grade.
          </p>
        </details>
        <details>
          <summary>Does it work for plain <code>.py</code> files?</summary>
          <p>
            Yes. The same flow handles <code>.py</code> sources — the question
            detector reads docstrings and comments instead of markdown cells.
          </p>
        </details>
        <details>
          <summary>What gets cached and where?</summary>
          <p>
            Pyodide and a few JavaScript chunks are cached by the browser (HTTP
            cache) on first visit, so subsequent loads are instant. Your files,
            grades and plagiarism results live only in the tab's memory and are
            wiped when you close it.
          </p>
        </details>
      </div>
    </section>

    <!-- ==================== FINAL CTA ==================== -->
    <section class="final-cta reveal">
      <h2>Ready when you are.</h2>
      <p>Drop a solution, drop a zip, start grading.</p>
      <button class="btn btn-primary big" @click="go">{{ ctaLabel }}</button>
    </section>

    <footer class="foot">
      <p>Granymede · grading for Jupyter notebooks, in your browser</p>
    </footer>
  </div>
</template>


<style scoped>
.landing {
  background: var(--bg-page);
  color: var(--text);
  min-height: 100vh;
}

/* ---------- Reveal-on-scroll ---------- */
.reveal {
  opacity: 0;
  transform: translateY(20px);
  transition: opacity 0.6s ease, transform 0.6s ease;
}
.reveal.in-view { opacity: 1; transform: none; }
@media (prefers-reduced-motion: reduce) {
  .reveal { opacity: 1; transform: none; transition: none; }
}

/* ==================== HERO ==================== */
.hero {
  background:
    radial-gradient(circle at 80% 20%, rgba(56, 189, 248, 0.20), transparent 55%),
    radial-gradient(circle at 10% 80%, rgba(139, 92, 246, 0.16), transparent 55%),
    radial-gradient(circle at 50% 110%, rgba(236, 72, 153, 0.10), transparent 60%),
    linear-gradient(135deg, #1e3a5f 0%, #2c4a72 60%, #1e293b 100%);
  color: white;
  padding: 1rem 1.5rem 4rem;
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
  display: flex; align-items: center; justify-content: space-between;
  max-width: 1200px; margin: 0 auto 3rem;
  position: relative; z-index: 1;
}
.topnav .logo { font-size: 1rem; font-weight: 600; }
.topnav-actions { display: flex; gap: 0.5rem; align-items: center; }

.hero-inner {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1.1fr 1fr;
  gap: 3rem;
  align-items: center;
  position: relative; z-index: 1;
}

.hero-text .badge {
  display: inline-flex; align-items: center; gap: 0.45rem;
  background: rgba(255,255,255,0.1);
  border: 1px solid rgba(255,255,255,0.2);
  border-radius: 999px;
  padding: 0.3rem 0.85rem;
  font-size: 0.78rem;
  margin-bottom: 1.4rem;
}
.hero-text .badge .dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #6ee7b7;
  box-shadow: 0 0 10px #6ee7b7;
  animation: pulse 2s ease-in-out infinite;
}
@keyframes pulse { 50% { opacity: 0.4; transform: scale(0.8); } }

.hero-text h1 {
  font-size: clamp(2.1rem, 4.6vw, 3.6rem);
  line-height: 1.05;
  margin: 0 0 1.2rem;
  letter-spacing: -0.025em;
  font-weight: 750;
}
.hero-text h1 .accent {
  background: linear-gradient(120deg, #93c5fd 0%, #c4b5fd 50%, #f0abfc 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.hero-text .lead {
  font-size: 1.1rem;
  line-height: 1.6;
  color: rgba(255,255,255,0.86);
  margin: 0 0 1.8rem;
  max-width: 560px;
}

.cta-row { display: flex; gap: 0.75rem; flex-wrap: wrap; margin-bottom: 1rem; }
.btn.big {
  padding: 0.78rem 1.5rem;
  font-size: 1rem;
  border-radius: 8px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}
.btn.big.btn-primary {
  background: white;
  color: #1e3a5f;
  border: none;
  box-shadow: 0 4px 14px rgba(0,0,0,0.18);
  transition: transform 0.12s, box-shadow 0.15s;
}
.btn.big.btn-primary:hover { background: #f1f5f9; transform: translateY(-1px); box-shadow: 0 8px 20px rgba(0,0,0,0.22); }
.btn.big.ghost {
  background: rgba(255,255,255,0.08);
  color: white;
  border: 1px solid rgba(255,255,255,0.25);
  text-decoration: none;
}
.btn.big.ghost:hover { background: rgba(255,255,255,0.18); text-decoration: none; }

.micro { font-size: 0.82rem; color: rgba(255,255,255,0.65); margin: 0.4rem 0 0; }
.micro .ok { color: #6ee7b7; }
.micro .warn { color: #fca5a5; }

/* hero mockup window */
.hero-art { display: flex; justify-content: center; }
.window {
  width: 100%; max-width: 460px;
  background: #0f1d31;
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,0.12);
  box-shadow: 0 25px 50px rgba(0,0,0,0.35);
  overflow: hidden;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  transform: rotate(-1deg);
}
.window.float { animation: float 6s ease-in-out infinite; }
@keyframes float {
  0%, 100% { transform: rotate(-1deg) translateY(0); }
  50%      { transform: rotate(-1deg) translateY(-6px); }
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
.win-bar .win-title { margin-left: auto; margin-right: auto; font-size: 0.78rem; color: rgba(255,255,255,0.55); }
.win-body { padding: 0.85rem; font-size: 0.82rem; color: #e2e8f0; }
.cell { padding: 0.65rem 0.85rem; border-radius: 6px; margin-bottom: 0.55rem; }
.cell.md { background: rgba(167, 139, 250, 0.08); border-left: 3px solid #a78bfa; font-family: system-ui; font-size: 0.85rem; }
.cell.md .hl { color: #ddd6fe; font-weight: 600; }
.cell.md .muted { color: rgba(255,255,255,0.55); margin-top: 0.2rem; font-size: 0.8rem; }
.cell.code { background: rgba(34, 197, 94, 0.06); border-left: 3px solid #22c55e; line-height: 1.55; font-size: 0.79rem; }
.cell.code .kw { color: #c084fc; }
.cell.code .fn { color: #fbbf24; }
.cell.code .num { color: #5eead4; }
.grade-strip {
  display: flex; align-items: center; gap: 0.35rem;
  padding: 0.55rem 0.6rem;
  background: rgba(255,255,255,0.04);
  border-radius: 6px;
  font-family: ui-monospace, monospace; font-size: 0.75rem;
}
.qchip { padding: 0.15rem 0.5rem; border-radius: 4px; background: rgba(255,255,255,0.08); color: rgba(255,255,255,0.7); }
.qchip.on { background: #2563eb; color: white; }
.grade-score { margin-left: auto; color: #6ee7b7; font-weight: 600; }

/* ==================== Testimonial / speed ==================== */
.testimonial {
  padding: 4rem 1.5rem 2.5rem;
  background: var(--bg-page);
}
.quote-card {
  max-width: 880px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: auto 1fr;
  align-items: center;
  gap: 2rem;
  padding: 1.7rem 2rem;
  background: linear-gradient(135deg, var(--bg-card) 0%, var(--accent-soft) 100%);
  border: 1px solid var(--accent-bd);
  border-radius: 14px;
  box-shadow: 0 6px 20px rgba(15, 23, 42, 0.06);
}
.quote-card .stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-right: 1.6rem;
  border-right: 1px solid var(--accent-bd);
  min-width: 120px;
}
.quote-card .stat strong {
  font-size: clamp(2.4rem, 4.5vw, 3.4rem);
  line-height: 1;
  font-weight: 800;
  letter-spacing: -0.04em;
  color: var(--accent);
  font-variant-numeric: tabular-nums;
}
.quote-card .stat span {
  margin-top: 0.35rem;
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
  text-align: center;
}
.quote-card .claim h2 {
  margin: 0 0 0.4rem;
  font-size: clamp(1.15rem, 2vw, 1.45rem);
  line-height: 1.25;
  letter-spacing: -0.01em;
  color: var(--text-strong);
  font-weight: 700;
}
.quote-card .claim p {
  margin: 0;
  font-size: 0.95rem;
  line-height: 1.55;
  color: var(--text);
}
.quote-card .claim .hl {
  color: var(--accent);
  font-weight: 700;
}

@media (max-width: 700px) {
  .quote-card {
    grid-template-columns: 1fr;
    gap: 1rem;
    padding: 1.4rem 1.5rem;
  }
  .quote-card .stat {
    border-right: none;
    border-bottom: 1px solid var(--accent-bd);
    padding-right: 0;
    padding-bottom: 1rem;
  }
}

/* ==================== Section heads ==================== */
.section-head { max-width: 720px; margin: 0 auto 2.2rem; text-align: center; }
.section-head h2 {
  font-size: clamp(1.55rem, 3vw, 2.15rem);
  letter-spacing: -0.015em;
  color: var(--text-strong);
  margin: 0 0 0.6rem;
  font-weight: 700;
}
.section-head p { color: var(--text-muted); font-size: 1rem; margin: 0; line-height: 1.5; }

/* ==================== Workflow preview ==================== */
.workflow {
  padding: 5rem 1.5rem;
  background: var(--bg-page);
}
.screens {
  max-width: 1300px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.25rem;
}
.screen {
  position: relative;
  display: flex; flex-direction: column;
  transition: transform 0.2s, opacity 0.6s, transform 0.6s;
}
.screen:hover { transform: translateY(-4px); }
.screen-tag {
  display: inline-block;
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--accent);
  background: var(--accent-soft);
  padding: 0.2rem 0.7rem;
  border-radius: 999px;
  margin-bottom: 0.55rem;
  align-self: flex-start;
}
.mock {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 6px 24px rgba(15, 23, 42, 0.08);
  display: flex; flex-direction: column;
}
.mock-bar {
  display: flex; align-items: center; gap: 0.4rem;
  padding: 0.5rem 0.7rem;
  background: var(--bg-soft);
  border-bottom: 1px solid var(--border);
}
.mock-bar.navy {
  background: var(--header-bg);
  border-bottom-color: rgba(255,255,255,0.1);
}
.mock-bar.navy .mock-title { color: rgba(255,255,255,0.85); }
.mock-bar .dot { width: 10px; height: 10px; border-radius: 50%; }
.mock-bar .dot.r { background: #ef4444; }
.mock-bar .dot.y { background: #f59e0b; }
.mock-bar .dot.g { background: #22c55e; }
.mock-bar .mock-title { margin-left: auto; margin-right: auto; font-size: 0.78rem; color: var(--text-muted); }
.mock-body { padding: 0.85rem; min-height: 280px; }

/* Screen 1: Setup */
.setup-mock { display: flex; flex-direction: column; gap: 0.5rem; }
.filebox {
  display: flex; align-items: center; gap: 0.45rem;
  padding: 0.45rem 0.6rem;
  background: var(--success-soft);
  border: 1px solid var(--success-bd);
  border-radius: 6px;
  font-size: 0.8rem;
  color: var(--text);
}
.filebox .ico { font-size: 1rem; }
.filebox .fname { font-family: ui-monospace, monospace; font-weight: 500; }
.filebox .ftag {
  margin-left: auto;
  font-size: 0.68rem;
  color: var(--success);
  background: var(--bg-card);
  padding: 1px 7px;
  border-radius: 999px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.4px;
}
.meta-row { display: flex; gap: 0.35rem; flex-wrap: wrap; }
.meta-row .pill {
  font-size: 0.7rem;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--bg-soft);
  border: 1px solid var(--border);
  color: var(--text-muted);
}
.meta-row .pill.ok {
  background: var(--accent-soft);
  color: var(--accent-tx);
  border-color: var(--accent-bd);
  font-weight: 600;
}
.dropzone {
  margin-top: 0.2rem;
  padding: 0.55rem 0.6rem;
  border: 1px dashed var(--accent);
  border-radius: 6px;
  text-align: center;
  color: var(--accent);
  font-size: 0.82rem;
  font-weight: 500;
  background: var(--accent-soft);
}
.qrow {
  display: grid;
  grid-template-columns: 18px 60px 1fr 36px;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.82rem;
}
.qrow.off { opacity: 0.4; }
.qrow .check {
  display: inline-flex; align-items: center; justify-content: center;
  width: 18px; height: 18px; border-radius: 4px;
  background: var(--bg-soft); color: var(--text-muted);
  border: 1px solid var(--border-strong);
  font-size: 0.7rem;
}
.qrow .check.on { background: var(--success); color: white; border-color: var(--success); }
.qrow code { background: var(--accent-soft); color: var(--accent-tx); padding: 1px 6px; border-radius: 3px; font-size: 0.75rem; }
.qrow .bar {
  height: 6px;
  background: var(--bg-soft);
  border-radius: 3px;
  overflow: hidden;
}
.qrow .bar i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, var(--accent), #93c5fd);
  border-radius: 3px;
}
.qrow .pts { font-size: 0.72rem; color: var(--text-muted); text-align: right; }

/* Screen 2: Grading */
.grading-mock { display: flex; flex-direction: column; gap: 0.55rem; }
.g-top {
  display: flex; align-items: center; gap: 0.5rem;
  background: var(--bg-soft);
  border-radius: 6px;
  padding: 0.35rem 0.5rem;
}
.g-nav {
  width: 24px; height: 24px;
  border-radius: 4px;
  border: 1px solid var(--border-strong);
  background: var(--bg-card);
  color: var(--text);
  font-size: 0.85rem;
  display: inline-flex; align-items: center; justify-content: center;
  cursor: default;
}
.g-name { flex: 1; display: flex; flex-direction: column; gap: 1px; text-align: center; }
.g-name strong { font-size: 0.86rem; color: var(--text-strong); }
.g-name span { font-size: 0.72rem; color: var(--text-muted); font-family: ui-monospace, monospace; }
.g-chips { display: flex; gap: 0.3rem; flex-wrap: wrap; }
.g-chips .qchip {
  display: inline-flex;
  align-items: center;
  padding: 0.18rem 0.55rem;
  border-radius: 4px;
  font-size: 0.72rem;
  background: var(--bg-soft);
  color: var(--text);
  font-family: ui-monospace, monospace;
  border: 1px solid var(--border-strong);
}
.g-chips .qchip.done { border-color: var(--success); color: var(--success); }
.g-chips .qchip.active { background: var(--accent); color: white; border-color: var(--accent); }
.g-pane {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.4rem;
  font-family: ui-monospace, monospace;
  font-size: 0.72rem;
}
.g-col {
  padding: 0.45rem 0.55rem;
  border-radius: 6px;
  background: var(--code-bg);
  border-left: 3px solid;
}
.g-col.solution { border-left-color: var(--accent); }
.g-col.student { border-left-color: var(--success); }
.g-col .lbl { font-size: 0.65rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.4px; margin-bottom: 0.3rem; }
.g-col .g-line { line-height: 1.4; }
.g-col .kw { color: #8b5cf6; }
.g-col .fn { color: #d97706; }
.g-col .num { color: #0d9488; }
.g-actions { display: flex; align-items: center; gap: 0.45rem; }
.suggest-pill {
  background: var(--warning-soft);
  color: var(--warning-tx);
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 600;
}
.comment-mini {
  font-size: 0.72rem;
  color: var(--text-muted);
  font-style: italic;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.btn-mini {
  margin-left: auto;
  background: var(--accent); color: white;
  padding: 0.25rem 0.7rem; border-radius: 4px;
  font-size: 0.75rem; font-weight: 600;
}

/* Screen 3: Pair compare */
.compare-mock { display: flex; flex-direction: column; gap: 0.55rem; }
.cmp-head {
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.5rem 0.65rem;
  background: var(--danger-soft);
  border: 1px solid var(--danger-bd);
  border-radius: 6px;
}
.cmp-pair { display: flex; align-items: center; gap: 0.35rem; font-size: 0.85rem; flex: 1; }
.cmp-pair strong { color: var(--text-strong); }
.cmp-arrow { color: var(--text-muted); }
.cmp-score { font-weight: 700; font-size: 1rem; }
.cmp-score.danger { color: var(--danger); }
.cmp-q {
  display: flex; align-items: center; gap: 0.4rem;
  padding: 0.35rem 0.55rem;
  background: var(--bg-soft);
  border-radius: 4px;
  font-size: 0.78rem;
}
.cmp-q code {
  background: var(--accent-soft);
  color: var(--accent-tx);
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 0.78rem;
  font-weight: 600;
}
.cmp-q-sim { color: var(--danger); font-weight: 600; font-family: ui-monospace, monospace; }
.cmp-tag {
  margin-left: auto;
  font-size: 0.68rem;
  color: var(--danger);
  background: var(--bg-card);
  border: 1px solid var(--danger-bd);
  padding: 1px 7px;
  border-radius: 999px;
  font-weight: 600;
}
.cmp-codes {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.4rem;
  font-family: ui-monospace, monospace;
  font-size: 0.7rem;
  line-height: 1.45;
}
.cmp-col {
  padding: 0.4rem 0.5rem;
  border-radius: 6px;
  background: var(--code-bg);
  border: 1px solid var(--border);
}
.cmp-line { color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cmp-line.dim { color: var(--text-muted); }
.cmp-line .kw { color: #8b5cf6; }
.cmp-line .fn { color: #d97706; }
.cmp-line .num { color: #0d9488; }
.cmp-block {
  position: relative;
  margin: 0.25rem -0.25rem;
  padding: 0.3rem 0.4rem;
  border-radius: 4px;
}
.cmp-block.exact {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.16), rgba(239, 68, 68, 0.06));
  border: 1.5px solid var(--danger);
}
.cmp-tag-mini {
  position: absolute;
  top: -7px;
  right: -3px;
  background: var(--bg-card);
  border: 1px solid var(--danger);
  color: var(--danger);
  font-size: 0.6rem;
  padding: 0 4px;
  border-radius: 3px;
  line-height: 1.2;
  font-family: system-ui, sans-serif;
}

/* ==================== Features ==================== */
.features {
  padding: 5rem 1.5rem;
  background: var(--bg-card);
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
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
  display: inline-flex;
  width: 48px; height: 48px;
  align-items: center; justify-content: center;
  background: var(--accent-soft);
  color: var(--accent);
  border-radius: 10px;
  margin-bottom: 0.85rem;
  padding: 12px;
  transition: background 0.15s, color 0.15s, transform 0.15s;
}
.features article:hover .ico {
  background: var(--accent);
  color: white;
  transform: scale(1.05);
}
.features article h3 { margin: 0 0 0.4rem; font-size: 1.05rem; color: var(--text-strong); }
.features article p { margin: 0; color: var(--text); font-size: 0.92rem; line-height: 1.55; }

/* ==================== How ==================== */
.how { padding: 5rem 1.5rem; background: var(--bg-page); }
.how .steps {
  list-style: none; padding: 0;
  max-width: 1100px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
}
.how .steps li {
  position: relative;
  padding: 1.4rem;
  background: var(--bg-card);
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
.how .steps h3 { margin: 0 0 0.4rem; font-size: 1.05rem; color: var(--text-strong); }
.how .steps p { margin: 0; color: var(--text); font-size: 0.92rem; line-height: 1.55; }
.how .steps code {
  background: var(--accent-soft); color: var(--accent-tx);
  padding: 1px 6px; border-radius: 3px;
  font-size: 0.85em; border: 1px solid var(--accent-bd);
}

/* ==================== Audience ==================== */
.audience {
  padding: 5rem 1.5rem;
  background: var(--bg-card);
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
}
.personas {
  max-width: 1100px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}
.personas article {
  background: var(--bg-page);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1.6rem;
  text-align: left;
  transition: border-color 0.15s, transform 0.15s;
}
.personas article:hover { border-color: var(--accent); transform: translateY(-2px); }
.personas article .ico {
  display: inline-flex;
  width: 52px; height: 52px;
  align-items: center; justify-content: center;
  background: linear-gradient(135deg, var(--accent-soft), rgba(139, 92, 246, 0.18));
  color: var(--accent);
  border-radius: 14px;
  margin-bottom: 0.7rem;
  padding: 13px;
  transition: transform 0.15s;
}
.personas article:hover .ico { transform: rotate(-4deg) scale(1.06); }
.personas article h3 { margin: 0 0 0.45rem; color: var(--text-strong); font-size: 1.05rem; }
.personas article p { margin: 0; color: var(--text); font-size: 0.9rem; line-height: 1.55; }

/* ==================== FAQ ==================== */
.faq { padding: 5rem 1.5rem; background: var(--bg-card); border-top: 1px solid var(--border); }
.faq-grid {
  max-width: 900px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.7rem;
  /* Each <details> sizes itself; the adjacent cell shouldn't stretch to
     match an open row, otherwise it looks like both opened together. */
  align-items: start;
}
.faq details {
  background: var(--bg-page);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0.85rem 1rem;
  transition: border-color 0.15s;
}
.faq details:hover { border-color: var(--border-strong); }
.faq details[open] { border-color: var(--accent); }
.faq summary {
  cursor: pointer;
  list-style: none;
  font-weight: 600;
  color: var(--text-strong);
  position: relative;
  padding-right: 1.2rem;
  font-size: 0.95rem;
}
.faq summary::-webkit-details-marker { display: none; }
.faq summary::after {
  content: '+';
  position: absolute;
  right: 0; top: 50%;
  transform: translateY(-50%);
  color: var(--accent);
  font-weight: 400;
  font-size: 1.3rem;
  transition: transform 0.2s;
}
.faq details[open] summary::after { content: '–'; }
.faq summary code {
  background: var(--accent-soft);
  color: var(--accent-tx);
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 0.85em;
  font-weight: 500;
}
.faq details p {
  margin: 0.7rem 0 0;
  color: var(--text);
  font-size: 0.92rem;
  line-height: 1.55;
}
.faq details code {
  background: var(--accent-soft);
  color: var(--accent-tx);
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 0.86em;
}

/* ==================== Final CTA ==================== */
.final-cta {
  padding: 5rem 1.5rem;
  text-align: center;
  background:
    radial-gradient(circle at 50% 50%, rgba(37, 99, 235, 0.12), transparent 70%),
    var(--bg-page);
}
.final-cta h2 {
  font-size: clamp(1.7rem, 3.5vw, 2.5rem);
  margin: 0 0 0.6rem;
  color: var(--text-strong);
  font-weight: 700;
  letter-spacing: -0.015em;
}
.final-cta p { color: var(--text-muted); margin: 0 0 1.5rem; font-size: 1.05rem; }
.final-cta .btn.big.btn-primary {
  background: var(--accent); color: white; border: none;
  padding: 0.85rem 1.7rem; font-size: 1.05rem;
}
.final-cta .btn.big.btn-primary:hover { background: var(--accent-hover); }

/* ==================== Footer ==================== */
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

/* ==================== responsive ==================== */
@media (max-width: 1024px) {
  .screens { grid-template-columns: 1fr; max-width: 600px; }
  .features .grid { grid-template-columns: repeat(2, 1fr); }
  .how .steps { grid-template-columns: 1fr; }
  .personas { grid-template-columns: 1fr; }
  .faq-grid { grid-template-columns: 1fr; }
}
@media (max-width: 700px) {
  .hero { padding: 1rem 1.25rem 3rem; }
  .hero-inner { grid-template-columns: 1fr; gap: 2rem; }
  .hero-art { order: -1; }
  .window { transform: none; max-width: 380px; }
  .window.float { animation: none; }
  .features .grid { grid-template-columns: 1fr; }
}
</style>
