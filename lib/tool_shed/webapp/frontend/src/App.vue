<template>
    <div>
        <a href="#main-content" class="skip-link">Skip to main content</a>
        <header class="shed-header">
            <ShedToolbar title="Tool Shed" />
        </header>
        <main id="main-content" class="shed-main" tabindex="-1">
            <router-view />
        </main>
        <GToast />
    </div>
</template>

<script lang="ts">
import { GToast } from "@galaxyproject/galaxy-ui"
import { defineComponent } from "vue"
import ShedToolbar from "./components/ShedToolbar.vue"

export default defineComponent({
    name: "App",
    components: {
        GToast,
        ShedToolbar,
    },
})
</script>

<style lang="sass">
// Skip link - visually hidden until focused
// Quasar's typography still loads (for q-select) and gives bare h1-h6 display-sized line heights
// and letter spacing; components size their own headings, so take the metrics back to normal.
// Prefixed with body to outrank Quasar's element rules, which load after this file.
body
  h1, h2, h3, h4, h5, h6
    line-height: 1.25
    letter-spacing: normal

// The masthead stays put while the page scrolls under it, as Quasar's fixed q-header did
.shed-header
  position: sticky
  top: 0
  z-index: 1000
  box-shadow: 0 1px 0 rgba(255, 255, 255, 0.04), 0 2px 8px rgba(25, 31, 51, 0.25)

.shed-main
  // The skip link lands here; keep its start clear of the sticky masthead
  scroll-margin-top: var(--shed-masthead-height)
  // Fill the window so short pages still sit on the page background
  min-height: calc(100vh - var(--shed-masthead-height))
  &:focus
    outline: none

.skip-link
  position: absolute
  top: -40px
  left: 0
  background: $primary
  color: white
  padding: 8px 16px
  z-index: 9999
  text-decoration: none
  font-weight: bold
  border-radius: 0 0 4px 0
  &:focus
    top: 0

// Horizontal rules, standing in for Quasar's q-separator
hr
  // Quasar's reset zeroes hr height, so draw the line as a border instead
  border: none
  border-top: 1px solid var(--shed-border-subtle)
  margin: 0
  &.spaced
    margin: 0.5rem 0

// Rendered READMEs bring their own rules and expect the usual spacing around them
.repository-readme hr
  margin: 1rem 0

// Focus indicators for keyboard navigation
*:focus-visible
  outline: 3px solid $accent !important
  outline-offset: 2px

// A choice, provides more contrast but is ultimately a bit
// too programmer app circa 2005?
//body
//    background: $secondary

.masonry-grid > .flex-break
  flex: 1 0 100% !important
  width: 0 !important

$x: 3
@for $i from 1 through ($x - 1)
    .masonry-grid > div:nth-child(#{$x}n + #{$i})
        order: #{$i}

.masonry-grid > div:nth-child(#{$x}n)
  order: 3

.masonry-grid

  .masonry-grid-item
    width: 33%
    padding: 1px
    > div
      padding: 4px 8px
</style>
