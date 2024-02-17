<script setup lang="ts">
import { ref } from "vue"
import { fetcher, components } from "@/schema"
import PageContainer from "@/components/PageContainer.vue"

const searchIndexer = fetcher.path("/api/tools/build_search_index").method("put").create()
type IndexResults = components["schemas"]["BuildSearchIndexResponse"]

const searchResults = ref(null as IndexResults | null)

async function onIndex() {
    const { data } = await searchIndexer({})
    searchResults.value = data
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
