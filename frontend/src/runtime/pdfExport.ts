/**
 * Client-side PDF reports for plagiarism findings.
 *
 * Mirrors the structure of the old Flask reportlab report (title, document
 * info, executive summary, severity classification, per-pair detailed
 * analysis) but built with jsPDF + jspdf-autotable so it runs entirely in
 * the browser. Produces an A4 file the user downloads via Blob URL.
 *
 * Two entry points:
 * - `exportPairPdf(pair)`         — single pair report
 * - `exportFullPdf(pairs)`        — multi-pair report
 */

import { jsPDF } from 'jspdf'
import autoTable from 'jspdf-autotable'
import type {
  PlagiarismAnalyzeResponse,
  PlagiarismCompareResponse,
  SuspiciousPair,
} from '../api/client'
import { plagiarismCompare } from '../api/client'

const PAGE_W = 210 // A4 mm
const MARGIN = 15

interface BuildContext {
  doc: jsPDF
  y: number
}

function ensureSpace(ctx: BuildContext, needed: number) {
  if (ctx.y + needed > 280) {
    ctx.doc.addPage()
    ctx.y = MARGIN
  }
}

function header(ctx: BuildContext, text: string, level: 1 | 2 | 3 = 2) {
  ensureSpace(ctx, level === 1 ? 20 : 14)
  const sizes = { 1: 18, 2: 13, 3: 11 } as const
  ctx.doc.setFont('helvetica', 'bold')
  ctx.doc.setFontSize(sizes[level])
  ctx.doc.setTextColor(level === 1 ? '#1e3a5f' : '#2c5282')
  ctx.doc.text(text, MARGIN, ctx.y)
  ctx.y += level === 1 ? 9 : level === 2 ? 7 : 5
  ctx.doc.setTextColor('#1f2937')
  ctx.doc.setFont('helvetica', 'normal')
  ctx.doc.setFontSize(10)
}

function paragraph(ctx: BuildContext, text: string, opts: { bold?: boolean } = {}) {
  ctx.doc.setFont('helvetica', opts.bold ? 'bold' : 'normal')
  ctx.doc.setFontSize(10)
  const wrapped = ctx.doc.splitTextToSize(text, PAGE_W - MARGIN * 2) as string[]
  for (const line of wrapped) {
    ensureSpace(ctx, 5)
    ctx.doc.text(line, MARGIN, ctx.y)
    ctx.y += 5
  }
  ctx.y += 1
}

function infoTable(ctx: BuildContext, rows: [string, string][]) {
  autoTable(ctx.doc, {
    startY: ctx.y,
    body: rows,
    theme: 'grid',
    styles: { fontSize: 9, cellPadding: 2 },
    columnStyles: { 0: { fontStyle: 'bold', fillColor: [240, 244, 248], cellWidth: 60 } },
    margin: { left: MARGIN, right: MARGIN },
  })
  ctx.y = (ctx.doc as unknown as { lastAutoTable: { finalY: number } }).lastAutoTable.finalY + 5
}

function severityTable(ctx: BuildContext, high: number, medium: number) {
  autoTable(ctx.doc, {
    startY: ctx.y,
    head: [['Similarity Range', 'Classification', 'Recommended Action', 'Count']],
    body: [
      ['95% – 100%', 'CRITICAL', 'Immediate investigation required', String(high)],
      ['85% – 94%', 'HIGH', 'Formal inquiry recommended', String(medium)],
      ['70% – 84%', 'MODERATE', 'Review recommended', '— (not in report)'],
    ],
    theme: 'grid',
    headStyles: { fillColor: [30, 58, 95], textColor: 255, fontStyle: 'bold' },
    styles: { fontSize: 9, cellPadding: 3, halign: 'center' },
    columnStyles: { 1: { fontStyle: 'bold' } },
    didParseCell: (data) => {
      if (data.section !== 'body') return
      const rowIdx = data.row.index
      if (rowIdx === 0) data.cell.styles.fillColor = [254, 226, 226]
      else if (rowIdx === 1) data.cell.styles.fillColor = [254, 243, 199]
      else if (rowIdx === 2) data.cell.styles.fillColor = [229, 231, 235]
    },
    margin: { left: MARGIN, right: MARGIN },
  })
  ctx.y = (ctx.doc as unknown as { lastAutoTable: { finalY: number } }).lastAutoTable.finalY + 6
}

function questionTable(ctx: BuildContext, q: PlagiarismCompareResponse['questions']) {
  const rows = q.map((qq) => {
    const sim = qq.similarity * 100
    const label = sim >= 85 ? '⚠ SUSPICIOUS' : sim >= 70 ? '⚡ Notable' : '✓ Different'
    return [qq.question_id, `${sim.toFixed(1)}%`, label]
  })
  autoTable(ctx.doc, {
    startY: ctx.y,
    head: [['Question', 'Similarity', 'Assessment']],
    body: rows,
    theme: 'grid',
    headStyles: { fillColor: [30, 58, 95], textColor: 255, fontStyle: 'bold' },
    styles: { fontSize: 9, cellPadding: 2.5, halign: 'center' },
    didParseCell: (data) => {
      if (data.section !== 'body') return
      const rowIdx = data.row.index
      const sim = parseFloat(rows[rowIdx][1]) / 100
      const fill: [number, number, number] = sim >= 0.85
        ? [254, 226, 226]
        : sim >= 0.70
          ? [254, 243, 199]
          : [209, 250, 229]
      data.cell.styles.fillColor = fill
    },
    margin: { left: MARGIN, right: MARGIN },
  })
  ctx.y = (ctx.doc as unknown as { lastAutoTable: { finalY: number } }).lastAutoTable.finalY + 5
}

function codeBlock(ctx: BuildContext, title: string, code: string) {
  ensureSpace(ctx, 12)
  ctx.doc.setFont('helvetica', 'bold')
  ctx.doc.setFontSize(9.5)
  ctx.doc.setTextColor('#1f2937')
  ctx.doc.text(title, MARGIN, ctx.y)
  ctx.y += 4
  ctx.doc.setFont('courier', 'normal')
  ctx.doc.setFontSize(7.5)
  const lines = (code || '(no code)').split('\n')
  const wrapped: string[] = []
  for (const line of lines) {
    const parts = ctx.doc.splitTextToSize(line || ' ', PAGE_W - MARGIN * 2 - 6) as string[]
    wrapped.push(...parts)
  }
  // Background panel
  const lineHeight = 3.4
  const blockH = wrapped.length * lineHeight + 4
  ensureSpace(ctx, blockH)
  ctx.doc.setFillColor('#f9fafb')
  ctx.doc.rect(MARGIN, ctx.y - 2, PAGE_W - MARGIN * 2, blockH, 'F')
  ctx.doc.setTextColor('#111827')
  for (const line of wrapped) {
    ctx.doc.text(line, MARGIN + 2, ctx.y + 1.5)
    ctx.y += lineHeight
  }
  ctx.y += 4
  ctx.doc.setFont('helvetica', 'normal')
  ctx.doc.setFontSize(10)
  ctx.doc.setTextColor('#1f2937')
}

function preamble(
  ctx: BuildContext,
  totalStudents: number,
  threshold: number,
  pairCount: number,
  highRisk: number,
  mediumRisk: number,
) {
  // Title
  ctx.doc.setFont('helvetica', 'bold')
  ctx.doc.setFontSize(20)
  ctx.doc.setTextColor('#1e3a5f')
  ctx.doc.text('OFFICIAL PLAGIARISM DETECTION REPORT', PAGE_W / 2, ctx.y, { align: 'center' })
  ctx.y += 12

  // Document info
  const now = new Date()
  const dateStr = now.toLocaleDateString(undefined, {
    year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
  infoTable(ctx, [
    ['Document Type', 'Academic Integrity Investigation'],
    ['Generated by', 'Ganymede (browser-only)'],
    ['Report Date', dateStr],
    ['Total Students', String(totalStudents)],
    ['Detection Threshold', `${(threshold * 100).toFixed(0)}%`],
    ['Analysis Method', 'Hybrid (TF-IDF 40% + AST 30% + Token 30%)'],
  ])

  header(ctx, 'EXECUTIVE SUMMARY')
  const total = (totalStudents * (totalStudents - 1)) / 2
  const summary = pairCount === 1
    ? `This report investigates one pair of students from a class of ${totalStudents}. ` +
      `The detection algorithm combines TF-IDF cosine similarity (40%), AST structural ` +
      `analysis (30%), and token Jaccard similarity (30%). The pair's overall similarity ` +
      `is documented in the case section that follows.`
    : `This report covers ${pairCount} suspicious pair(s) identified across ` +
      `${totalStudents} submissions (${total.toLocaleString()} pairwise comparisons). ` +
      `${highRisk} case(s) reach the CRITICAL threshold (≥95%), and ${mediumRisk} fall in the ` +
      `HIGH range (85-94%). The detection algorithm combines TF-IDF cosine similarity ` +
      `(40%), AST structural analysis (30%), and token Jaccard similarity (30%) — it ` +
      `flags both verbatim copying and structurally-identical code with renamed variables.`
  paragraph(ctx, summary)

  header(ctx, 'SEVERITY CLASSIFICATION')
  severityTable(ctx, highRisk, mediumRisk)
}

async function appendCase(
  ctx: BuildContext,
  idx: number,
  pair: SuspiciousPair,
  comparison: PlagiarismCompareResponse,
) {
  ctx.doc.addPage()
  ctx.y = MARGIN
  const severity = pair.similarity >= 0.95 ? 'CRITICAL' : 'HIGH'
  header(ctx, `CASE #${idx} — ${severity} (${(pair.similarity * 100).toFixed(1)}%)`, 2)
  infoTable(ctx, [
    ['Student A', `${pair.student1_name} (id: ${pair.student1_id})`],
    ['Student B', `${pair.student2_name} (id: ${pair.student2_id})`],
    ['Overall similarity', `${(comparison.overall_similarity * 100).toFixed(1)}%`],
  ])

  paragraph(ctx, 'Similarity by Question:', { bold: true })
  questionTable(ctx, comparison.questions)

  header(ctx, 'DETAILED CODE COMPARISON', 3)
  // Sort questions by similarity (highest first)
  const sorted = [...comparison.questions].sort((a, b) => b.similarity - a.similarity)
  for (const q of sorted) {
    if (!q.code1 && !q.code2) continue
    const blockTags = q.matching_blocks.length
      ? ` — ${q.matching_blocks.length} matching block(s)`
      : ''
    header(ctx, `${q.question_id} · ${(q.similarity * 100).toFixed(1)}%${blockTags}`, 3)
    codeBlock(ctx, comparison.student1_name, q.code1)
    codeBlock(ctx, comparison.student2_name, q.code2)
  }
}

async function buildReport(
  pairs: SuspiciousPair[],
  analyze: PlagiarismAnalyzeResponse,
  filename: string,
) {
  const doc = new jsPDF({ unit: 'mm', format: 'a4' })
  const ctx: BuildContext = { doc, y: MARGIN }

  const high = pairs.filter((p) => p.similarity >= 0.95).length
  const medium = pairs.length - high
  preamble(ctx, analyze.student_ids.length, analyze.threshold, pairs.length, high, medium)

  // Fetch the comparisons sequentially to avoid hammering the runtime in
  // parallel (Pyodide is single-threaded anyway).
  for (let i = 0; i < pairs.length; i++) {
    const pair = pairs[i]
    const comparison = await plagiarismCompare(pair.student1_id, pair.student2_id)
    await appendCase(ctx, i + 1, pair, comparison)
  }

  doc.save(filename)
}

function safeFilename(s: string): string {
  return s.replace(/[^a-zA-Z0-9._-]+/g, '_').slice(0, 40)
}

export async function exportPairPdf(
  pair: SuspiciousPair,
  analyze: PlagiarismAnalyzeResponse,
): Promise<void> {
  const date = new Date().toISOString().slice(0, 10).replace(/-/g, '')
  const name = `plagiarism_${safeFilename(pair.student1_name)}_vs_${safeFilename(pair.student2_name)}_${date}.pdf`
  await buildReport([pair], analyze, name)
}

export async function exportFullPdf(
  pairs: SuspiciousPair[],
  analyze: PlagiarismAnalyzeResponse,
): Promise<void> {
  const date = new Date().toISOString().slice(0, 10).replace(/-/g, '')
  const name = `plagiarism_report_${date}.pdf`
  await buildReport(pairs, analyze, name)
}
