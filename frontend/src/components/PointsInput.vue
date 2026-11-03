<script setup lang="ts">
/**
 * Compact stepper for "max points per question". Two side buttons nudge
 * by `step`, the centre cell stays editable for the rare exact-value
 * case. Designed to be the kind of thing you click twice instead of
 * having to focus and retype.
 *
 * Click-and-hold accelerates after ~250ms so adjusting from 0 to 8 in
 * steps of 0.5 isn't 16 individual clicks.
 */

import { computed, onBeforeUnmount, ref } from 'vue'

const props = withDefaults(
  defineProps<{
    modelValue: number
    step?: number
    min?: number
    max?: number
    disabled?: boolean
  }>(),
  { step: 0.5, min: 0, disabled: false },
)
const emit = defineEmits<{ 'update:modelValue': [value: number] }>()

const focused = ref(false)

function clamp(v: number): number {
  if (Number.isNaN(v)) v = 0
  if (props.min !== undefined && v < props.min) v = props.min
  if (props.max !== undefined && v > props.max) v = props.max
  // Round to two decimals — avoids 1.7000000000001 from float math.
  return Math.round(v * 100) / 100
}

function setValue(v: number) {
  emit('update:modelValue', clamp(v))
}

function bump(delta: number) {
  setValue(props.modelValue + delta)
}

const canDecrement = computed(
  () => !props.disabled && (props.min === undefined || props.modelValue > props.min),
)
const canIncrement = computed(
  () => !props.disabled && (props.max === undefined || props.modelValue < props.max),
)

// --- press-and-hold acceleration --------------------------------------
let holdTimer: number | null = null
let holdInterval = 200

function startHold(delta: number) {
  if (props.disabled) return
  bump(delta) // immediate hit
  holdInterval = 200
  const tick = () => {
    bump(delta)
    holdInterval = Math.max(35, holdInterval * 0.85)
    holdTimer = window.setTimeout(tick, holdInterval)
  }
  holdTimer = window.setTimeout(tick, 350) // small delay before auto-repeat
}

function stopHold() {
  if (holdTimer !== null) {
    clearTimeout(holdTimer)
    holdTimer = null
  }
}

onBeforeUnmount(stopHold)

function onInputChange(e: Event) {
  const raw = (e.target as HTMLInputElement).value.replace(',', '.')
  const v = Number.parseFloat(raw)
  setValue(v)
}

// Arrow-up / arrow-down on the centre input nudge by step (instead of
// the browser's hardcoded 1.0 step for type=number).
function onKeyDown(e: KeyboardEvent) {
  if (props.disabled) return
  if (e.key === 'ArrowUp') {
    e.preventDefault()
    bump(props.step)
  } else if (e.key === 'ArrowDown') {
    e.preventDefault()
    bump(-props.step)
  }
}
</script>

<template>
  <div class="points-input" :class="{ disabled, focused }">
    <button
      type="button"
      class="step"
      :disabled="!canDecrement"
      aria-label="decrease"
      @mousedown="startHold(-step)"
      @mouseup="stopHold"
      @mouseleave="stopHold"
      @touchstart.prevent="startHold(-step)"
      @touchend="stopHold"
    >−</button>
    <input
      type="text"
      inputmode="decimal"
      class="value"
      :value="modelValue"
      :disabled="disabled"
      @change="onInputChange"
      @focus="focused = true"
      @blur="focused = false"
      @keydown="onKeyDown"
    />
    <button
      type="button"
      class="step"
      :disabled="!canIncrement"
      aria-label="increase"
      @mousedown="startHold(step)"
      @mouseup="stopHold"
      @mouseleave="stopHold"
      @touchstart.prevent="startHold(step)"
      @touchend="stopHold"
    >+</button>
  </div>
</template>

<style scoped>
.points-input {
  display: inline-flex;
  align-items: stretch;
  border: 1px solid var(--border-strong);
  border-radius: 6px;
  overflow: hidden;
  background: var(--bg-card);
  transition: border-color 0.1s, box-shadow 0.1s;
  user-select: none;
}
.points-input.focused {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
}
.points-input.disabled { opacity: 0.55; }

.value {
  border: none;
  background: transparent;
  width: 52px;
  text-align: center;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-weight: 600;
  color: var(--text);
  padding: 0.3rem 0.2rem;
  font-size: 0.92rem;
  -moz-appearance: textfield;
}
.value::-webkit-outer-spin-button,
.value::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
.value:focus { outline: none; }

.step {
  width: 28px;
  background: var(--bg-soft);
  border: none;
  cursor: pointer;
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-muted);
  padding: 0;
  line-height: 1;
  transition: background 0.1s, color 0.1s;
}
.step:hover:not(:disabled) {
  background: var(--accent-soft);
  color: var(--accent);
}
.step:active:not(:disabled) {
  background: var(--primary);
  color: white;
}
.step:disabled { cursor: not-allowed; opacity: 0.5; }
.step:first-of-type { border-right: 1px solid var(--border); }
.step:last-of-type { border-left: 1px solid var(--border); }
</style>
