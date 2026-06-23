<script setup lang="ts">
import { computed } from "vue"
interface Props {
    id: string
}

const props = defineProps<Props>()

const bioToolHref = computed(() => {
    return `https://bio.tools/${props.id}`
})

const openEBenchHref = computed(() => {
    return `https://openebench.bsc.es/tool/${props.id}`
})
</script>
<template>
    <span> {{ id }} (<a :href="bioToolHref">bio.tools</a>) (<a :href="openEBenchHref">OpenEBench</a>) </span>
</template>
