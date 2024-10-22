<script setup lang="ts">
import { ref } from "vue"
import { ToolShedApi, components } from "@/schema"
import PageContainer from "@/components/PageContainer.vue"
import { notifyOnCatch } from "@/util"

type IndexResults = components["schemas"]["BuildSearchIndexResponse"]

const searchResults = ref<IndexResults>()

async function onIndex() {
    try {
        const { data } = await ToolShedApi().PUT("/api/tools/build_search_index")
        searchResults.value = data
    } catch (e) {
        notifyOnCatch(e)
    }
}
</script>
<template>
    <page-container>
        <q-btn label="Re-index search" @click="onIndex" />
        <div v-if="searchResults">
            {{ searchResults }}
        </div>
    </page-container>
</template>
