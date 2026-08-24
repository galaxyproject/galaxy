<script setup lang="ts">
import { GButton } from "@galaxyproject/galaxy-ui"
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { faMagnifyingGlass } from "@fortawesome/free-solid-svg-icons"
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
                        <GButton icon-only transparent aria-label="Search" @click="doSearch">
                            <FontAwesomeIcon :icon="faMagnifyingGlass" />
                        </GButton>
                    </template>
                </q-input>
            </div>
        </div>
    </div>
</template>
