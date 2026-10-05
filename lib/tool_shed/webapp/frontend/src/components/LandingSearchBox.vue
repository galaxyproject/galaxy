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
    <div class="landing-search-wrapper">
        <h1 class="landing-title">Find Galaxy Tools</h1>
        <div class="landing-search-row">
            <div class="landing-search">
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
.landing-search-wrapper {
    text-align: center;
    padding: calc(var(--spacing-8) + var(--spacing-4));
}

.landing-title {
    margin: 0 0 var(--spacing-4) 0;
    font-size: 2.125rem;
}

.landing-search-row {
    display: flex;
    justify-content: center;
}

.landing-search {
    display: flex;
    gap: var(--spacing-2);
    width: 100%;
}

@media (min-width: 1024px) {
    .landing-search {
        width: 66.6667%;
    }
}

@media (min-width: 1440px) {
    .landing-search {
        width: 50%;
    }
}

.landing-search :deep(.g-form-input) {
    flex: 1;
}
</style>
