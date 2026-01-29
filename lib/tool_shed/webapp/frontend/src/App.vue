<template>
    <div>
        <q-layout view="hHh lpR fFf">
            <q-header elevated>
                <ShedToolbar title="Galaxy Tool Shed" />
            </q-header>
            <q-page-container>
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
