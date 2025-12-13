<script setup lang="ts">
import "vue-json-pretty/lib/styles.css"
import VueJsonPretty from "vue-json-pretty"
import { getFieldDescription } from "./fieldDescriptions"

interface Props {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    data: any // vue-json-pretty accepts any JSON-serializable data
    modelName?: string // e.g., "RepositoryRevisionMetadata"
    deep?: number
}
withDefaults(defineProps<Props>(), {
    modelName: undefined,
    deep: 2,
})
</script>

<template>
    <VueJsonPretty :data="data" :virtual="false" :showLength="true" :deep="deep">
        <template v-slot:nodeKey="{ node, defaultKey }">
            <span
                :title="getFieldDescription(modelName, String(node.key))"
                :class="{ 'has-description': getFieldDescription(modelName, String(node.key)) }"
            >
                {{ defaultKey }}
            </span>
        </template>
    </VueJsonPretty>
</template>

<style scoped>
.has-description {
    border-bottom: 1px dotted #666;
    cursor: help;
}
</style>
