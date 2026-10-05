<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { faCircleExclamation } from "@fortawesome/free-solid-svg-icons"
import { GAlert, GHeading } from "@galaxyproject/galaxy-ui"
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
    },
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
    },
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
    <div class="repository-page">
        <loading-div v-if="loading" />
        <error-banner error="Failed to load repository" v-else-if="!repository"> </error-banner>
        <section class="repository-card" v-else>
            <div class="repository-header-row">
                <div class="repository-header repository-header-main">
                    <GHeading h1 size="md" class="repository-name">{{ repository.name }}</GHeading>
                    <div class="repository-owner">
                        <router-link class="repository-owner-link" :to="`/repositories_by_owner/${repository.owner}`">{{
                            repository.owner
                        }}</router-link>
                    </div>
                </div>
                <div class="repository-header repository-header-actions">
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
                </div>
            </div>
            <div class="repository-section">
                <p class="description">
                    {{ longDescription }}
                </p>
                <repository-links :repository="repository" :current-revision="currentRevision" v-if="repository" />
            </div>
            <hr />
            <div class="repository-section">
                <InstallingHowto
                    v-if="repositoryName && repositoryOwner"
                    :repository-name="repositoryName"
                    :repository-owner="repositoryOwner"
                />
            </div>
            <hr />
            <div class="repository-section" v-if="canManage">
                <manage-push-access :repository-id="repositoryId"> </manage-push-access>
            </div>
            <hr />
            <div class="repository-section" v-if="empty">
                This repository is empty.
                <span v-if="canPush">
                    Check out the
                    <a :href="UPDATING_WITH_PLANEMO_URL">Planemo documentation on updating repositories</a>.
                </span>
            </div>
            <div class="repository-section" v-else>
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
                <GAlert v-if="isUnknownRevision" variant="danger">
                    <strong>The change log does not include revision {{ currentRevision }}.</strong>
                </GAlert>
                <div v-if="currentMetadata">
                    <GAlert v-if="malicious" variant="danger">
                        <strong>This repository revision has been marked as malicious and cannot be installed.</strong>
                    </GAlert>
                    <p v-for="(content, key) of readmes" :key="key">
                        <span class="repository-readme" v-html="content"></span>
                    </p>
                    <div class="repository-tools" v-if="tools && tools.length > 0">
                        <h2 class="repository-list-heading">Tools</h2>
                        <ul class="repository-tools-list">
                            <repository-tool
                                v-for="tool in tools"
                                :key="tool.id"
                                :tool="tool"
                                :trs-tool-id="trsToolId(tool)"
                                :changeset-revision="currentMetadata.changeset_revision"
                            ></repository-tool>
                        </ul>
                    </div>

                    <div class="repository-invalid-tools" v-if="invalidTools && invalidTools.length > 0">
                        <h2 class="repository-list-heading">Invalid Tools</h2>
                        <ul class="repository-invalid-tools-list">
                            <li
                                class="invalid-tool-item"
                                v-for="invalidTool in invalidTools"
                                :key="invalidTool.tool_config"
                            >
                                <div class="invalid-tool-name">
                                    <FontAwesomeIcon :icon="faCircleExclamation" class="invalid-tool-icon" />
                                    <code>{{ invalidTool.tool_config }}</code>
                                </div>
                                <div class="invalid-tool-message" v-if="invalidTool.error_message">
                                    {{ invalidTool.error_message }}
                                </div>
                            </li>
                        </ul>
                    </div>
                </div>
            </div>
        </section>
    </div>
</template>

<style scoped>
.repository-page {
    margin: var(--spacing-6);
}

.repository-card {
    background: #fff;
    border: 1px solid var(--color-grey-300);
    border-radius: 0.25rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.repository-header-row {
    display: flex;
    flex-wrap: wrap;
}

.repository-header {
    padding: var(--spacing-4);
    background: var(--color-galaxy-primary);
    color: #fff;
}

.repository-header-main {
    flex: 1 1 auto;
}

.repository-name {
    margin: 0;
    color: inherit;
}

.repository-owner {
    margin-top: var(--spacing-1);
}

.repository-owner-link {
    color: #fff;
    text-decoration: none;
}

.repository-owner-link:hover,
.repository-owner-link:focus-visible {
    text-decoration: underline;
}

.repository-section {
    padding: var(--spacing-4);
}

.repository-list-heading {
    margin: 0;
    padding: var(--spacing-4) var(--spacing-4) var(--spacing-2);
    color: var(--color-grey-600);
    font-size: var(--font-size-medium);
    font-weight: 600;
}

.repository-tools,
.repository-invalid-tools {
    border: 1px solid var(--color-grey-300);
    border-radius: 0.25rem;
}

.repository-invalid-tools {
    margin-top: var(--spacing-4);
}

.repository-tools-list,
.repository-invalid-tools-list {
    margin: 0;
    padding: 0 0 var(--spacing-2);
    list-style: none;
}

.invalid-tool-item {
    padding: var(--spacing-2) var(--spacing-4);
}

.invalid-tool-icon {
    margin-right: var(--spacing-1);
    color: var(--color-red-600);
}

.invalid-tool-message {
    margin-top: var(--spacing-1);
    color: var(--color-grey-600);
    font-size: var(--font-size-small);
}
</style>
