<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { runtimeStage } from '../runtime/pyodide'
import BrandMark from '../components/BrandMark.vue'
import ThemeToggle from '../components/ThemeToggle.vue'
import gradingShot from '../assets/landing/grading.jpg'
import setupShot from '../assets/landing/setup.jpg'
import consoleCard from '../assets/landing/console-student.jpg'
import consoleSolution from '../assets/landing/console-solution.jpg'

const router = useRouter()

const runtimeNote = computed(() => {
  switch (runtimeStage.value) {
    case 'ready':
      return 'Python is loaded — the grading screens open straight away.'
    case 'error':
      return 'Python failed to load. Reload the page to try again.'
    default:
      return 'Python is loading in the background while you read.'
  }
})

function go() {
  router.push('/setup')
}

const repo = 'https://github.com/PauloHCRocha/GradingToolJupyter2000'

// Real input and output of anonymizer.py, as [text, kind] segments per line.
type Seg = [string, '' | 'pii' | 'ph']
const before: Seg[][] = [
  [['# Nome: ', ''], ['Ana Ribeiro', 'pii']],
  [['# Número: ', ''], ['2023101', 'pii']],
  [['# ', ''], ['ana.ribeiro@alunos.exemplo.pt', 'pii']],
  [['import math', '']],
  [['', '']],
  [['def area(r):', '']],
  [['    return math.pi * r ** 2', '']],
]
const after: Seg[][] = [
  [['# Nome: ', ''], ['<REDACTED>', 'ph']],
  [['# Número: ', ''], ['<REDACTED>', 'ph']],
  [['# ', ''], ['<EMAIL>', 'ph']],
  [['import math', '']],
  [['', '']],
  [['def area(r):', '']],
  [['    return math.pi * r ** 2', '']],
]

// The exported CSV, as in the screenshots (one comment column shown).
const csv = [
  ['Ana Ribeiro', '2023101', '2', '', '3', '1', '6'],
  ['Bruno Costa', '2023102', '1.5', 'Usa 3.14 em vez de math.pi…', '3', '0', '4.5'],
  ['Carla Mendes', '2023103', '2', '', '3', '1', '6'],
  ['Duarte Sousa', '2023104', '1.5', 'Mesmo problema que na Q1…', '3', '1', '5.5'],
]

// Mini similarity matrix for the plagiarism card (lower triangle).
const heat = [[], [0.32], [0.41, 0.28], [0.36, 0.96, 0.3], [0.22, 0.38, 0.45, 0.33]]
function heatColor(v: number) {
  if (v > 0.9) return '#e5484d'
  if (v > 0.6) return '#f59e0b'
  if (v > 0.4) return '#c4b13a'
  return '#8cc084'
}
</script>

<template>
  <div class="landing">
    <!-- ==================== HERO ==================== -->
    <section class="hero">
      <svg class="orbits" viewBox="0 0 1200 640" preserveAspectRatio="xMaxYMin slice" aria-hidden="true">
        <g transform="rotate(-14 930 150)" fill="none" stroke="currentColor">
          <ellipse cx="930" cy="150" rx="560" ry="185" />
          <ellipse cx="930" cy="150" rx="380" ry="125" />
          <ellipse cx="930" cy="150" rx="215" ry="70" />
          <circle cx="1000" cy="273" r="9" class="moon" stroke="none" />
          <circle cx="1104" cy="206" r="5" class="moon-2" stroke="none" />
        </g>
      </svg>

      <header class="masthead topnav">
        <div class="wrap masthead-inner">
          <RouterLink to="/" class="brand"><BrandMark />Granymede</RouterLink>
          <nav class="links" aria-label="On this page">
            <a href="#how">How it works</a>
            <a href="#features">Features</a>
            <a href="#privacy">Privacy</a>
            <a href="#faq">Questions</a>
            <ThemeToggle />
          </nav>
        </div>
      </header>

      <div class="wrap hero-copy">
        <p class="kicker">Grading for Python and Jupyter assignments</p>
        <h1>
          Every answer
          <span class="marked">next to your solution<svg class="pen" viewBox="0 0 300 14" preserveAspectRatio="none" aria-hidden="true"><path d="M3 10 C 50 4, 120 12, 180 7 S 270 3, 297 8" /></svg></span>,<br class="wide-only" />
          one question at a time.
        </h1>
        <p class="lead">
          Load your solution and the students' files. Granymede finds the questions, puts each answer
          beside yours, runs the code when you need it and keeps the grades. It all happens in your
          browser, so the files never leave your computer.
        </p>
        <div class="cta">
          <button class="start" @click="go">Start grading</button>
          <a class="see" href="#how">See how it works</a>
        </div>
        <p class="runtime" :class="runtimeStage">
          <span class="dot" />{{ runtimeNote }}
        </p>
      </div>

      <div class="wrap stage">
        <img class="shot-main" :src="gradingShot" width="2200" height="1004"
             alt="The grading screen: question 1 for the student Bruno Costa, graded 1.5 out of 2, with the solution and his answer side by side." />
        <img class="shot-float" :src="consoleCard" width="1000" height="333"
             alt="The student's program run in a console: given 21, it prints 2121." />
      </div>
    </section>

    <!-- ==================== HOW ==================== -->
    <section id="how" class="how wrap">
      <header class="section-head">
        <p class="eyebrow">How it works</p>
        <h2>A grading session, from the zip to the CSV</h2>
      </header>

      <ol class="steps">
        <li class="step">
          <div class="step-text">
            <span class="step-n">1</span>
            <h3>Drop in your solution and the students' work</h3>
            <p>
              Your solution file, <code>.py</code> or <code>.ipynb</code>, tells Granymede where each question
              starts and what it is worth: a comment such as <code># Q1 (2 points)</code> is enough, or a
              markdown heading in a notebook. The students' files can come straight from the zip that Moodle
              gives you, or one by one.
            </p>
          </div>
          <figure class="shot">
            <img :src="setupShot" width="1200" height="819" loading="lazy"
                 alt="The setup screen with a solution file of three questions and a zip of four students loaded." />
            <figcaption>Three questions found in the solution, four students in the zip.</figcaption>
          </figure>
        </li>

        <li class="step flip">
          <div class="step-text">
            <span class="step-n">2</span>
            <h3>Read, run, grade</h3>
            <p>
              Move through the class with the arrow keys. For each question you see the statement, your
              solution and the student's answer. Not sure the code works? Run it: when it asks for input you
              type it, as in a terminal, and run your solution with the same input to compare.
            </p>
          </div>
          <figure class="shot consoles-fig">
            <div class="stacked">
              <img :src="consoleCard" width="1000" height="333" loading="lazy"
                   alt="The student's console: given 21, the program prints 2121." />
              <img :src="consoleSolution" width="1000" height="333" loading="lazy"
                   alt="The solution's console: given 21, the program prints 42." />
            </div>
            <p class="verdict">≠ The output differs from the solution for these inputs</p>
            <figcaption>Bruno forgot <code>int()</code>: given 21, his program prints 2121 and the solution prints 42.</figcaption>
          </figure>
        </li>

        <li class="step">
          <div class="step-text">
            <span class="step-n">3</span>
            <h3>Export the grades</h3>
            <p>
              One CSV file: a row per student, a column per question and your comments. It imports into
              Moodle and opens in Excel with the accents intact.
            </p>
          </div>
          <figure class="shot sheet-fig">
            <div class="sheet" role="img" aria-label="An excerpt of the exported CSV file.">
              <div class="sheet-bar"><span class="file">grades.csv</span></div>
              <table>
                <thead>
                  <tr><th>Student Name</th><th>Number</th><th>Q1</th><th>Q1_comment</th><th>Q2</th><th>Q3</th><th>Total</th></tr>
                </thead>
                <tbody>
                  <tr v-for="row in csv" :key="row[1]">
                    <td v-for="(cell, i) in row" :key="i" :class="{ num: i !== 0 && i !== 3, note: i === 3 }">{{ cell }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <figcaption>An excerpt of the exported file.</figcaption>
          </figure>
        </li>
      </ol>
    </section>

    <!-- ==================== FEATURES ==================== -->
    <section id="features" class="features wrap">
      <header class="section-head">
        <p class="eyebrow">Features</p>
        <h2>What else it does</h2>
      </header>
      <div class="cards">
        <article class="card">
          <div class="frag frag-console" aria-hidden="true">
            <pre><span class="kw">while</span> True:
    i += 1</pre>
            <span class="frag-status">⏱ Stopped after 10 s</span>
          </div>
          <h3>Runs code safely</h3>
          <p>In a separate Python inside the page, with a time limit, so an endless loop can't freeze the tab. You edit a copy; the submission never changes.</p>
        </article>

        <article class="card">
          <div class="frag frag-suggest" aria-hidden="true">
            <div class="row"><span class="pill high">high</span><strong>2 / 2</strong><span class="muted">· score 100%</span></div>
            <div class="row small">Pontos fortes: boa estrutura lógica, output adequado</div>
          </div>
          <h3>Suggests a grade</h3>
          <p>A simple comparison with your solution (structure, imports, output) proposes a grade and a comment. You decide.</p>
        </article>

        <article class="card">
          <div class="frag frag-heat" aria-hidden="true">
            <div class="heat">
              <template v-for="(row, i) in heat" :key="i">
                <span v-for="j in 5" :key="j" class="cell"
                      :style="j - 1 < row.length ? { background: heatColor(row[j - 1]) } : j - 1 === i ? {} : { visibility: 'hidden' }"
                      :class="{ diag: j - 1 === i }" />
              </template>
            </div>
            <span class="heat-note"><strong>96%</strong> Bruno ↔ Duarte</span>
          </div>
          <h3>Looks for copied work</h3>
          <p>Compares every pair of submissions, groups the similar ones and opens any pair side by side, with the matching blocks marked.</p>
        </article>

        <article class="card">
          <div class="frag frag-unicode" aria-hidden="true">
            <code>pri<mark>U+200B</mark>nt("Olá")</code>
            <span class="frag-status warn">⚠ 1 invisible character</span>
          </div>
          <h3>Spots pasted text</h3>
          <p>Flags zero-width spaces and other invisible characters that often come along when code is pasted from a chatbot.</p>
        </article>

        <article class="card">
          <div class="frag frag-claude" aria-hidden="true">
            <div class="crit"><span class="pts">1.5/2</span><span>Uses math.pi and the formula πr²</span></div>
            <div class="row"><span class="tag">Claude</span><span class="btn-mini">Reject</span><span class="btn-mini primary">Accept</span></div>
          </div>
          <h3>Grades with Claude, if you want</h3>
          <p>Optional. Claude drafts a rubric that you edit, then proposes points per criterion. Nothing counts until you accept, change or reject it.</p>
        </article>

        <article class="card">
          <div class="frag frag-files" aria-hidden="true">
            <div class="row">
              <span class="chip">ficha3.py</span>
              <span class="chip">notebook.ipynb</span>
              <span class="chip">turma.zip</span>
            </div>
            <span class="frag-status ok">✓ 4 students loaded</span>
          </div>
          <h3>Handles real files</h3>
          <p>Scripts and notebooks, Moodle folders or loose files, and submissions with syntax errors — they still open and can be graded.</p>
        </article>
      </div>
    </section>

    <!-- ==================== PRIVACY ==================== -->
    <section id="privacy" class="privacy">
      <div class="wrap privacy-inner">
        <div class="privacy-text">
          <p class="eyebrow">Privacy</p>
          <h2>The files stay on your computer</h2>
          <p>
            The page is a set of static files, and the Python that reads the submissions runs inside your
            browser tab — it's <a href="https://pyodide.org" target="_blank" rel="noopener">Pyodide</a>, Python
            compiled to WebAssembly. Nothing is uploaded, and closing the tab clears everything. Your
            browser's network panel will confirm it.
          </p>
          <p>
            The one exception is optional: grading with Claude, which you switch on with your own API key.
            Before anything is sent, names, student numbers and e-mail addresses are replaced, and you can
            preview exactly what goes out.
          </p>
        </div>
        <div class="anon">
          <figure>
            <figcaption>In the student's file</figcaption>
            <pre><template v-for="(line, i) in before" :key="i"><span v-for="(seg, k) in line" :key="k" :class="seg[1]">{{ seg[0] }}</span>{{ '\n' }}</template></pre>
          </figure>
          <span class="anon-arrow" aria-hidden="true">→</span>
          <figure>
            <figcaption>What Claude receives</figcaption>
            <pre><template v-for="(line, i) in after" :key="i"><span v-for="(seg, k) in line" :key="k" :class="seg[1]">{{ seg[0] }}</span>{{ '\n' }}</template></pre>
          </figure>
        </div>
      </div>
    </section>

    <!-- ==================== FAQ ==================== -->
    <section id="faq" class="faq wrap">
      <div class="faq-side">
        <p class="eyebrow">Questions</p>
        <h2>Before you start</h2>
        <p>Something else? The <a :href="repo" target="_blank" rel="noopener">source code is on GitHub</a>.</p>
      </div>
      <div class="faq-list">
        <details>
          <summary>Does it work with plain <code>.py</code> files?</summary>
          <p>
            Yes. A comment at the start of a line such as <code># Q1 (2 points)</code> or
            <code># Question 2</code> starts a question, and so does a block like
            <code>"""ID: 1 / Label: … / Grade: 5 points"""</code>. A file with no markers at all is graded as
            a single question.
          </p>
        </details>
        <details>
          <summary>My solution doesn't use “Q1” headers. What now?</summary>
          <p>
            Granymede also understands <code>ID:</code>, <code>Label:</code> and <code>Grade:</code> blocks
            (or <code>Pergunta</code>, <code>Enunciado</code>, <code>Cotação</code>). If nothing is found, the
            setup screen says so and shows what a header should look like.
          </p>
        </details>
        <details>
          <summary>Is running a student's code safe?</summary>
          <p>
            It runs in the browser's WebAssembly sandbox, in a worker of its own, so it can't reach your files,
            the grades or anything outside the tab. A run that doesn't finish is stopped after the time limit
            you choose.
          </p>
        </details>
        <details>
          <summary>How big a class can it handle?</summary>
          <p>
            Around a hundred submissions work comfortably on a normal laptop. The plagiarism check compares
            every pair, so it slows down with several hundred.
          </p>
        </details>
        <details>
          <summary>What exactly does Claude do, and what does it cost?</summary>
          <p>
            For each question it drafts a solution and a rubric, which you edit. Then it reads each anonymised
            submission and proposes points per criterion, with a short justification. Every grade waits for
            you, and only the ones you accept go into the CSV. It uses your Anthropic API key, so the cost goes
            to your account; the page shows an estimate as it runs.
          </p>
        </details>
        <details>
          <summary>Is anything stored?</summary>
          <p>
            The browser keeps Python and the page's code in its cache, so later visits load faster. Files and
            grades live only in the open tab. If you use Claude, your API key stays in that tab too, unless you
            ask the page to remember it on this computer.
          </p>
        </details>
      </div>
    </section>

    <!-- ==================== CLOSING ==================== -->
    <section class="closing">
      <div class="wrap closing-inner">
        <BrandMark class="closing-mark" />
        <h2>Try it with last week's assignment</h2>
        <p>No account and nothing to install: it runs in this tab.</p>
        <button class="start" @click="go">Start grading</button>
      </div>
    </section>

    <footer class="foot">
      <div class="wrap foot-inner">
        <span class="foot-brand"><BrandMark />Granymede</span>
        <span>
          Made by <a href="https://paulohcrocha.com" target="_blank" rel="noopener">Paulo Rocha</a> ·
          <a :href="repo" target="_blank" rel="noopener">Source code</a>
        </span>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.landing {
  --paper: #fbfaf7;
  --paper-2: #f2f0e9;
  --card: #ffffff;
  --ink: #1b1f26;
  --ink-2: #485060;
  --ink-3: #6e7584;
  --rule: #e4e0d6;
  --link: #1e4b8f;
  --navy: #12223a;
  --navy-2: #1c3658;
  --on-navy: #f1f4f9;
  --on-navy-2: #b6c3d6;
  --violet: #7c3aed;
  --violet-soft: #a78bfa;
  --serif: 'Source Serif 4 Variable', Georgia, 'Times New Roman', serif;
  --mono: ui-monospace, SFMono-Regular, Menlo, monospace;
  min-height: 100vh;
  background: var(--paper);
  color: var(--ink);
  font-size: 1.0625rem;
  line-height: 1.65;
}
:root[data-theme='dark'] .landing {
  --paper: #111317;
  --paper-2: #191c22;
  --card: #171a20;
  --ink: #ebe9e4;
  --ink-2: #b5b9c2;
  --ink-3: #8b919c;
  --rule: #2a2f38;
  --link: #93b8ee;
  --navy: #0c1626;
  --navy-2: #13253d;
}

.wrap { max-width: 1140px; margin-left: auto; margin-right: auto; padding-left: 24px; padding-right: 24px; }
a { color: var(--link); text-decoration: underline; text-underline-offset: 3px; text-decoration-thickness: 1px; }
a:hover { text-decoration-thickness: 2px; }
code {
  font-family: var(--mono);
  font-size: 0.86em;
  padding: 0.05em 0.3em;
  border-radius: 4px;
  background: var(--paper-2);
  border: 1px solid var(--rule);
}
h1, h2, h3 { font-family: var(--serif); font-weight: 600; letter-spacing: -0.012em; }
h2 { margin: 0; font-size: clamp(1.8rem, 3.2vw, 2.4rem); line-height: 1.15; color: var(--ink); }
h3 { margin: 0; color: var(--ink); }
.eyebrow {
  margin: 0 0 10px;
  font-size: 0.78rem;
  font-weight: 650;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--violet);
}
:root[data-theme='dark'] .eyebrow { color: var(--violet-soft); }

.start {
  padding: 0.8rem 1.5rem;
  border: none;
  border-radius: 9px;
  background: var(--ink);
  color: var(--paper);
  font-size: 1rem;
  font-weight: 650;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.12);
  transition: transform 0.12s, box-shadow 0.12s, opacity 0.12s;
}
.start:hover { transform: translateY(-1px); box-shadow: 0 6px 16px -6px rgba(0, 0, 0, 0.35); }
.start:active { transform: translateY(0); }

/* ---------------- hero ---------------- */
.hero {
  position: relative;
  overflow: hidden;
  color: var(--on-navy);
  /* Navy everywhere except the last 230px, where the screenshot hangs
     over the paper below. */
  background:
    linear-gradient(180deg, var(--navy) 0%, var(--navy-2) 100%) top / 100% calc(100% - 230px) no-repeat,
    var(--paper);
}
.orbits {
  position: absolute;
  inset: 0 0 auto 0;
  width: 100%;
  height: calc(100% - 230px);
  color: rgba(255, 255, 255, 0.09);
  pointer-events: none;
}
.orbits ellipse { stroke-width: 1.2; }
.orbits .moon { fill: var(--violet); }
.orbits .moon-2 { fill: #60a5fa; opacity: 0.8; }

.masthead { position: relative; border-bottom: 1px solid rgba(255, 255, 255, 0.08); }
.masthead-inner { display: flex; align-items: center; justify-content: space-between; gap: 1rem; height: 66px; }
.brand {
  display: inline-flex; align-items: center;
  font-family: var(--serif); font-size: 1.3rem; font-weight: 650;
  color: var(--on-navy); text-decoration: none;
}
.links { display: flex; align-items: center; gap: 1.5rem; font-size: 0.94rem; }
.links a { color: var(--on-navy-2); text-decoration: none; }
.links a:hover { color: #fff; }

.hero-copy { position: relative; padding-top: 76px; }
.kicker { margin: 0 0 16px; color: var(--on-navy-2); font-size: 0.98rem; }
h1 {
  margin: 0;
  max-width: 24ch;
  font-size: clamp(2.4rem, 5.4vw, 4rem);
  line-height: 1.06;
  color: #fff;
}
.marked { position: relative; white-space: nowrap; }
.pen {
  position: absolute;
  left: -1%;
  bottom: -0.1em;
  width: 102%;
  height: 0.3em;
  overflow: visible;
}
.pen path { fill: none; stroke: var(--violet-soft); stroke-width: 4; stroke-linecap: round; vector-effect: non-scaling-stroke; }
.lead { margin: 26px 0 0; max-width: 56ch; color: var(--on-navy-2); font-size: 1.16rem; }
.cta { display: flex; align-items: center; gap: 1.6rem; margin-top: 34px; }
.hero .start { background: #fff; color: var(--navy); }
.see { color: #fff; }
.runtime { display: flex; align-items: center; gap: 0.5rem; margin: 18px 0 0; color: var(--on-navy-2); font-size: 0.85rem; }
.runtime .dot { width: 7px; height: 7px; border-radius: 50%; background: #f5b83d; }
.runtime.ready .dot { background: #4ade80; }
.runtime.error .dot { background: #f87171; }

.stage { position: relative; margin-top: 60px; padding-bottom: 28px; }
.shot-main {
  display: block;
  width: 100%;
  height: auto;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 0 0 1px rgba(15, 23, 42, 0.08), 0 40px 80px -30px rgba(8, 15, 30, 0.55);
}
.shot-float {
  position: absolute;
  right: -18px;
  bottom: 0;
  width: 38%;
  height: auto;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 0 0 1px rgba(15, 23, 42, 0.1), 0 24px 48px -16px rgba(8, 15, 30, 0.45);
}
:root[data-theme='dark'] .shot-main,
:root[data-theme='dark'] .shot-float { filter: brightness(0.94); }

/* ---------------- sections ---------------- */
.how, .features, .faq { padding-top: 110px; }
.section-head { margin-bottom: 48px; max-width: 40ch; }

.steps { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 84px; }
.step { display: grid; grid-template-columns: minmax(0, 5fr) minmax(0, 7fr); gap: 56px; align-items: center; }
.step.flip { grid-template-columns: minmax(0, 7fr) minmax(0, 5fr); }
.step.flip .step-text { order: 2; }
.step-n {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  margin-bottom: 16px;
  border-radius: 50%;
  border: 1.5px solid var(--violet-soft);
  font-family: var(--serif);
  font-size: 1.2rem;
  font-weight: 600;
  color: var(--violet);
}
:root[data-theme='dark'] .step-n { color: var(--violet-soft); }
.step h3 { margin-bottom: 12px; font-size: 1.5rem; line-height: 1.25; }
.step p { margin: 0; color: var(--ink-2); }

.shot { margin: 0; }
.shot img {
  display: block;
  width: 100%;
  height: auto;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 0 0 1px var(--rule), 0 18px 40px -20px rgba(20, 20, 30, 0.3);
}
:root[data-theme='dark'] .shot img { filter: brightness(0.92); }
.shot figcaption { margin-top: 12px; color: var(--ink-3); font-size: 0.88rem; }

/* two consoles, slightly offset */
.stacked { display: grid; gap: 14px; }
.stacked img { width: 91%; }
.stacked img:last-child { justify-self: end; }
.verdict { margin: 14px 0 0; font-weight: 650; font-size: 0.92rem; color: #c2410c; }
:root[data-theme='dark'] .verdict { color: #fdba74; }

/* spreadsheet preview */
.sheet {
  overflow-x: auto;
  border-radius: 10px;
  background: var(--card);
  box-shadow: 0 0 0 1px var(--rule), 0 18px 40px -20px rgba(20, 20, 30, 0.3);
}
.sheet-bar { padding: 8px 14px; border-bottom: 1px solid var(--rule); background: var(--paper-2); }
.sheet-bar .file { font-family: var(--mono); font-size: 0.8rem; color: var(--ink-3); }
.sheet table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
.sheet th, .sheet td { padding: 8px 12px; border-bottom: 1px solid var(--rule); border-right: 1px solid var(--rule); text-align: left; white-space: nowrap; }
.sheet th { font-weight: 600; color: var(--ink-2); background: var(--paper); font-size: 0.76rem; }
.sheet td { color: var(--ink); }
.sheet td.num { font-family: var(--mono); text-align: right; font-variant-numeric: tabular-nums; }
.sheet td.note { color: var(--ink-3); font-style: italic; }
.sheet tr:last-child td { border-bottom: none; }
.sheet th:last-child, .sheet td:last-child { border-right: none; font-weight: 650; }

/* ---------------- feature cards ---------------- */
.cards { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 22px; }
.card {
  display: flex;
  flex-direction: column;
  padding: 22px;
  border-radius: 14px;
  background: var(--card);
  box-shadow: 0 0 0 1px var(--rule), 0 1px 2px rgba(20, 20, 30, 0.04);
  transition: transform 0.18s, box-shadow 0.18s;
}
.card:hover { transform: translateY(-2px); box-shadow: 0 0 0 1px var(--rule), 0 16px 32px -18px rgba(20, 20, 30, 0.3); }
.card h3 { margin: 18px 0 8px; font-size: 1.2rem; }
.card p { margin: 0; color: var(--ink-2); font-size: 0.97rem; line-height: 1.6; }

/* little pieces of the real interface */
.frag {
  min-height: 112px;
  padding: 14px;
  border-radius: 10px;
  background: var(--paper-2);
  border: 1px solid var(--rule);
  font-size: 0.82rem;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 10px;
}
.frag pre { margin: 0; font-family: var(--mono); font-size: 0.82rem; color: var(--ink); line-height: 1.5; }
.frag .kw { color: #cf222e; }
:root[data-theme='dark'] .frag .kw { color: #ff7b72; }
.frag-status { align-self: flex-start; padding: 2px 9px; border-radius: 999px; font-size: 0.75rem; font-weight: 600; background: #fde2e1; color: #a1262c; }
.frag-status.warn { background: #fdf0d2; color: #8a5300; }
:root[data-theme='dark'] .frag-status { background: rgba(229, 72, 77, 0.18); color: #ffb3b5; }
:root[data-theme='dark'] .frag-status.warn { background: rgba(245, 158, 11, 0.18); color: #fcd38d; }
.row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.row.small { color: var(--ink-3); font-size: 0.78rem; }
.muted { color: var(--ink-3); }
.pill { padding: 1px 8px; border-radius: 999px; font-size: 0.68rem; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase; }
.pill.high { background: #d1fae5; color: #065f46; }
:root[data-theme='dark'] .pill.high { background: rgba(34, 197, 94, 0.18); color: #86efac; }
.heat { display: grid; grid-template-columns: repeat(5, 16px); gap: 3px; }
.heat .cell { width: 16px; height: 16px; border-radius: 3px; background: transparent; }
.heat .cell.diag { background: var(--rule); }
.frag-heat { flex-direction: row; align-items: center; justify-content: flex-start; gap: 18px; }
.heat-note { color: var(--ink-2); font-size: 0.8rem; }
.heat-note strong { display: block; font-family: var(--serif); font-size: 1.4rem; color: #e5484d; line-height: 1.1; }
.frag-unicode code { align-self: flex-start; font-size: 0.86rem; padding: 4px 8px; background: var(--card); }
.frag-unicode mark {
  margin: 0 2px;
  padding: 0 4px;
  border-radius: 3px;
  background: #e5484d;
  color: #fff;
  font-size: 0.68rem;
  vertical-align: 1px;
}
.crit { display: flex; gap: 10px; align-items: baseline; padding: 8px 10px; border-radius: 7px; background: var(--card); border: 1px solid var(--rule); }
.crit .pts { font-family: var(--mono); font-weight: 700; color: #b45309; }
.tag { padding: 1px 8px; border-radius: 999px; background: var(--violet); color: #fff; font-size: 0.68rem; font-weight: 700; margin-right: auto; }
.btn-mini { padding: 2px 9px; border-radius: 6px; border: 1px solid var(--rule); background: var(--card); font-size: 0.74rem; color: var(--ink-2); }
.btn-mini.primary { background: #2563eb; border-color: #2563eb; color: #fff; }
.frag-files .row { gap: 6px; }
.frag-status.ok { background: #d1fae5; color: #065f46; }
:root[data-theme='dark'] .frag-status.ok { background: rgba(34, 197, 94, 0.18); color: #86efac; }
.chip { padding: 3px 9px; border-radius: 6px; background: var(--card); border: 1px solid var(--rule); font-family: var(--mono); font-size: 0.74rem; color: var(--ink); }

/* ---------------- privacy band ---------------- */
.privacy {
  margin-top: 120px;
  padding: 96px 0;
  background: linear-gradient(180deg, var(--navy), var(--navy-2));
  color: var(--on-navy-2);
}
.privacy-inner { display: grid; grid-template-columns: minmax(0, 5fr) minmax(0, 7fr); gap: 56px; align-items: center; }
.privacy h2 { color: #fff; margin-bottom: 18px; }
.privacy .eyebrow { color: var(--violet-soft); }
.privacy-text p:not(.eyebrow) { margin: 0 0 14px; }
.privacy a { color: #fff; }
.anon { display: grid; grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr); gap: 12px; align-items: end; }
.anon-arrow { align-self: center; }
.anon figure { margin: 0; }
.anon figcaption { margin-bottom: 8px; font-size: 0.8rem; color: var(--on-navy-2); }
.anon pre {
  margin: 0;
  padding: 14px 16px;
  overflow-x: auto;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  font-family: var(--mono);
  font-size: 0.8rem;
  line-height: 1.65;
  color: #dde4ee;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.anon .pii { background: rgba(229, 72, 77, 0.28); color: #ffd1d2; border-radius: 3px; padding: 0 2px; }
.anon .ph { background: rgba(167, 139, 250, 0.28); color: #e6dcff; border-radius: 3px; padding: 0 2px; }
.anon-arrow { font-size: 1.4rem; color: var(--violet-soft); }

/* ---------------- faq ---------------- */
.faq { display: grid; grid-template-columns: minmax(0, 4fr) minmax(0, 8fr); gap: 56px; }
.faq-side p:not(.eyebrow) { margin: 16px 0 0; color: var(--ink-2); }
.faq-list details { border-bottom: 1px solid var(--rule); }
.faq-list details:first-of-type { border-top: 1px solid var(--rule); }
.faq summary {
  cursor: pointer;
  list-style: none;
  position: relative;
  padding: 18px 32px 18px 0;
  font-weight: 600;
  color: var(--ink);
}
.faq summary::-webkit-details-marker { display: none; }
.faq summary::after {
  content: '+';
  position: absolute;
  right: 6px;
  top: 15px;
  font-size: 1.3rem;
  font-weight: 400;
  color: var(--violet);
}
.faq details[open] summary::after { content: '–'; }
.faq details p { margin: 0 0 20px; color: var(--ink-2); }

/* ---------------- closing + footer ---------------- */
.closing { margin-top: 120px; padding: 88px 0; border-top: 1px solid var(--rule); background: var(--paper-2); text-align: center; }
.closing-inner { display: flex; flex-direction: column; align-items: center; }
.closing-mark { width: 64px !important; height: 64px !important; margin: 0 0 18px !important; }
.closing h2 { margin-bottom: 10px; }
.closing p { margin: 0 0 26px; color: var(--ink-2); }
.foot { border-top: 1px solid var(--rule); color: var(--ink-3); font-size: 0.9rem; }
.foot-inner { display: flex; justify-content: space-between; align-items: center; gap: 1rem; flex-wrap: wrap; padding-top: 22px; padding-bottom: 22px; }
.foot-brand { display: inline-flex; align-items: center; font-family: var(--serif); font-weight: 600; color: var(--ink-2); }
.foot a { color: var(--ink-2); }

/* ---------------- small screens ---------------- */
@media (max-width: 960px) {
  .cards { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .step, .step.flip, .privacy-inner, .faq { grid-template-columns: minmax(0, 1fr); gap: 28px; }
  .step.flip .step-text { order: 0; }
  .links a { display: none; }
}
@media (max-width: 640px) {
  .cards { grid-template-columns: minmax(0, 1fr); }
  .hero-copy { padding-top: 48px; }
  .cta { flex-direction: column; align-items: flex-start; gap: 1rem; }
  .marked { white-space: normal; }
  .wide-only { display: none; }
  .orbits circle { display: none; }
  .pen { display: none; }
  .shot-float { position: static; width: 85%; margin-top: -40px; margin-left: 12px; }
  .anon { grid-template-columns: minmax(0, 1fr); }
  .anon-arrow { transform: rotate(90deg); justify-self: center; }
  .how, .features, .faq { padding-top: 80px; }
}
</style>
