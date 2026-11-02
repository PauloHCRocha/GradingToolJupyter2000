<script setup lang="ts">
/**
 * Drop zone for one file: drag a file onto it, or click (or press
 * Enter/Space on it) to pick one. The parent handles the file as soon as
 * it arrives — there is no separate upload button.
 */
import { ref } from 'vue'

defineProps<{
  /** For the file picker's filter, e.g. ".py,.ipynb". */
  accept: string
  title: string
  detail: string
  status: 'idle' | 'busy' | 'done' | 'error' | 'pending'
  /** A file is being dragged somewhere over the page. */
  highlight?: boolean
  /** Let the file picker select several files. */
  multiple?: boolean
  /** Text of the button that clears this zone; no button when unset. */
  removeLabel?: string
}>()
const emit = defineEmits<{ files: [files: File[]]; remove: [] }>()

const over = ref(false)
// dragenter/dragleave fire for every child element crossed; count them so
// the highlight doesn't flicker.
let depth = 0

function onEnter() {
  depth++
  over.value = true
}
function onLeave() {
  depth = Math.max(0, depth - 1)
  if (!depth) over.value = false
}
function onDrop(e: DragEvent) {
  depth = 0
  over.value = false
  const files = Array.from(e.dataTransfer?.files ?? [])
  if (files.length) emit('files', files)
}
function onPick(e: Event) {
  const input = e.target as HTMLInputElement
  const files = Array.from(input.files ?? [])
  // Reset so picking the same file again still triggers a change.
  input.value = ''
  if (files.length) emit('files', files)
}
</script>

<template>
  <label
    class="drop"
    :class="[status, { over, highlight }]"
    @dragenter.prevent="onEnter"
    @dragover.prevent
    @dragleave="onLeave"
    @drop.prevent.stop="onDrop"
  >
    <input type="file" class="picker" :accept="accept" :multiple="multiple" :disabled="status === 'busy'"
           :aria-label="`Choose a file — ${title}`" @change="onPick" />
    <span class="icon" aria-hidden="true">
      <span v-if="status === 'busy'" class="spin" />
      <template v-else-if="status === 'done'">✓</template>
      <template v-else-if="status === 'error'">!</template>
      <template v-else-if="status === 'pending'">…</template>
      <svg v-else viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2"
           stroke-linecap="round" stroke-linejoin="round"><path d="M12 16V4M6 10l6-6 6 6M4 20h16" /></svg>
    </span>
    <span class="text">
      <strong class="title">{{ title }}</strong>
      <span class="detail">{{ detail }}</span>
    </span>
    <span v-if="over" class="drop-here">Drop to load</span>
    <button v-else-if="removeLabel && status !== 'busy'" type="button" class="remove"
            @click.prevent.stop="emit('remove')">
      {{ removeLabel }}
    </button>
  </label>
</template>

<style scoped>
.drop {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.85rem;
  padding: 1rem 1.1rem;
  border: 2px dashed var(--border-strong);
  border-radius: 10px;
  background: var(--bg-soft);
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}
.drop:hover,
.drop.highlight { border-color: var(--accent); background: var(--accent-soft); }
.drop.over { border-style: solid; border-color: var(--accent); background: var(--accent-soft); }
.drop:focus-within { outline: 2px solid var(--accent); outline-offset: 2px; }
.drop.done { border-style: solid; border-color: var(--success); background: var(--success-soft); }
.drop.error { border-style: solid; border-color: var(--danger); background: var(--danger-soft); }
.drop.pending { border-color: var(--warning); background: var(--warning-soft); }
.drop.busy { cursor: progress; }
.drop.done.highlight, .drop.done.over { border-color: var(--accent); background: var(--accent-soft); }

/* Visually hidden but focusable, so the zone works from the keyboard. */
.picker {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
  pointer-events: none;
}

.icon {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--bg-card);
  border: 1px solid var(--border);
  color: var(--accent);
  font-weight: 700;
  font-size: 1.05rem;
}
.done .icon { color: var(--success); border-color: var(--success-bd); }
.error .icon { color: var(--danger); border-color: var(--danger-bd); }
.pending .icon { color: var(--warning-tx); border-color: var(--warning-bd); }

.text { display: flex; flex-direction: column; min-width: 0; }
.title { font-size: 0.95rem; color: var(--text-strong); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.detail { font-size: 0.82rem; color: var(--text-muted); }
.error .detail { color: var(--danger-tx); }
.pending .detail { color: var(--warning-tx); }

.drop-here {
  margin-left: auto;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--accent);
}

.remove {
  margin-left: auto;
  flex: 0 0 auto;
  padding: 0.3rem 0.7rem;
  border: 1px solid var(--border-strong);
  border-radius: 6px;
  background: var(--bg-card);
  color: var(--text);
  font-size: 0.8rem;
}
.remove:hover { border-color: var(--danger); color: var(--danger); }

.spin {
  width: 16px;
  height: 16px;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
