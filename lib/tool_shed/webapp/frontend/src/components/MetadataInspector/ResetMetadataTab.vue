<script setup lang="ts">
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
        emit("resetComplete")
    } catch (e) {
        notifyOnCatch(e)
    } finally {
        loading.value = false
    }
}

function clearPreview() {
    previewResult.value = null
}
</script>

<template>
    <div>
        <!-- Initial state -->
        <q-banner v-if="!previewResult" class="bg-blue-1 q-mb-md">
            <template #avatar>
                <q-icon name="sym_r_info" color="primary" />
            </template>
            <div><strong>Reset metadata</strong> regenerates all revision metadata from repository contents.</div>
            <div class="q-mt-sm text-caption">
                Use cases:
                <ul class="q-mb-none">
                    <li>Fix corrupted tool_config paths after migration</li>
                    <li>Refresh metadata after tool shed code updates</li>
                    <li>Repair missing or incomplete metadata</li>
                </ul>
            </div>
            <template #action>
                <q-btn color="primary" label="Preview Changes" @click="runPreview" :loading="loading" />
            </template>
        </q-banner>

        <!-- Results -->
        <div v-if="previewResult">
            <q-card class="q-mb-md">
                <q-card-section>
                    <div class="row items-center justify-between">
                        <div>
                            <span class="text-weight-bold">
                                {{ previewResult.dry_run ? "Preview Results" : "Reset Complete" }}
                            </span>
                            <q-chip
                                :color="previewResult.status === 'ok' ? 'positive' : 'warning'"
                                size="sm"
                                class="q-ml-sm"
                            >
                                {{ previewResult.status }}
                            </q-chip>
                            <span v-if="previewResult.dry_run" class="text-caption q-ml-sm">(dry run)</span>
                        </div>
                        <div>
                            <q-btn
                                v-if="previewResult.dry_run"
                                color="primary"
                                label="Apply Now"
                                @click="applyReset"
                                :loading="loading"
                            />
                            <q-btn flat label="New Preview" @click="clearPreview" class="q-ml-sm" :disable="loading" />
                        </div>
                    </div>
                </q-card-section>
            </q-card>

            <!-- View mode toggle -->
            <q-btn-toggle
                v-model="viewMode"
                :options="[
                    { value: 'table', label: 'Summary Table' },
                    { value: 'diff', label: 'JSON Diff' },
                ]"
                class="q-mb-md"
            />

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
