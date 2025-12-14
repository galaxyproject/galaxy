<script setup lang="ts">
import { ref, computed } from "vue"
import { storeToRefs } from "pinia"
import { useRepositoryStore } from "@/stores"
import LoadingDiv from "@/components/LoadingDiv.vue"
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
const activeTab = ref("overview")

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

function goToRevision(revision: string) {
    expandRevision.value = revision
    activeTab.value = "revisions"
}

function onResetComplete() {
    // Refresh the repository data after reset
    repositoryStore.refresh()
}
</script>

<template>
    <q-page class="q-ma-lg">
        <loading-div v-if="loading" message="Loading metadata..." />
        <error-banner v-else-if="!repository" error="Failed to load repository" />
        <q-card v-else>
            <q-card-section class="bg-primary text-white">
                <div class="text-h6">{{ repository.name }} – <em>Metadata Inspector</em></div>
                <div class="text-subtitle">
                    <router-link
                        class="text-white"
                        style="text-decoration: none"
                        :to="`/repositories_by_owner/${repository.owner}`"
                    >
                        {{ repository.owner }}
                    </router-link>
                </div>
            </q-card-section>

            <!-- Invalid tools warning banner -->
            <q-banner v-if="totalInvalidTools > 0" class="bg-warning text-white">
                <template #avatar>
                    <q-icon name="sym_r_warning" />
                </template>
                {{ totalInvalidTools }} invalid tool(s) found across revisions.
                <template #action>
                    <q-btn flat label="View in Revisions" @click="activeTab = 'revisions'" />
                </template>
            </q-banner>

            <q-tabs v-model="activeTab" class="text-primary" align="left">
                <q-tab name="overview" label="Overview" />
                <q-tab name="tool-history" label="Tool History" />
                <q-tab name="revisions" :label="`Revisions (${revisionCount})`" />
                <q-tab name="reset" label="Reset Metadata" v-if="canManage" />
            </q-tabs>

            <q-separator />

            <q-tab-panels v-model="activeTab">
                <q-tab-panel name="overview">
                    <OverviewTab :metadata="repositoryMetadata" />
                </q-tab-panel>
                <q-tab-panel name="tool-history">
                    <ToolHistoryTab :metadata="repositoryMetadata" @goToRevision="goToRevision" />
                </q-tab-panel>
                <q-tab-panel name="revisions">
                    <RevisionsTab :metadata="repositoryMetadata" :expand-revision="expandRevision" />
                </q-tab-panel>
                <q-tab-panel name="reset" v-if="canManage">
                    <ResetMetadataTab :repository-id="repositoryId" @resetComplete="onResetComplete" />
                </q-tab-panel>
            </q-tab-panels>
        </q-card>
    </q-page>
</template>
