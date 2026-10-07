<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { faCircleExclamation } from "@fortawesome/free-solid-svg-icons"
import { GAlert } from "@galaxyproject/galaxy-ui"
import { computed, watch, ref } from "vue"
import { storeToRefs } from "pinia"
import { useRepositoryStore } from "@/stores"
import { hasBrowsableFiles, newestRevision } from "@/api"
import LoadingDiv from "@/components/LoadingDiv.vue"
import PageHeader from "@/components/PageHeader.vue"
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
    return currentRevision.value && metadataByRevision.value && !(currentRevision.value in metadataByRevision.value)
})

const currentMetadata = computed(() => {
    return metadataByRevision.value[currentRevision.value]
})

repositoryStore.setId(props.repositoryId)

const currentRevision = ref<string>(props.changesetRevision || "")
watch(
    () => newestRevision(repositoryMetadata.value),
    (newest) => {
        if (newest && currentRevision.value == "") {
            currentRevision.value = newest
        }
    },
)

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

// The header carries the one-line description; the about card only repeats it when there is more to say
const longDescription = computed(() => {
    const long = repository.value?.long_description
    return long && long !== repository.value?.description ? long : ""
})
const hasReadmes = computed(() => Object.keys(readmes.value).length > 0)
const repositoryName = computed(() => repository.value?.name)
const repositoryOwner = computed(() => repository.value?.owner)
const deprecated = computed(() => repository.value?.deprecated || false)
const latestRevisionDownloadable = computed(() => repositoryInstallInfo.value?.metadata_info?.downloadable || false)
const tools = computed(() => currentMetadata.value?.tools || [])
const invalidTools = computed(() => currentMetadata.value?.invalid_tools || [])
const malicious = computed(() => currentMetadata.value?.malicious || false)
const browsableRevision = computed(() =>
    currentMetadata.value && hasBrowsableFiles(currentMetadata.value) ? currentRevision.value : null,
)
const canManage = computed(() => repositoryPermissions.value?.can_manage || false)
const canPush = computed(() => repositoryPermissions.value?.can_push || false)
</script>

<template>
    <div class="repository-page">
        <loading-div v-if="loading" class="repository-status" />
        <error-banner error="Failed to load repository" v-else-if="!repository" class="repository-status">
        </error-banner>
        <template v-else>
            <page-header :title="repository.name" :subtitle="repository.description">
                <template #eyebrow>
                    <router-link class="repository-owner-link" :to="`/repositories_by_owner/${repository.owner}`">{{
                        repository.owner
                    }}</router-link>
                </template>
                <template #meta>
                    <repository-health
                        :last-updated="repository.update_time"
                        :installs="repository.times_downloaded"
                        :downloadable="latestRevisionDownloadable"
                    />
                </template>
                <template #actions>
                    <div class="repository-header-actions">
                        <repository-explore :repository="repository" :browsable-revision="browsableRevision" />
                        <repository-actions
                            :repository-id="repository.id"
                            :deprecated="deprecated"
                            @update="onUpdate"
                            @deprecate="onDeprecate"
                            @undeprecate="onUndeprecate"
                            v-if="canManage"
                        >
                        </repository-actions>
                    </div>
                </template>
            </page-header>

            <div class="repository-body">
                <div class="repository-main">
                    <GAlert v-if="deprecated" variant="warning" class="repository-alert">
                        <strong>This repository has been deprecated.</strong>
                    </GAlert>

                    <section class="repository-card shed-card" v-if="empty">
                        <div class="shed-card-body">
                            This repository is empty.
                            <span v-if="canPush">
                                Check out the
                                <a :href="UPDATING_WITH_PLANEMO_URL">Planemo documentation on updating repositories</a>.
                            </span>
                        </div>
                    </section>
                    <template v-else>
                        <section class="repository-card shed-card">
                            <div v-if="repositoryMetadata" class="repository-revision-bar">
                                <revision-select :revisions="repositoryMetadata" v-model="currentRevision">
                                    <revision-actions
                                        :repository-id="repositoryId"
                                        :current-metadata="currentMetadata"
                                        v-if="currentMetadata && canManage"
                                        @update="onUpdate"
                                    />
                                </revision-select>
                            </div>
                            <div
                                class="shed-card-body repository-revision-alerts"
                                v-if="isUnknownRevision || malicious"
                            >
                                <GAlert v-if="isUnknownRevision" variant="danger">
                                    <strong>The change log does not include revision {{ currentRevision }}.</strong>
                                </GAlert>
                                <GAlert v-if="currentMetadata && malicious" variant="danger">
                                    <strong
                                        >This repository revision has been marked as malicious and cannot be
                                        installed.</strong
                                    >
                                </GAlert>
                            </div>
                            <template v-if="currentMetadata">
                                <div class="repository-tools" v-if="tools && tools.length > 0">
                                    <h2 class="repository-list-heading">
                                        Tools <span class="repository-list-count">{{ tools.length }}</span>
                                    </h2>
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
                                <p v-else class="shed-card-body repository-no-tools shed-muted">
                                    This revision does not contain any valid tools.
                                </p>
                            </template>
                        </section>

                        <section
                            class="repository-card repository-invalid-tools shed-card"
                            v-if="currentMetadata && invalidTools && invalidTools.length > 0"
                        >
                            <h2 class="repository-list-heading">
                                Invalid Tools <span class="repository-list-count">{{ invalidTools.length }}</span>
                            </h2>
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
                        </section>
                    </template>

                    <section
                        class="repository-card shed-card"
                        v-if="longDescription || (currentMetadata && hasReadmes)"
                    >
                        <div class="shed-card-body">
                            <h2 class="shed-section-title">About</h2>
                            <p v-if="longDescription" class="description">{{ longDescription }}</p>
                            <template v-if="currentMetadata">
                                <div v-for="(content, key) of readmes" :key="key" class="repository-readme-wrapper">
                                    <span class="repository-readme" v-html="content"></span>
                                </div>
                            </template>
                        </div>
                    </section>
                </div>

                <aside class="repository-aside">
                    <section class="repository-card shed-card">
                        <div class="shed-card-body">
                            <InstallingHowto
                                v-if="repositoryName && repositoryOwner"
                                :repository-name="repositoryName"
                                :repository-owner="repositoryOwner"
                            />
                        </div>
                    </section>
                    <section class="repository-card shed-card">
                        <div class="shed-card-body">
                            <h2 class="shed-section-title">Links</h2>
                            <repository-links :repository="repository" :current-revision="currentRevision" />
                        </div>
                    </section>
                    <section class="repository-card shed-card" v-if="canManage">
                        <div class="shed-card-body">
                            <manage-push-access :repository-id="repositoryId"> </manage-push-access>
                        </div>
                    </section>
                </aside>
            </div>
        </template>
    </div>
</template>

<style scoped>
.repository-status {
    max-width: var(--shed-content-width);
    margin: 2rem auto;
    padding: 0 1.5rem;
}

.repository-owner-link {
    color: inherit;
}

.repository-header-actions {
    display: flex;
    align-items: center;
}

/* Round menu toggles read as glass buttons on the dark header */
.repository-header-actions :deep(.action-menu-toggle) {
    color: #fff;
    background-color: rgba(255, 255, 255, 0.12);
    box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.2);
}

.repository-header-actions :deep(.action-menu-toggle:hover),
.repository-header-actions :deep(.action-menu-toggle[aria-expanded="true"]) {
    color: var(--color-galaxy-dark);
    background-color: var(--shed-gold);
}

.repository-body {
    display: grid;
    gap: 1.5rem;
    max-width: var(--shed-content-width);
    margin: 0 auto;
    padding: 1.75rem 1.5rem 3rem;
}

@media (min-width: 1024px) {
    .repository-body {
        grid-template-columns: minmax(0, 1fr) 22rem;
        align-items: start;
    }

    .repository-aside {
        position: sticky;
        top: calc(var(--shed-masthead-height) + 1rem);
    }
}

@media (max-width: 599px) {
    .repository-body {
        padding: 1.25rem 1rem 2rem;
    }
}

.repository-main,
.repository-aside {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
    min-width: 0;
}

.repository-card {
    overflow: hidden;
}

.repository-alert {
    margin: 0;
}

.repository-revision-bar {
    padding: 0.85rem 1.25rem;
    background: color-mix(in srgb, var(--shed-page-bg) 55%, white);
    border-bottom: 1px solid var(--shed-border-subtle);
}

.repository-revision-alerts {
    padding-bottom: 0;
}

.repository-no-tools {
    margin: 0;
}

.repository-list-heading {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin: 0;
    padding: 1rem 1.25rem 0.5rem;
    font-size: 1.05rem;
    font-weight: 700;
}

.repository-list-count {
    padding: 0 0.5rem;
    font-size: 0.75rem;
    line-height: 1.6;
    color: var(--shed-muted);
    background: var(--color-ebony-clay-50, #dfe2ea);
    border-radius: 999px;
}

.repository-tools-list,
.repository-invalid-tools-list {
    margin: 0;
    padding: 0 0 0.25rem;
    list-style: none;
}

.repository-invalid-tools {
    border-left: 4px solid var(--color-red-500);
}

.invalid-tool-item {
    padding: 0.75rem 1.25rem;
}

.invalid-tool-item + .invalid-tool-item {
    border-top: 1px solid var(--shed-border-subtle);
}

.invalid-tool-icon {
    margin-right: 0.4rem;
    color: var(--color-red-600);
}

.invalid-tool-message {
    margin-top: 0.3rem;
    color: var(--shed-muted);
    font-size: 0.88rem;
}

.description {
    margin: 0 0 1rem;
    white-space: pre-line;
}

/* Plain-text READMEs arrive with every space as &nbsp;, so long lines can't wrap -- scroll them */
.repository-readme-wrapper {
    overflow-x: auto;
}

.repository-readme-wrapper + .repository-readme-wrapper {
    margin-top: 1rem;
}
</style>
