<script setup lang="ts">
import { GAlert } from "@galaxyproject/galaxy-ui"
import { computed } from "vue"
import type { RepositoryFileContents, RepositoryFileEntry } from "@/api"
import { components } from "@/schema"
import ErrorBanner from "@/components/ErrorBanner.vue"
import LoadingDiv from "@/components/LoadingDiv.vue"
import RepositoryFileTree from "@/components/RepositoryFileTree.vue"
import RepositoryFileViewer from "@/components/RepositoryFileViewer.vue"
import RevisionSelect from "@/components/RevisionSelect.vue"

type RepositoryMetadata = components["schemas"]["RepositoryMetadata"]

interface Props {
    revisions: RepositoryMetadata
    revision: string | null
    revisionUnavailable?: boolean
    withdrawn?: "deleted" | "deprecated" | null
    files: RepositoryFileEntry[] | null
    filesLoading?: boolean
    filesError?: string | null
    file?: string | null
    fileMissing?: boolean
    contents: RepositoryFileContents | null
    contentsLoading?: boolean
    contentsError?: string | null
}

const props = withDefaults(defineProps<Props>(), {
    revisionUnavailable: false,
    withdrawn: null,
    filesLoading: false,
    filesError: null,
    file: null,
    fileMissing: false,
    contentsLoading: false,
    contentsError: null,
})

const emit = defineEmits<{
    (event: "update:revision", revision: string): void
    (event: "select", path: string): void
}>()

const hasRevisions = computed(() => Object.keys(props.revisions).length > 0)
const selectedRevision = computed({
    get: () => props.revision ?? "",
    set: (revision: string) => emit("update:revision", revision),
})
</script>

<template>
    <div class="contents-body">
        <section v-if="withdrawn" class="contents-card contents-wide shed-card">
            <div class="shed-card-body">
                <GAlert variant="warning" class="contents-alert">
                    This repository has been {{ withdrawn }}, so its files can't be browsed.
                </GAlert>
            </div>
        </section>
        <section v-else-if="!hasRevisions" class="contents-card contents-wide shed-card">
            <p class="shed-card-body contents-message">This repository has no installable revisions to browse.</p>
        </section>
        <template v-else>
            <section class="contents-card contents-wide shed-card">
                <div class="contents-revision-bar">
                    <RevisionSelect :revisions="revisions" v-model="selectedRevision" />
                </div>
                <div v-if="revisionUnavailable" class="shed-card-body">
                    <GAlert variant="danger" class="contents-alert">
                        <strong>Revision {{ revision }} is not an installable revision of this repository.</strong>
                    </GAlert>
                </div>
            </section>
            <template v-if="!revisionUnavailable">
                <nav aria-label="Files" class="contents-card contents-aside shed-card">
                    <div class="shed-card-body">
                        <h2 class="shed-section-title">Files</h2>
                        <LoadingDiv v-if="filesLoading" message="Loading files" />
                        <ErrorBanner v-else-if="filesError" :error="filesError" />
                        <template v-else-if="files">
                            <RepositoryFileTree
                                v-if="files.length > 0"
                                :files="files"
                                :selected="file"
                                @select="emit('select', $event)"
                            />
                            <p v-else class="contents-message shed-muted">This revision has no files.</p>
                        </template>
                    </div>
                </nav>
                <section class="contents-card contents-main shed-card">
                    <div class="shed-card-body">
                        <h2 v-if="file" class="contents-file-path">{{ file }}</h2>
                        <GAlert v-if="fileMissing" variant="warning" class="contents-alert">
                            {{ file }} is not in this revision.
                        </GAlert>
                        <RepositoryFileViewer
                            v-else
                            :file="contents"
                            :loading="contentsLoading || (!!file && filesLoading)"
                            :error="contentsError"
                        />
                    </div>
                </section>
            </template>
        </template>
    </div>
</template>

<style scoped>
.contents-body {
    display: grid;
    gap: 1.25rem;
    width: 100%;
    max-width: var(--shed-content-width);
    margin: 0 auto;
    padding: 1.75rem 1.5rem 3rem;
}

@media (min-width: 1024px) {
    .contents-body {
        grid-template-columns: 20rem minmax(0, 1fr);
        align-items: start;
    }

    .contents-wide {
        grid-column: 1 / -1;
    }

    .contents-aside {
        position: sticky;
        top: calc(var(--shed-masthead-height) + 1rem);
        max-height: calc(100vh - var(--shed-masthead-height) - 2rem);
        overflow-y: auto;
    }
}

@media (max-width: 599px) {
    .contents-body {
        padding: 1.25rem 1rem 2rem;
    }
}

.contents-card {
    min-width: 0;
    overflow: hidden;
}

.contents-revision-bar {
    padding: 0.85rem 1.25rem;
    background: color-mix(in srgb, var(--shed-page-bg) 55%, white);
}

.contents-alert {
    margin: 0;
}

.contents-message {
    margin: 0;
}

.contents-file-path {
    margin: 0 0 0.75rem;
    font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    font-size: 1rem;
    font-weight: 700;
    overflow-wrap: anywhere;
}
</style>
