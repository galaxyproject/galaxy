<template>
    <div>
        <a href="#main-content" class="skip-link">Skip to main content</a>
        <q-layout view="hHh lpR fFf">
            <q-header elevated role="banner">
                <ShedToolbar title="Galaxy Tool Shed" />
            </q-header>
            <q-page-container id="main-content" role="main">
                <router-view />
            </q-page-container>
        </q-layout>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue"
import ShedToolbar from "./components/ShedToolbar.vue"

export default defineComponent({
    name: "App",
    components: {
        ShedToolbar,
    },
})
</script>

<style lang="sass">
// Skip link - visually hidden until focused
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
