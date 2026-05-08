<script setup lang="ts">
/**
 * Stroke-style SVG icons for the landing page. All share the same
 * 24×24 viewBox, 1.75 stroke width and currentColor fill, so they
 * render consistently and pick up colour from CSS.
 */
defineProps<{
  name:
    | 'privacy'
    | 'detect'
    | 'scale'
    | 'shield'
    | 'play'
    | 'split'
    | 'cap'
    | 'bolt'
    | 'users'
}>()
</script>

<template>
  <svg
    class="landing-icon"
    :class="`icon-${name}`"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.75"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <!-- Lock — privacy -->
    <template v-if="name === 'privacy'">
      <rect x="3.5" y="11" width="17" height="10.5" rx="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
      <circle cx="12" cy="16" r="1.2" fill="currentColor" stroke="none" />
      <path d="M12 17v2" />
    </template>

    <!-- Magnifier with embedded marker — dynamic detection -->
    <template v-else-if="name === 'detect'">
      <circle cx="10.5" cy="10.5" r="6.5" />
      <path d="m21 21-4.6-4.6" />
      <path d="M8 9h5M8 12h3.5" />
    </template>

    <!-- Balance scales — grade suggestion -->
    <template v-else-if="name === 'scale'">
      <path d="M12 3v18" />
      <path d="M8 21h8" />
      <path d="M4 7h16" />
      <path d="M12 4 6 7l3 7a3 3 0 0 0 6 0L12 4Z" stroke-linejoin="miter" />
      <path d="M12 4l6 3-3 7a3 3 0 0 1-6 0" stroke-linejoin="miter" />
    </template>

    <!-- Shield — plagiarism guard -->
    <template v-else-if="name === 'shield'">
      <path d="M12 3 4 6v6c0 4.4 3.4 8.4 8 9 4.6-.6 8-4.6 8-9V6l-8-3Z" />
      <path d="m9 12 2 2 4-4" />
    </template>

    <!-- Play in a circle — run code -->
    <template v-else-if="name === 'play'">
      <circle cx="12" cy="12" r="9" />
      <path d="M10 8.5 16 12l-6 3.5z" fill="currentColor" stroke="currentColor" stroke-linejoin="round" />
    </template>

    <!-- Split / two columns — side-by-side review -->
    <template v-else-if="name === 'split'">
      <rect x="3.5" y="4" width="7.5" height="16" rx="1.5" />
      <rect x="13" y="4" width="7.5" height="16" rx="1.5" />
      <path d="M5.5 8h3.5M5.5 11h3M15 8h3.5M15 11h3" />
    </template>

    <!-- Graduation cap — university instructors -->
    <template v-else-if="name === 'cap'">
      <path d="M2 9.5 12 5l10 4.5L12 14 2 9.5Z" stroke-linejoin="miter" />
      <path d="M6 11.5v4c0 0 2 2.5 6 2.5s6-2.5 6-2.5v-4" />
      <path d="M22 9.5v4" />
    </template>

    <!-- Lightning bolt — bootcamp / speed -->
    <template v-else-if="name === 'bolt'">
      <path d="M13 2 4.5 13H10l-1 9L19.5 11H14l1-9z" stroke-linejoin="miter" />
    </template>

    <!-- Three users — teaching assistants -->
    <template v-else-if="name === 'users'">
      <circle cx="9" cy="8" r="3.5" />
      <path d="M2.5 20v-1.5a4 4 0 0 1 4-4h5a4 4 0 0 1 4 4V20" />
      <path d="M16 4.5a3.5 3.5 0 0 1 0 7" />
      <path d="M21.5 20v-1.5a4 4 0 0 0-3-3.87" />
    </template>
  </svg>
</template>

<style scoped>
.landing-icon {
  width: 100%;
  height: 100%;
  display: block;
}
</style>
