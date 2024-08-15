<script setup lang="ts">
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
        copyAndNotify(link, "Link copied to your clipboard")
    }
}

const props = defineProps<RepositoryLinkProps>()
const link = computed(() => `/view/${props.repository.owner}/${props.repository.name}/${props.currentRevision}`)
const homepage = computed(() => props.repository.homepage_url)
const dev_url = computed(() => props.repository.remote_repository_url)
</script>
<template>
    <p v-if="currentRevision">
        <q-icon name="link" size="md" class="q-pl-xs q-pr-md" />
        <a class="text-primary text-bold" :href="link">{{ link }}</a>
        <q-btn size="sm" class="q-px-sm" flat dense icon="content_copy" @click="copyLink(link)" />
    </p>
    <p v-if="homepage">
        <q-icon name="home" size="md" class="q-pl-xs q-pr-md" />
        <a class="text-primary text-bold" :href="homepage">{{ homepage }}</a>
        <q-btn size="sm" class="q-px-sm" flat dense icon="content_copy" @click="copyLink(homepage)" />
    </p>
    <p v-if="dev_url">
        <q-icon name="code" size="md" class="q-pl-xs q-pr-md" />
        <a class="text-primary text-bold" :href="dev_url">{{ dev_url }}</a>
        <q-btn size="sm" class="q-px-sm" flat dense icon="content_copy" @click="copyLink(dev_url)" />
    </p>
</template>
