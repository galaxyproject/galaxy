<script setup lang="ts">
import type { IconDefinition } from "@fortawesome/fontawesome-svg-core"
import { faCode, faCopy, faHouse, faLink } from "@fortawesome/free-solid-svg-icons"
import { GButton } from "@galaxyproject/galaxy-ui"
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { computed } from "vue"
import { copyAndNotify } from "@/util"
import { components } from "@/schema"

type DetailedRepository = components["schemas"]["DetailedRepository"]

interface RepositoryLinkProps {
    repository: DetailedRepository
    currentRevision: string | null
}

interface LinkRow {
    label: string
    icon: IconDefinition
    href: string
}

function copyLink(href: string) {
    const absoluteLink = href.startsWith("http") ? href : `${window.location.origin}${href}`
    copyAndNotify(absoluteLink, "Link copied to your clipboard")
}

const props = defineProps<RepositoryLinkProps>()

const rows = computed(() => {
    const { owner, name, homepage_url, remote_repository_url } = props.repository
    const rows: LinkRow[] = []
    if (props.currentRevision) {
        rows.push({ label: "Permalink", icon: faLink, href: `/view/${owner}/${name}/${props.currentRevision}` })
    }
    if (homepage_url) {
        rows.push({ label: "Homepage", icon: faHouse, href: homepage_url })
    }
    if (remote_repository_url) {
        rows.push({ label: "Development repository", icon: faCode, href: remote_repository_url })
    }
    return rows
})
</script>
<template>
    <ul class="repository-links">
        <li v-for="row in rows" :key="row.label" class="repository-link">
            <FontAwesomeIcon :icon="row.icon" class="repository-link-icon" fixed-width />
            <span class="repository-link-text">
                <span class="repository-link-label">{{ row.label }}</span>
                <a class="repository-link-url" :href="row.href">{{ row.href }}</a>
            </span>
            <GButton
                icon-only
                transparent
                size="small"
                aria-label="Copy link"
                title="Copy link"
                @click="copyLink(row.href)"
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
