<script setup lang="ts">
import { computed } from "vue"
interface Props {
    id: string
}

const props = defineProps<Props>()

const href = computed(() => {
    return `http://spdx.org/licenses/${props.id}`
})
</script>
<template>
    <span
        ><a :href="href">{{ id }}</a></span
    >
</template>
