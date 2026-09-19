<script setup lang="ts">
import { ref } from "vue"
import { useRouter } from "vue-router"

const router = useRouter()
const searchQuery = ref("")

function doSearch() {
    if (searchQuery.value.trim()) {
        router.push({ path: "/repositories_by_search", query: { q: searchQuery.value.trim() } })
    }
}
</script>
<template>
    <div class="text-center q-pa-xl">
        <h1 class="text-h4 q-mb-md">Find Galaxy Tools</h1>
        <div class="row justify-center">
            <div class="col-12 col-md-8 col-lg-6">
                <q-input v-model="searchQuery" outlined placeholder="Search repositories..." @keyup.enter="doSearch">
                    <template #append>
                        <q-btn flat dense icon="search" aria-label="Search" @click="doSearch" />
                    </template>
                </q-input>
            </div>
        </div>
    </div>
</template>
