<script setup lang="ts">
import { GAlert } from "@galaxyproject/galaxy-ui"
import { computed, ref, watch } from "vue"
import { storeToRefs } from "pinia"
import { useRouter } from "vue-router"
import {
    hasBrowsableFiles,
    newestRevision,
    repositoryFileContents,
    repositoryFiles,
    type RepositoryFileContents,
    type RepositoryFileEntry,
} from "@/api"
import { components } from "@/schema"
import { useRepositoryStore } from "@/stores"
import { contentsLocation } from "@/router"
import { errorMessageAsString } from "@/util"
import ErrorBanner from "@/components/ErrorBanner.vue"
import LoadingDiv from "@/components/LoadingDiv.vue"
import PageHeader from "@/components/PageHeader.vue"
import RepositoryFileTree from "@/components/RepositoryFileTree.vue"
import RepositoryFileViewer from "@/components/RepositoryFileViewer.vue"
import RevisionSelect from "@/components/RevisionSelect.vue"

type RepositoryMetadata = components["schemas"]["RepositoryMetadata"]

interface Props {
    repositoryId: string
    revision?: string | null
    file?: string | null
}

const props = withDefaults(defineProps<Props>(), {
    revision: null,
    file: null,
})

const router = useRouter()
const repositoryStore = useRepositoryStore()
const { loading, repository, repositoryMetadata } = storeToRefs(repositoryStore)

repositoryStore.setId(props.repositoryId)
watch(
    () => props.repositoryId,
    (repositoryId) => repositoryStore.setId(repositoryId),
)

const browsableRevisions = computed(() => {
    const browsable: RepositoryMetadata = {}
    for (const [key, revision] of Object.entries(repositoryMetadata.value ?? {})) {
        if (hasBrowsableFiles(revision)) {
            browsable[key] = revision
        }
    }
    return browsable
})
const changesets = computed(() => Object.values(browsableRevisions.value).map((r) => r.changeset_revision))
const currentRevision = computed(() => props.revision || newestRevision(browsableRevisions.value))
const revisionUnavailable = computed(() => !!props.revision && !changesets.value.includes(props.revision))
// The files API 404s deprecated and deleted repositories, as hgweb does
const withdrawn = computed(() => {
    if (repository.value?.deleted) {
        return "deleted"
    }
    return repository.value?.deprecated ? "deprecated" : null
})
const browseRevision = computed(() =>
    loading.value || withdrawn.value || revisionUnavailable.value ? null : currentRevision.value,
)

const files = ref<RepositoryFileEntry[] | null>(null)
const filesLoading = ref(false)
const filesError = ref<string | null>(null)
let filesRequest = 0

watch(
    browseRevision,
    async (revision) => {
        const request = ++filesRequest
        files.value = null
        filesError.value = null
        filesLoading.value = !!revision
        if (!revision) {
            return
        }
        try {
            const listing = await repositoryFiles(props.repositoryId, revision)
            if (request === filesRequest) {
                files.value = listing.files
            }
        } catch (e) {
            if (request === filesRequest) {
                filesError.value = "Failed to load the files in this revision."
            }
        } finally {
            if (request === filesRequest) {
                filesLoading.value = false
            }
        }
    },
    { immediate: true },
)

const fileMissing = computed(
    () => !!props.file && files.value !== null && !files.value.some((entry) => entry.path === props.file),
)
const fileToLoad = computed(() => (props.file && files.value && !fileMissing.value ? props.file : null))

const contents = ref<RepositoryFileContents | null>(null)
const contentsLoading = ref(false)
const contentsError = ref<string | null>(null)
let contentsRequest = 0

watch(
    [browseRevision, fileToLoad],
    async ([revision, path]) => {
        const request = ++contentsRequest
        contents.value = null
        contentsError.value = null
        contentsLoading.value = !!(revision && path)
        if (!revision || !path) {
            return
        }
        try {
            const result = await repositoryFileContents(props.repositoryId, revision, path)
            if (request === contentsRequest) {
                contents.value = result
            }
        } catch (e) {
            if (request === contentsRequest) {
                contentsError.value = errorMessageAsString(e)
            }
        } finally {
            if (request === contentsRequest) {
                contentsLoading.value = false
            }
        }
    },
    { immediate: true },
)

const selectedRevision = computed({
    get: () => currentRevision.value ?? "",
    set: (revision: string) => router.replace(contentsLocation(props.repositoryId, revision, props.file)),
})

function selectFile(path: string) {
    router.push(contentsLocation(props.repositoryId, props.revision, path))
}
</script>

<template>
    <div class="repository-contents-page">
        <LoadingDiv v-if="loading" class="contents-status" />
        <ErrorBanner v-else-if="!repository" error="Failed to load repository" class="contents-status" />
        <template v-else>
            <PageHeader title="Contents">
                <template #eyebrow>
                    <router-link :to="`/repositories_by_owner/${repository.owner}`">{{ repository.owner }}</router-link>
                    /
                    <router-link :to="`/repositories/${repositoryId}`">{{ repository.name }}</router-link>
                </template>
            </PageHeader>
            <div class="contents-body">
                <section v-if="withdrawn" class="contents-card contents-wide shed-card">
                    <div class="shed-card-body">
                        <GAlert variant="warning" class="contents-alert">
                            This repository has been {{ withdrawn }}, so its files can't be browsed.
                        </GAlert>
                    </div>
                </section>
                <section v-else-if="changesets.length === 0" class="contents-card contents-wide shed-card">
                    <p class="shed-card-body contents-message">
                        This repository has no installable revisions to browse.
                    </p>
                </section>
                <template v-else>
                    <section class="contents-card contents-wide shed-card">
                        <div class="contents-revision-bar">
                            <RevisionSelect :revisions="browsableRevisions" v-model="selectedRevision" />
                        </div>
                        <div v-if="revisionUnavailable" class="shed-card-body">
                            <GAlert variant="danger" class="contents-alert">
                                <strong
                                    >Revision {{ revision }} is not an installable revision of this repository.</strong
                                >
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
                                        @select="selectFile"
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
    </div>
</template>

<style scoped>
.contents-status {
    max-width: var(--shed-content-width);
    margin: 2rem auto;
    padding: 0 1.5rem;
}

.contents-body {
    display: grid;
    gap: 1.25rem;
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
