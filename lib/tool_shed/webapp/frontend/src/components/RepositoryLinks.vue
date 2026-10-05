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
    <p v-if="currentRevision">
        <FontAwesomeIcon :icon="faLink" class="repository-link-icon" style="font-size: 32px" />
        <a class="repository-link-url" :href="link">{{ link }}</a>
        <GButton icon-only transparent aria-label="Copy link" @click="copyLink(link)">
            <FontAwesomeIcon :icon="faCopy" />
        </GButton>
    </p>
    <p v-if="homepage">
        <FontAwesomeIcon :icon="faHouse" class="repository-link-icon" style="font-size: 32px" />
        <a class="repository-link-url" :href="homepage">{{ homepage }}</a>
        <GButton icon-only transparent aria-label="Copy link" @click="copyLink(homepage)">
            <FontAwesomeIcon :icon="faCopy" />
        </GButton>
    </p>
    <p v-if="dev_url">
        <FontAwesomeIcon :icon="faCode" class="repository-link-icon" style="font-size: 32px" />
        <a class="repository-link-url" :href="dev_url">{{ dev_url }}</a>
        <GButton icon-only transparent aria-label="Copy link" @click="copyLink(dev_url)">
            <FontAwesomeIcon :icon="faCopy" />
        </GButton>
    </p>
</template>

<style scoped>
.repository-link-icon {
    padding-left: var(--spacing-1);
    padding-right: var(--spacing-4);
}

.repository-link-url {
    color: var(--color-galaxy-primary);
    font-weight: bold;
}
</style>
