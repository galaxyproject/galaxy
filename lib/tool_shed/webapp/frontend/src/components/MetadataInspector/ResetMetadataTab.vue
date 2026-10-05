<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { faCircleInfo } from "@fortawesome/free-solid-svg-icons"
import { GAlert, GButton, GButtonGroup } from "@galaxyproject/galaxy-ui"
import { ref } from "vue"
import { ToolShedApi } from "@/schema"
import type { components } from "@/schema"
import { notifyOnCatch } from "@/util"
import ChangesetSummaryTable from "./ChangesetSummaryTable.vue"
import JsonDiffViewer from "./JsonDiffViewer.vue"

type ResetMetadataResponse = components["schemas"]["ResetMetadataOnRepositoryResponse"]

interface Props {
    repositoryId: string
}
const props = defineProps<Props>()
const emit = defineEmits<{
    (e: "resetComplete"): void
}>()

const loading = ref(false)
const previewResult = ref<ResetMetadataResponse | null>(null)
const viewMode = ref<"table" | "diff">("table")

async function runPreview() {
    loading.value = true
    previewResult.value = null
    try {
        const { data } = await ToolShedApi().POST("/api/repositories/{encoded_repository_id}/reset_metadata", {
            params: {
                path: { encoded_repository_id: props.repositoryId },
                query: { dry_run: true, verbose: true },
            },
        })
        previewResult.value = data ?? null
    } catch (e) {
        notifyOnCatch(e)
    } finally {
        loading.value = false
    }
}

async function applyReset() {
    loading.value = true
    try {
        const { data } = await ToolShedApi().POST("/api/repositories/{encoded_repository_id}/reset_metadata", {
            params: {
                path: { encoded_repository_id: props.repositoryId },
                query: { dry_run: false, verbose: true },
            },
        })
        previewResult.value = data ?? null
        // Don't auto-refresh - let user see results first, they can click "New Preview" to refresh
    } catch (e) {
        notifyOnCatch(e)
    } finally {
        loading.value = false
    }
}

function clearPreview() {
    // If we had completed a non-dry-run reset, refresh parent data
    if (previewResult.value && !previewResult.value.dry_run) {
        emit("resetComplete")
    }
    previewResult.value = null
}
</script>

<template>
    <div>
        <!-- Initial state -->
        <GAlert v-if="!previewResult" variant="info" class="q-mb-md">
            <div class="reset-metadata-banner">
                <FontAwesomeIcon :icon="faCircleInfo" class="text-primary" />
                <div class="reset-metadata-banner-content">
                    <div>
                        <strong>Reset metadata</strong> regenerates all revision metadata from repository contents.
                    </div>
                    <div class="q-mt-sm text-caption">
                        Use cases:
                        <ul class="q-mb-none">
                            <li>Fix corrupted tool_config paths after migration</li>
                            <li>Refresh metadata after tool shed code updates</li>
                            <li>Repair missing or incomplete metadata</li>
                        </ul>
                    </div>
                </div>
                <GButton color="blue" :loading="loading" @click="runPreview">Preview Changes</GButton>
            </div>
        </GAlert>

        <!-- Results -->
        <div v-if="previewResult">
            <q-card class="q-mb-md">
                <q-card-section>
                    <div class="row items-center justify-between">
                        <div>
                            <span class="text-weight-bold">
                                {{ previewResult.dry_run ? "Preview Results" : "Reset Complete" }}
                            </span>
                            <span
                                class="reset-status-chip q-ml-sm"
                                :class="
                                    previewResult.status === 'ok'
                                        ? 'reset-status-chip--ok'
                                        : 'reset-status-chip--warning'
                                "
                            >
                                {{ previewResult.status }}
                            </span>
                            <span v-if="previewResult.dry_run" class="text-caption q-ml-sm">(dry run)</span>
                        </div>
                        <div>
                            <GButton v-if="previewResult.dry_run" color="blue" :loading="loading" @click="applyReset">
                                Apply Now
                            </GButton>
                            <GButton transparent class="q-ml-sm" :disabled="loading" @click="clearPreview">
                                New Preview
                            </GButton>
                        </div>
                    </div>
                </q-card-section>
            </q-card>

            <!-- View mode toggle -->
            <GButtonGroup class="q-mb-md">
                <GButton
                    outline
                    :pressed="viewMode === 'table'"
                    :aria-pressed="viewMode === 'table'"
                    @click="viewMode = 'table'"
                >
                    Summary Table
                </GButton>
                <GButton
                    outline
                    :pressed="viewMode === 'diff'"
                    :aria-pressed="viewMode === 'diff'"
                    @click="viewMode = 'diff'"
                >
                    JSON Diff
                </GButton>
            </GButtonGroup>

            <!-- Summary Table View -->
            <ChangesetSummaryTable
                v-if="viewMode === 'table' && previewResult.changeset_details"
                :changesets="previewResult.changeset_details"
            />
            <div v-else-if="viewMode === 'table'" class="text-grey">No changeset details available</div>

            <!-- JSON Diff View -->
            <div v-if="viewMode === 'diff'">
                <JsonDiffViewer
                    v-if="previewResult.repository_metadata_before && previewResult.repository_metadata_after"
                    :before="previewResult.repository_metadata_before"
                    :after="previewResult.repository_metadata_after"
                />
                <div v-else class="text-grey">No diff data available</div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.reset-metadata-banner {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-start;
    gap: var(--spacing-3);
}

.reset-metadata-banner-content {
    flex: 1 1 auto;
}

.reset-status-chip {
    display: inline-block;
    padding: var(--spacing-1) var(--spacing-2);
    border-radius: var(--spacing-4);
    font-size: var(--font-size-small);
}

.reset-status-chip--ok {
    background-color: var(--color-green-200);
    color: var(--color-green-900);
}

.reset-status-chip--warning {
    background-color: var(--color-orange-200);
    color: var(--color-orange-900);
}
</style>
