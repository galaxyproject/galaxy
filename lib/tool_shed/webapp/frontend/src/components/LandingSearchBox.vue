<script setup lang="ts">
import { GButton, GFormInput } from "@galaxyproject/galaxy-ui"
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { faMagnifyingGlass } from "@fortawesome/free-solid-svg-icons"
import { ref } from "vue"
import { useRouter } from "vue-router"

const router = useRouter()
const searchQuery = ref("")

// GFormInput forwards keydown rather than keyup, so skip the auto-repeats of a held Enter and
// the Enter that confirms an IME composition
function onEnter(event: KeyboardEvent) {
    if (!event.repeat && !event.isComposing) {
        doSearch()
    }
}

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
            <div class="col-12 col-md-8 col-lg-6 landing-search">
                <GFormInput
                    :model-value="searchQuery"
                    placeholder="Search repositories..."
                    aria-label="Search repositories"
                    @update:model-value="searchQuery = $event ?? ''"
                    @keydown.enter="onEnter"
                />
                <GButton icon-only transparent aria-label="Search" @click="doSearch">
                    <FontAwesomeIcon :icon="faMagnifyingGlass" />
                </GButton>
            </div>
        </div>
    </div>
</template>

<style scoped>
.landing-search {
    display: flex;
    gap: var(--spacing-2);
}

.landing-search :deep(.g-form-input) {
    flex: 1;
}
</style>
