<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { faTriangleExclamation } from "@fortawesome/free-solid-svg-icons"
import { GAlert, GButton, GTab, GTabs } from "@galaxyproject/galaxy-ui"
import { ref, computed, nextTick } from "vue"
import { storeToRefs } from "pinia"
import { useRepositoryStore } from "@/stores"
import LoadingDiv from "@/components/LoadingDiv.vue"
import PageHeader from "@/components/PageHeader.vue"
import ErrorBanner from "@/components/ErrorBanner.vue"
import OverviewTab from "@/components/MetadataInspector/OverviewTab.vue"
import ToolHistoryTab from "@/components/MetadataInspector/ToolHistoryTab.vue"
import RevisionsTab from "@/components/MetadataInspector/RevisionsTab.vue"
import ResetMetadataTab from "@/components/MetadataInspector/ResetMetadataTab.vue"

interface Props {
    repositoryId: string
}
const props = defineProps<Props>()

const repositoryStore = useRepositoryStore()
const { loading, repository, repositoryMetadata, repositoryPermissions } = storeToRefs(repositoryStore)

repositoryStore.setId(props.repositoryId)

const canManage = computed(() => repositoryPermissions.value?.can_manage || false)
const activeTab = ref("revisions")

// GTabs selects by index, so map the named tabs onto it. Reset is last because it's conditional.
const tabNames = computed(() => {
    const names = ["revisions", "tool-history", "raw-json"]
    if (canManage.value) {
        names.push("reset")
    }
    return names
})
const activeTabIndex = computed(() => Math.max(0, tabNames.value.indexOf(activeTab.value)))

function onTabInput(index: number) {
    activeTab.value = tabNames.value[index] ?? "revisions"
}

const revisionCount = computed(() => {
    if (!repositoryMetadata.value) return 0
    return Object.keys(repositoryMetadata.value).length
})

// Count invalid tools across all revisions
const totalInvalidTools = computed(() => {
    if (!repositoryMetadata.value) return 0
    let count = 0
    for (const rev of Object.values(repositoryMetadata.value)) {
        count += rev.invalid_tools?.length || 0
    }
    return count
})

// Cross-tab navigation support
const expandRevision = ref<string | null>(null)

async function goToRevision(revision: string) {
    // RevisionsTab stays mounted across tab switches, so clear first to re-trigger its watcher
    // when the same revision is requested again after being collapsed.
    expandRevision.value = null
    await nextTick()
    expandRevision.value = revision
    activeTab.value = "revisions"
}

function onResetComplete() {
    // Refresh the repository data after reset
    repositoryStore.refresh()
}
</script>

<template>
    <div class="metadata-inspector-page">
        <loading-div v-if="loading" message="Loading metadata..." class="inspector-status" />
        <error-banner v-else-if="!repository" error="Failed to load repository" class="inspector-status" />
        <template v-else>
            <page-header title="Metadata Inspector">
                <template #eyebrow>
                    <router-link class="inspector-owner-link" :to="`/repositories_by_owner/${repository.owner}`">{{
                        repository.owner
                    }}</router-link>
                    /
                    <router-link :to="`/repositories/${repositoryId}`">{{ repository.name }}</router-link>
                </template>
            </page-header>
            <div class="inspector-body">
                <section class="inspector-card shed-card">
                    <!-- Invalid tools warning banner -->
                    <!-- A finding about the repository, not an event: announce it politely rather than as an alert -->
                    <GAlert v-if="totalInvalidTools > 0" variant="warning" role="status" class="invalid-tools-alert">
                        <FontAwesomeIcon :icon="faTriangleExclamation" />
                        <span class="invalid-tools-message"
                            >{{ totalInvalidTools }} invalid tool(s) found across revisions.</span
                        >
                        <GButton transparent @click="activeTab = 'revisions'">View in Revisions</GButton>
                    </GAlert>

                    <GTabs class="inspector-tabs" lazy :value="activeTabIndex" @input="onTabInput">
                        <GTab :title="`Revisions (${revisionCount})`">
                            <RevisionsTab :metadata="repositoryMetadata" :expand-revision="expandRevision" />
                        </GTab>
                        <GTab title="Tool History">
                            <ToolHistoryTab :metadata="repositoryMetadata" @goToRevision="goToRevision" />
                        </GTab>
                        <GTab title="Raw JSON">
                            <OverviewTab :metadata="repositoryMetadata" />
                        </GTab>
                        <GTab v-if="canManage" title="Reset Metadata">
                            <ResetMetadataTab :repository-id="repositoryId" @resetComplete="onResetComplete" />
                        </GTab>
                    </GTabs>
                </section>
            </div>
        </template>
    </div>
</template>

<style scoped>
.inspector-status {
    max-width: var(--shed-content-width);
    margin: 2rem auto;
    padding: 0 1.5rem;
}

.inspector-body {
    max-width: var(--shed-content-width);
    margin: 0 auto;
    padding: 1.75rem 1.5rem 3rem;
}

.inspector-card {
    overflow: hidden;
}

.invalid-tools-alert {
    display: flex;
    align-items: center;
    gap: var(--spacing-3);
    margin: 0;
    padding: var(--spacing-3) 1.25rem;
    background: var(--color-yellow-100);
    color: var(--color-yellow-900);
    border: none;
    border-bottom: 1px solid var(--color-yellow-300);
    border-radius: 0;
}

.invalid-tools-message {
    flex: 1;
}

.inspector-tabs :deep(.tab-content) {
    padding: 1.25rem;
}
</style>
