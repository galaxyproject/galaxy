<script setup lang="ts">
import { computed } from "vue"
interface Props {
    term: string
}

const props = defineProps<Props>()

const edamHref = computed(() => {
    return `https://edamontology.github.io/edam-browser/#${props.term}`
})
const bioPortalHref = computed(() => {
    return `https://edamontology.github.io/edam-browser/#${props.term}`
})
</script>
<template>
    <span> {{ term }} (<a :href="edamHref">EDAM ontology browser</a>) (<a :href="bioPortalHref">BioPortal</a>) </span>
</template>
