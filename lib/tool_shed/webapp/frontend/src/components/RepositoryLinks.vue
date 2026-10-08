<script setup lang="ts">
import { faCode, faHouse, faLink } from "@fortawesome/free-solid-svg-icons"
import { GButton } from "@galaxyproject/galaxy-ui"
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { faCopy } from "@fortawesome/free-solid-svg-icons"
import { computed } from "vue"
import { copyAndNotify } from "@/util"
import { components } from "@/schema"

type DetailedRepository = components["schemas"]["DetailedRepository"]

interface RepositoryLinkProps {
    repository: DetailedRepository
    currentRevision: string | null
}

// why are the v-if's below not preventing needing undefined here typescript?
function copyLink(link: string | undefined) {
    if (link) {
        const absoluteLink = link.startsWith("http") ? link : `${window.location.origin}${link}`
        copyAndNotify(absoluteLink, "Link copied to your clipboard")
    }
}

const props = defineProps<RepositoryLinkProps>()
const link = computed(() => `/view/${props.repository.owner}/${props.repository.name}/${props.currentRevision}`)
const homepage = computed(() => props.repository.homepage_url)
const dev_url = computed(() => props.repository.remote_repository_url)
</script>
<template>
    <ul class="repository-links">
        <li v-if="currentRevision" class="repository-link">
            <FontAwesomeIcon :icon="faLink" class="repository-link-icon" fixed-width />
            <span class="repository-link-text">
                <span class="repository-link-label">Permalink</span>
                <a class="repository-link-url" :href="link">{{ link }}</a>
            </span>
            <GButton
                icon-only
                transparent
                size="small"
                aria-label="Copy link"
                title="Copy link"
                @click="copyLink(link)"
            >
                <FontAwesomeIcon :icon="faCopy" />
            </GButton>
        </li>
        <li v-if="homepage" class="repository-link">
            <FontAwesomeIcon :icon="faHouse" class="repository-link-icon" fixed-width />
            <span class="repository-link-text">
                <span class="repository-link-label">Homepage</span>
                <a class="repository-link-url" :href="homepage">{{ homepage }}</a>
            </span>
            <GButton
                icon-only
                transparent
                size="small"
                aria-label="Copy link"
                title="Copy link"
                @click="copyLink(homepage)"
            >
                <FontAwesomeIcon :icon="faCopy" />
            </GButton>
        </li>
        <li v-if="dev_url" class="repository-link">
            <FontAwesomeIcon :icon="faCode" class="repository-link-icon" fixed-width />
            <span class="repository-link-text">
                <span class="repository-link-label">Development repository</span>
                <a class="repository-link-url" :href="dev_url">{{ dev_url }}</a>
            </span>
            <GButton
                icon-only
                transparent
                size="small"
                aria-label="Copy link"
                title="Copy link"
                @click="copyLink(dev_url)"
            >
                <FontAwesomeIcon :icon="faCopy" />
            </GButton>
        </li>
    </ul>
</template>

<style scoped>
.repository-links {
    margin: 0;
    padding: 0;
    list-style: none;
}

.repository-link {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.5rem 0;
}

.repository-link + .repository-link {
    border-top: 1px solid var(--shed-border-subtle);
}

.repository-link-icon {
    flex: none;
    color: var(--color-galaxy-primary);
}

.repository-link-text {
    flex: 1;
    min-width: 0;
}

.repository-link-label {
    display: block;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--shed-muted);
}

.repository-link-url {
    display: block;
    overflow: hidden;
    font-size: 0.9rem;
    white-space: nowrap;
    text-overflow: ellipsis;
}

.repository-link :deep(.g-button.g-transparent) {
    flex: none;
    color: var(--shed-muted);
}
</style>
