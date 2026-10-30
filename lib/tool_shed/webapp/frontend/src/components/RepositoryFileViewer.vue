<script setup lang="ts">
import { faCircleInfo } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { computed } from "vue"
import type { RepositoryFileContents } from "@/api"
import { basename } from "@/components/fileTree"
import ConfigFileContents from "@/components/ConfigFileContents.vue"
import ErrorBanner from "@/components/ErrorBanner.vue"
import LoadingDiv from "@/components/LoadingDiv.vue"

interface Props {
    file: RepositoryFileContents | null
    loading?: boolean
    error?: string | null
}

const props = withDefaults(defineProps<Props>(), {
    loading: false,
    error: null,
})

const name = computed(() => (props.file ? basename(props.file.path) : ""))

// Why a file has no text to show, or null when it does
const notice = computed(() => {
    const file = props.file
    if (!file) {
        return null
    }
    if (file.type === "symlink") {
        return `${name.value} is a symbolic link, so it has no contents to show.`
    }
    if (file.truncated) {
        return `${name.value} is too large to show here (${(file.size / (1024 * 1024)).toFixed(1)} MB).`
    }
    if (file.binary) {
        return `${name.value} is a binary file and can't be shown here.`
    }
    if (!file.content) {
        return `${name.value} is empty.`
    }
    return null
})
</script>

<template>
    <div class="repository-file-viewer">
        <LoadingDiv v-if="loading" message="Loading file" />
        <ErrorBanner v-else-if="error" :error="error" />
        <p v-else-if="!file" class="file-viewer-notice">Select a file to view its contents.</p>
        <p v-else-if="notice" class="file-viewer-notice" role="status">
            <FontAwesomeIcon :icon="faCircleInfo" class="file-viewer-notice-icon" />
            {{ notice }}
        </p>
        <ConfigFileContents v-else :name="name" :contents="file.content ?? ''" what="File" />
    </div>
</template>

<style scoped>
.repository-file-viewer :deep(.config-file-contents) {
    margin: 0;
}

.file-viewer-notice {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin: 0;
    padding: 1rem 1.25rem;
    color: var(--shed-muted);
    background: color-mix(in srgb, var(--shed-page-bg) 55%, white);
    border: 1px dashed var(--shed-border);
    border-radius: var(--shed-radius-sm);
}

.file-viewer-notice-icon {
    flex: none;
    color: var(--shed-link);
}
</style>
