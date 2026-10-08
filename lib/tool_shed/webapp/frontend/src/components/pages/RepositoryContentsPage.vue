<script setup lang="ts">
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
import RepositoryContentsBrowser from "@/components/RepositoryContentsBrowser.vue"

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

function selectRevision(revision: string) {
    router.replace(contentsLocation(props.repositoryId, revision, props.file))
}

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
            <RepositoryContentsBrowser
                :revisions="browsableRevisions"
                :revision="currentRevision"
                :revision-unavailable="revisionUnavailable"
                :withdrawn="withdrawn"
                :files="files"
                :files-loading="filesLoading"
                :files-error="filesError"
                :file="file"
                :file-missing="fileMissing"
                :contents="contents"
                :contents-loading="contentsLoading"
                :contents-error="contentsError"
                @update:revision="selectRevision"
                @select="selectFile"
            />
        </template>
    </div>
</template>

<style scoped>
.contents-status {
    max-width: var(--shed-content-width);
    margin: 2rem auto;
    padding: 0 1.5rem;
}
</style>
