<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import '@fontsource-variable/source-serif-4'
import { runtimeStage } from '../runtime/pyodide'
import BrandMark from '../components/BrandMark.vue'
import ThemeToggle from '../components/ThemeToggle.vue'
import gradingShot from '../assets/landing/grading.jpg'
import setupShot from '../assets/landing/setup.jpg'
import consoleShot from '../assets/landing/console.jpg'

const router = useRouter()

const runtimeNote = computed(() => {
  switch (runtimeStage.value) {
    case 'ready':
      return 'Python is loaded. The grading screens open straight away.'
    case 'error':
      return 'Python failed to load. Reload the page to try again.'
    default:
      return 'Python is loading in the background while you read.'
  }
})

function go() {
  router.push('/setup')
}

// Real input and output of anonymizer.py, shown in the privacy section.
const studentFile = `# Nome: Ana Ribeiro
# Número: 2023101
# ana.ribeiro@alunos.exemplo.pt
import math

def area(r):
    return math.pi * r ** 2`

const sentFile = `# Nome: <REDACTED>
# Número: <REDACTED>
# <EMAIL>
import math

def area(r):
    return math.pi * r ** 2`
</script>

<template>
  <div class="landing">
    <header class="masthead">
      <div class="wrap masthead-inner">
        <RouterLink to="/" class="brand"><BrandMark />Granymede</RouterLink>
        <nav class="links" aria-label="On this page">
          <a href="#how">How it works</a>
          <a href="#privacy">Privacy</a>
          <a href="#faq">Questions</a>
          <a href="https://github.com/PauloHCRocha/GradingToolJupyter2000" target="_blank" rel="noopener">Source</a>
          <ThemeToggle />
        </nav>
      </div>
    </header>

    <main>
      <section class="intro wrap">
        <p class="kicker">A grading tool for Python and Jupyter assignments</p>
        <h1>Every answer next to your solution, one question at a time.</h1>
        <p class="lead">
          Load your solution and the students' files. Granymede finds the questions, puts each
          answer beside yours, runs the code when you need it and keeps the grades. It all
          happens in your browser, so the files never leave your computer.
        </p>
        <div class="cta">
          <button class="start" @click="go">Start grading</button>
          <a class="quiet" href="#how">How it works</a>
        </div>
        <p class="runtime" :class="runtimeStage">{{ runtimeNote }}</p>

        <figure class="shot hero-shot">
          <img :src="gradingShot" width="2200" height="1034"
               alt="The grading screen: question 1 for the student Bruno Costa, graded 1.5 out of 2, with the solution and his answer side by side." />
          <figcaption>
            Grading Bruno's answer to question 1. Your solution is on the left and his is on the right; the
            grade and the comment go above.
          </figcaption>
        </figure>
      </section>

      <section id="how" class="how wrap">
        <h2>How a grading session goes</h2>
        <ol class="steps">
          <li class="step">
            <div class="step-text">
              <span class="step-n">Step 1</span>
              <h3>Drop in your solution and the students' work</h3>
              <p>
                Your solution file, <code>.py</code> or <code>.ipynb</code>, tells Granymede where each question
                starts and what it is worth. A comment such as <code># Q1 (2 points)</code> is enough, or a
                markdown heading in a notebook. The students' files can come straight from the zip that Moodle
                gives you, or one by one.
              </p>
            </div>
            <figure class="shot">
              <img :src="setupShot" width="1200" height="813" loading="lazy"
                   alt="The setup screen with a solution file of three questions and a zip of four students loaded." />
              <figcaption>Three questions found in the solution, four students in the zip.</figcaption>
            </figure>
          </li>
          <li class="step wide">
            <div class="step-text">
              <span class="step-n">Step 2</span>
              <h3>Read, run, grade</h3>
              <p>
                Move through the class with the arrow keys. For each question you see the statement, your
                solution and the student's answer. When you are not sure the code works, run it: if it asks for
                input you type it, as in a terminal, and you can run your solution with the same input to
                compare the two.
              </p>
            </div>
            <figure class="shot">
              <img :src="consoleShot" width="2200" height="373" loading="lazy"
                   alt="Two consoles side by side. With the input 21, the student's program prints 2121 and the solution prints 42." />
              <figcaption>Bruno forgot <code>int()</code>: given 21, his program prints 2121 and the solution prints 42.</figcaption>
            </figure>
          </li>
          <li class="step text-only">
            <div class="step-text">
              <span class="step-n">Step 3</span>
              <h3>Export the grades</h3>
              <p>
                One CSV file with a row per student, a column per question and your comments, ready to import
                into Moodle or open in a spreadsheet.
              </p>
            </div>
          </li>
        </ol>
      </section>

      <section class="more wrap">
        <h2>What else it does</h2>
        <dl class="spec">
          <div>
            <dt>Runs code safely</dt>
            <dd>
              In a separate Python inside the page, with a time limit, so an endless loop can't freeze the
              tab. You edit a copy; the submission itself never changes.
            </dd>
          </div>
          <div>
            <dt>Suggests a grade</dt>
            <dd>A simple comparison with your solution (structure, imports, output) proposes a grade. You decide.</dd>
          </div>
          <div>
            <dt>Looks for copied work</dt>
            <dd>Compares every pair of submissions and groups the similar ones, with a heatmap you can click through.</dd>
          </div>
          <div>
            <dt>Spots pasted text</dt>
            <dd>Flags the invisible Unicode characters that often come along when code is pasted from a chatbot.</dd>
          </div>
          <div>
            <dt>Grades with Claude, if you want</dt>
            <dd>
              Optional. Claude drafts a rubric that you edit, then proposes a grade per criterion. Nothing counts
              until you accept, change or reject it.
            </dd>
          </div>
          <div>
            <dt>Handles real files</dt>
            <dd>Notebooks and plain scripts, Moodle folders or loose files, and files with syntax errors.</dd>
          </div>
        </dl>
      </section>

      <section id="privacy" class="privacy wrap">
        <h2>Where the files go</h2>
        <div class="privacy-text">
          <p>
            Nowhere. The page is a set of static files, and the Python that reads the submissions runs inside
            your browser tab: it is <a href="https://pyodide.org" target="_blank" rel="noopener">Pyodide</a>,
            Python compiled to WebAssembly. Nothing is uploaded, and closing the tab clears everything. Your
            browser's network panel will show it.
          </p>
          <p>
            The one exception is optional: grading with Claude, which you switch on with your own API key.
            Before anything is sent, names, student numbers and e-mail addresses are replaced, and you can
            preview exactly what goes out. This is what happens to the top of a file:
          </p>
        </div>
        <div class="anon">
          <figure>
            <figcaption>In the student's file</figcaption>
            <pre>{{ studentFile }}</pre>
          </figure>
          <figure>
            <figcaption>What Claude receives</figcaption>
            <pre>{{ sentFile }}</pre>
          </figure>
        </div>
      </section>

      <section id="faq" class="faq wrap">
        <h2>Questions</h2>
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
            (or <code>Pergunta</code>, <code>Enunciado</code>, <code>Cotação</code>). If nothing is found, it
            tells you so on the setup screen and shows what a header should look like.
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
            For each question it drafts a solution and a rubric, which you edit. Then it reads each
            anonymised submission and proposes points per criterion, with a short justification. Every grade
            waits for you, and only the ones you accept go into the CSV. It uses your Anthropic API key, so the
            cost goes to your account; the page shows an estimate as it runs.
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
      </section>

      <section class="closing wrap">
        <p>Ready to try it with your own class?</p>
        <button class="start" @click="go">Start grading</button>
      </section>
    </main>

    <footer class="foot">
      <div class="wrap foot-inner">
        <span><BrandMark />Granymede</span>
        <span>
          Made by <a href="https://paulohcrocha.com" target="_blank" rel="noopener">Paulo Rocha</a> ·
          <a href="https://github.com/PauloHCRocha/GradingToolJupyter2000" target="_blank" rel="noopener">Source code</a>
        </span>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.landing {
  --paper: #fbfaf7;
  --paper-2: #f3f1ea;
  --ink: #1c1f24;
  --ink-2: #4b5260;
  --ink-3: #6f7685;
  --rule: #e4e0d6;
  --link: #1e4b8f;
  --serif: 'Source Serif 4 Variable', Georgia, 'Times New Roman', serif;
  min-height: 100vh;
  background: var(--paper);
  color: var(--ink);
  font-size: 1.0625rem;
  line-height: 1.65;
}
:root[data-theme='dark'] .landing {
  --paper: #121417;
  --paper-2: #1a1d22;
  --ink: #e9e7e2;
  --ink-2: #b4b8c0;
  --ink-3: #8a909b;
  --rule: #2b3038;
  --link: #8fb4ec;
}

.wrap { max-width: 1120px; margin-left: auto; margin-right: auto; padding: 0 24px; }
a { color: var(--link); text-decoration: underline; text-underline-offset: 3px; text-decoration-thickness: 1px; }
a:hover { text-decoration-thickness: 2px; }
code {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.86em;
  padding: 0.05em 0.3em;
  border-radius: 4px;
  background: var(--paper-2);
  border: 1px solid var(--rule);
}
h1, h2, h3 { font-family: var(--serif); color: var(--ink); font-weight: 600; letter-spacing: -0.012em; }

/* masthead */
.masthead { border-bottom: 1px solid var(--rule); }
.masthead-inner { display: flex; align-items: center; justify-content: space-between; gap: 1rem; height: 64px; }
.brand {
  display: inline-flex; align-items: center;
  font-family: var(--serif); font-size: 1.3rem; font-weight: 650;
  color: var(--ink); text-decoration: none;
}
.links { display: flex; align-items: center; gap: 1.4rem; font-size: 0.95rem; }
.links a { color: var(--ink-2); text-decoration: none; }
.links a:hover { color: var(--ink); text-decoration: underline; }

/* intro */
.intro { padding-top: 72px; }
.kicker { margin: 0 0 14px; color: var(--ink-3); font-size: 0.95rem; }
h1 { margin: 0; max-width: 21ch; font-size: clamp(2.3rem, 5vw, 3.6rem); line-height: 1.08; }
.lead { margin: 22px 0 0; max-width: 58ch; color: var(--ink-2); font-size: 1.15rem; }
.cta { display: flex; align-items: center; gap: 1.5rem; margin-top: 30px; }
.start {
  padding: 0.75rem 1.4rem;
  border: none;
  border-radius: 8px;
  background: var(--ink);
  color: var(--paper);
  font-size: 1rem;
  font-weight: 600;
  transition: transform 0.12s, opacity 0.12s;
}
.start:hover { opacity: 0.88; }
.start:active { transform: translateY(1px); }
.quiet { color: var(--ink-2); }
.runtime { margin: 14px 0 0; color: var(--ink-3); font-size: 0.85rem; }
.runtime.error { color: #b42318; }

/* screenshots */
.shot { margin: 0; }
.shot img {
  display: block;
  width: 100%;
  height: auto;
  border: 1px solid var(--rule);
  border-radius: 10px;
  box-shadow: 0 1px 2px rgba(20, 20, 20, 0.04), 0 12px 32px -12px rgba(20, 20, 20, 0.18);
  background: #fff;
}
:root[data-theme='dark'] .shot img { filter: brightness(0.92); box-shadow: none; }
.shot figcaption { margin-top: 10px; color: var(--ink-3); font-size: 0.88rem; }
.hero-shot { margin-top: 56px; }

/* sections */
section + section { margin-top: 96px; }
h2 { margin: 0 0 28px; padding-top: 28px; border-top: 1px solid var(--rule); font-size: 1.85rem; line-height: 1.2; }

/* steps */
.steps { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 56px; }
.step { display: grid; grid-template-columns: minmax(0, 5fr) minmax(0, 7fr); gap: 40px; align-items: start; }
.step.text-only { grid-template-columns: minmax(0, 5fr); }
/* A very wide screenshot reads better under the text, at full width. */
.step.wide { grid-template-columns: minmax(0, 1fr); gap: 20px; }
.step.wide .step-text { max-width: 62ch; }
.step-n {
  display: inline-block;
  margin-bottom: 6px;
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ink-3);
}
.step h3 { margin: 0 0 10px; font-size: 1.35rem; line-height: 1.25; }
.step p { margin: 0; color: var(--ink-2); }

/* spec list */
.spec { margin: 0; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 48px; }
.spec > div { padding: 18px 0; border-bottom: 1px solid var(--rule); }
.spec dt { font-weight: 650; color: var(--ink); }
.spec dd { margin: 4px 0 0; color: var(--ink-2); }

/* privacy */
.privacy-text { max-width: 68ch; }
.privacy-text p { margin: 0 0 14px; color: var(--ink-2); }
.anon { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; margin-top: 24px; }
.anon figure { margin: 0; }
.anon figcaption { margin-bottom: 8px; font-size: 0.85rem; color: var(--ink-3); }
.anon pre {
  margin: 0;
  padding: 14px 16px;
  overflow-x: auto;
  border: 1px solid var(--rule);
  border-radius: 8px;
  background: var(--paper-2);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.85rem;
  line-height: 1.6;
  color: var(--ink);
}

/* faq */
.faq details { border-bottom: 1px solid var(--rule); }
.faq details:first-of-type { border-top: 1px solid var(--rule); }
.faq summary {
  cursor: pointer;
  list-style: none;
  padding: 16px 28px 16px 0;
  position: relative;
  font-weight: 600;
  color: var(--ink);
}
.faq summary::-webkit-details-marker { display: none; }
.faq summary::after {
  content: '+';
  position: absolute;
  right: 4px;
  top: 14px;
  color: var(--ink-3);
  font-weight: 400;
  font-size: 1.2rem;
}
.faq details[open] summary::after { content: '–'; }
.faq details p { margin: 0 0 18px; max-width: 68ch; color: var(--ink-2); }
.faq h2 { margin-bottom: 14px; }

/* closing + footer */
.closing { display: flex; align-items: center; gap: 1.5rem; flex-wrap: wrap; padding-top: 8px; padding-bottom: 96px; }
.closing p { margin: 0; font-family: var(--serif); font-size: 1.5rem; color: var(--ink); }
.foot { border-top: 1px solid var(--rule); color: var(--ink-3); font-size: 0.9rem; }
.foot-inner { display: flex; justify-content: space-between; align-items: center; gap: 1rem; flex-wrap: wrap; padding-top: 22px; padding-bottom: 22px; }
.foot-inner > span:first-child { display: inline-flex; align-items: center; font-family: var(--serif); font-weight: 600; color: var(--ink-2); }
.foot a { color: var(--ink-2); }

@media (max-width: 860px) {
  .step { grid-template-columns: minmax(0, 1fr); gap: 18px; }
  .spec, .anon { grid-template-columns: minmax(0, 1fr); }
  .links a:not(:last-of-type) { display: none; }
}
@media (max-width: 520px) {
  .intro { padding-top: 44px; }
  .cta { flex-direction: column; align-items: flex-start; gap: 0.9rem; }
  section + section { margin-top: 72px; }
}
</style>
