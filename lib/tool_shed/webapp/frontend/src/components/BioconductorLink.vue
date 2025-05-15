<script setup lang="ts">
import { computed } from "vue"
interface Props {
    id: string
}

const props = defineProps<Props>()

const href = computed(() => {
    return `https://bioconductor.org/packages/${props.id}`
})
</script>
<template>
    <a :href="href">{{ id }} (doi:10.18129/B9.bioc.{{ id }})</a>
</template>
