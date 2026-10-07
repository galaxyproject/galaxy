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
    <div class="landing-hero shed-brand-backdrop">
        <div class="landing-hero-inner">
            <p class="landing-eyebrow">The Galaxy Tool Shed</p>
            <h1 class="landing-title">Find <span class="landing-title-accent">Galaxy</span> tools</h1>
            <p class="landing-lede">
                Discover, install, and share the community-built tools that power Galaxy servers around the world.
            </p>
            <div class="landing-search" role="search">
                <FontAwesomeIcon :icon="faMagnifyingGlass" class="landing-search-icon" aria-hidden="true" />
                <GFormInput
                    :model-value="searchQuery"
                    class="landing-search-input"
                    placeholder="Search by name, owner, or description"
                    aria-label="Search repositories"
                    @update:model-value="searchQuery = $event ?? ''"
                    @keydown.enter="onEnter"
                />
                <GButton class="landing-search-button" aria-label="Search" @click="doSearch">Search</GButton>
            </div>
            <p class="landing-browse">
                Or browse
                <router-link to="/repositories_by_category">by category</router-link>
                &middot;
                <router-link to="/repositories_by_owner">by owner</router-link>
            </p>
        </div>
    </div>
</template>

<style scoped>
.landing-hero {
    position: relative;
    overflow: hidden;
    color: #fff;
}

.landing-hero-inner {
    max-width: 52rem;
    margin: 0 auto;
    padding: 4.5rem 1.5rem 4rem;
    text-align: center;
}

.landing-eyebrow {
    margin: 0 0 0.75rem;
    font-size: 0.85rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--color-ebony-clay-200, #bbc0d2);
}

.landing-title {
    margin: 0;
    font-size: clamp(2.25rem, 1.5rem + 3vw, 3.5rem);
    font-weight: 700;
    line-height: 1.05;
    letter-spacing: -0.01em;
    color: #fff;
}

.landing-title-accent {
    color: var(--shed-gold);
}

.landing-lede {
    margin: 1rem auto 2rem;
    max-width: 36rem;
    font-size: 1.15rem;
    color: var(--color-ebony-clay-100, #d3d6e2);
}

.landing-search {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.4rem 0.4rem 0.4rem 1.1rem;
    background: #fff;
    border-radius: 0.75rem;
    box-shadow:
        0 10px 30px rgba(10, 14, 28, 0.35),
        0 0 0 1px rgba(255, 255, 255, 0.08);
    transition: box-shadow var(--shed-transition);
}

.landing-search:focus-within {
    box-shadow:
        0 10px 30px rgba(10, 14, 28, 0.35),
        0 0 0 3px var(--shed-gold);
}

.landing-search-icon {
    flex: none;
    color: var(--shed-muted);
}

.landing-search :deep(.landing-search-input) {
    flex: 1;
    min-width: 0;
    height: 2.75rem;
    padding: 0;
    font-size: 1.05rem;
    color: var(--shed-heading);
    background: transparent;
    border: none;
    box-shadow: none;
}

.landing-search :deep(.landing-search-input:focus) {
    outline: none;
    box-shadow: none;
}

/* Gold is the brand's primary call to action: dark text on gold, darkening on hover */
.landing-search :deep(.g-button.landing-search-button) {
    flex: none;
    height: 2.75rem;
    padding: 0 1.4rem;
    font-size: 1rem;
    font-weight: 700;
    color: var(--color-galaxy-dark, #2c3143);
    background: var(--shed-gold);
    border: none;
    border-radius: 0.5rem;
}

.landing-search :deep(.g-button.landing-search-button:hover) {
    background: var(--color-galaxy-gold-dark, #d19e00);
}

.landing-browse {
    margin: 1.25rem 0 0;
    color: var(--color-ebony-clay-200, #bbc0d2);
}

.landing-browse a {
    color: #fff;
    font-weight: 700;
    text-decoration-color: rgba(255, 255, 255, 0.35);
}

.landing-browse a:hover {
    color: var(--shed-gold);
    text-decoration-color: var(--shed-gold);
}

@media (max-width: 599px) {
    .landing-hero-inner {
        padding: 3rem 1rem 2.75rem;
    }

    .landing-search-icon {
        display: none;
    }

    .landing-search {
        padding-left: 0.85rem;
    }
}
</style>
