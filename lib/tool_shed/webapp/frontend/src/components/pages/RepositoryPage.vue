<script setup lang="ts">
import { computed, watch, ref } from "vue"
import { storeToRefs } from "pinia"
import { useRepositoryStore } from "@/stores"
import LoadingDiv from "@/components/LoadingDiv.vue"
import ErrorBanner from "@/components/ErrorBanner.vue"
import RevisionSelect from "@/components/RevisionSelect.vue"
import RepositoryTool from "@/components/RepositoryTool.vue"
import ManagePushAccess from "@/components/ManagePushAccess.vue"
import RepositoryActions from "@/components/RepositoryActions.vue"
import RevisionActions from "@/components/RevisionActions.vue"
import RepositoryHealth from "@/components/RepositoryHealth.vue"
import InstallingHowto from "@/components/InstallingHowto.vue"
import RepositoryLinks from "@/components/RepositoryLinks.vue"
import RepositoryExplore from "@/components/RepositoryExplore.vue"
import { type RevisionMetadata, type RepositoryTool as RepositoryToolModel } from "@/schema"
import { ToolShedApi } from "@/schema"
import { notifyOnCatch } from "@/util"
import { UPDATING_WITH_PLANEMO_URL } from "@/constants"

interface RepositoryProps {
    repositoryId: string
    changesetRevision?: string | null
}

function onUpdate() {
    repositoryStore.refresh()
}

async function onDeprecate() {
    const repositoryId = repository.value?.id
    if (repositoryId) {
        ToolShedApi()
            .PUT("/api/repositories/{encoded_repository_id}/deprecated", {
                params: { path: { encoded_repository_id: repositoryId } },
            })
            .then(onUpdate)
            .catch(notifyOnCatch)
    }
}

async function onUndeprecate() {
    const repositoryId = repository.value?.id
    if (repositoryId) {
        ToolShedApi()
            .DELETE("/api/repositories/{encoded_repository_id}/deprecated", {
                params: { path: { encoded_repository_id: repositoryId } },
            })
            .then(onUpdate)
            .catch(notifyOnCatch)
    }
}

const props = defineProps<RepositoryProps>()

const repositoryStore = useRepositoryStore()
const { empty, loading, repository, repositoryMetadata, repositoryInstallInfo, repositoryPermissions } =
    storeToRefs(repositoryStore)

watch(
    () => props.repositoryId,
    (_first, second) => {
        repositoryStore.setId(second)
    }
)

function trsToolId(tool: RepositoryToolModel) {
    const repo = repository.value
    if (repo) {
        const repoOwner = repo.owner
        const repoName = repo.name
        const toolId = tool.id
        return `${repoOwner}~${repoName}~${toolId}`
    } else {
        return undefined
    }
}

const repositoryRevisionKeys = computed(() => {
    const keys = []
    if (repositoryMetadata.value) {
        for (const key of Object.keys(repositoryMetadata?.value || {})) {
            keys.push(key)
        }
    }
    return keys
})

const repositoryChangesetRevisions = computed(() => {
    const changesets = []
    if (repositoryRevisionKeys.value) {
        for (const key of repositoryRevisionKeys.value) {
            const [, changeset] = key.split(":", 2)
            changesets.push(changeset)
        }
    }
    return changesets
})

const metadataByRevision = computed(() => {
    const byRevision: { [revision: string]: RevisionMetadata } = {}
    if (repositoryMetadata.value) {
        for (const key of Object.keys(repositoryMetadata?.value || {})) {
            const [, changeset] = key.split(":", 2)
            const revisionMetadata = repositoryMetadata?.value[key]
            if (changeset && revisionMetadata) {
                byRevision[changeset] = revisionMetadata
            }
        }
    }
    return byRevision
})

const isUnknownRevision = computed(() => {
    console.log(metadataByRevision.value)
    console.log(currentRevision.value)
    console.log(currentRevision.value in metadataByRevision.value)
    return currentRevision.value && metadataByRevision.value && !(currentRevision.value in metadataByRevision.value)
})

const currentMetadata = computed(() => {
    return metadataByRevision.value[currentRevision.value]
})

repositoryStore.setId(props.repositoryId)

const currentRevision = ref<string>(props.changesetRevision || "")
watch(repositoryChangesetRevisions, () => {
    const changesets = repositoryChangesetRevisions.value
    if (changesets && changesets.length > 0 && currentRevision.value == "") {
        currentRevision.value = changesets[changesets.length - 1]
    }
})

const readmes = ref<{ [key: string]: string | undefined }>({})
watch(
    () => props.changesetRevision,
    (newValue: RepositoryProps["changesetRevision"]) => {
        if (newValue && newValue != currentRevision.value) {
            currentRevision.value = newValue
        }
    }
)

watch(currentRevision, () => {
    if (currentRevision.value) {
        ToolShedApi()
            .GET("/api/repositories/{encoded_repository_id}/revisions/{changeset_revision}/readmes", {
                params: {
                    path: {
                        encoded_repository_id: props.repositoryId,
                        changeset_revision: currentRevision.value,
                    },
                },
            })
            .then((response) => {
                if (response.data) {
                    readmes.value = response.data
                } else {
                    readmes.value = {}
                }
            })
            .catch(notifyOnCatch)
    } else {
        readmes.value = {}
    }
})

const longDescription = computed(() => (repository.value?.long_description || repository.value?.description) as string)
const repositoryName = computed(() => repository.value?.name)
const repositoryOwner = computed(() => repository.value?.owner)
const deprecated = computed(() => repository.value?.deprecated || false)
const latestRevisionDownloadable = computed(() => repositoryInstallInfo.value?.metadata_info?.downloadable || false)
const tools = computed(() => currentMetadata.value?.tools || [])
const invalidTools = computed(() => currentMetadata.value?.invalid_tools || [])
const malicious = computed(() => currentMetadata.value?.malicious || false)
const canManage = computed(() => repositoryPermissions.value?.can_manage || false)
const canPush = computed(() => repositoryPermissions.value?.can_push || false)
</script>

<template>
    <q-page class="q-ma-lg">
        <loading-div v-if="loading" />
        <error-banner error="Failed to load repository" v-else-if="!repository"> </error-banner>
        <q-card v-else>
            <q-card-section horizontal class="row">
                <q-card-section class="bg-primary text-white col-grow">
                    <div class="text-h6">{{ repository.name }}</div>
                    <div class="text-subtitle">
                        <router-link
                            class="text-white"
                            style="text-decoration: none"
                            :to="`/repositories_by_owner/${repository.owner}`"
                            >{{ repository.owner }}</router-link
                        >
                    </div>
                </q-card-section>
                <q-card-section class="bg-primary">
                    <repository-explore :repository="repository" :current-revision="currentRevision" />
                    <repository-actions
                        :repository-id="repository.id"
                        :deprecated="deprecated"
                        @update="onUpdate"
                        @deprecate="onDeprecate"
                        @undeprecate="onUndeprecate"
                        v-if="canManage"
                    >
                    </repository-actions>
                    <repository-health
                        :last-updated="repository.update_time"
                        :installs="repository.times_downloaded"
                        :downloadable="latestRevisionDownloadable"
                    >
                    </repository-health>
                </q-card-section>
            </q-card-section>
            <q-card-section>
                <p class="description">
                    {{ longDescription }}
                </p>
                <repository-links :repository="repository" :current-revision="currentRevision" v-if="repository" />
            </q-card-section>
            <q-separator />
            <q-card-section>
                <InstallingHowto
                    v-if="repositoryName && repositoryOwner"
                    :repository-name="repositoryName"
                    :repository-owner="repositoryOwner"
                />
            </q-card-section>
            <q-separator />
            <q-card-section v-if="canManage">
                <manage-push-access :repository-id="repositoryId"> </manage-push-access>
            </q-card-section>
            <q-separator />
            <q-card-section v-if="empty">
                This repository is empty.
                <span v-if="canPush">
                    Check out the
                    <a :href="UPDATING_WITH_PLANEMO_URL">Planemo documentation on updating repositories</a>.
                </span>
            </q-card-section>
            <q-card-section v-else>
                <p v-if="repositoryMetadata">
                    <revision-select :revisions="repositoryMetadata" v-model="currentRevision">
                        <revision-actions
                            :repository-id="repositoryId"
                            :current-metadata="currentMetadata"
                            v-if="currentMetadata && canManage"
                            @update="onUpdate"
                        />
                    </revision-select>
                </p>
                <q-banner inline-actions rounded class="bg-negative text-white" v-if="isUnknownRevision">
                    <strong>The change log does not include revision {{ currentRevision }}.</strong>
                </q-banner>
                <div v-if="currentMetadata">
                    <q-banner inline-actions rounded class="bg-negative text-white" v-if="malicious">
                        <strong>This repository revision has been marked as malicious and cannot be installed.</strong>
                    </q-banner>
                    <p v-for="(content, key) of readmes" :key="key">
                        <span v-html="content"></span>
                    </p>
                    <!-- <span class="repository-select-label text-h6 q-mr-lg">Tools</span> -->
                    <q-list bordered class="rounded-borders" v-if="tools && tools.length > 0">
                        <!-- style="max-width: 600px"> -->
                        <q-item-label header>Tools</q-item-label>
                        <repository-tool
                            v-for="tool in tools"
                            :key="tool.id"
                            :tool="tool"
                            :trs-tool-id="trsToolId(tool)"
                            :changeset-revision="currentMetadata.changeset_revision"
                        ></repository-tool>
                    </q-list>

                    <q-list bordered class="rounded-borders q-mt-md" v-if="invalidTools && invalidTools.length > 0">
                        <q-item-label header>Invalid Tools</q-item-label>
                        <q-item v-for="invalidTool in invalidTools" :key="invalidTool">
                            <code>{{ invalidTool }}</code>
                        </q-item>
                    </q-list>
                </div>
            </q-card-section>
        </q-card>
    </q-page>
</template>
