<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { faCheck, faCircleQuestion, faXmark } from "@fortawesome/free-solid-svg-icons"
import type { components } from "@/schema"

type ChangesetMetadataStatus = components["schemas"]["ChangesetMetadataStatus"]

interface Props {
    changesets: ChangesetMetadataStatus[]
}
defineProps<Props>()

const columns = [
    {
        name: "revision",
        label: "Revision",
        field: (row: ChangesetMetadataStatus) => `${row.numeric_revision}:${row.changeset_revision.substring(0, 7)}`,
        align: "left" as const,
    },
    { name: "comparison_result", label: "Change Type", field: "comparison_result", align: "left" as const },
    { name: "record_operation", label: "Snapshot", field: "record_operation", align: "left" as const },
    { name: "tools", label: "Tools", field: "has_tools", align: "center" as const },
    { name: "error", label: "Error", field: "error", align: "left" as const },
]

// Display labels for comparison results (friendlier than raw API values)
const comparisonLabels: Record<string, string> = {
    initial: "First revision",
    equal: "Unchanged",
    subset: "Expanded",
    "not equal and not subset": "Modified",
    no_metadata: "Empty",
}

// Detailed tooltips explaining what each comparison result means
const comparisonTooltips: Record<string, string> = {
    initial: "First changeset with tools or dependencies - starting point for metadata tracking",
    equal: "Metadata identical to previous revision - no changes detected",
    subset: "New tools or dependencies added, nothing removed - changes accumulate until a breaking change triggers a snapshot",
    "not equal and not subset":
        "Tools or dependencies were removed or modified - previous revision was saved as an installable snapshot",
    no_metadata: "No tools or dependencies found in this changeset",
}
</script>

<template>
    <q-table
        :rows="changesets"
        :columns="columns"
        row-key="changeset_revision"
        dense
        flat
        :pagination="{ rowsPerPage: 0 }"
        hide-pagination
    >
        <template #header-cell-comparison_result="props">
            <q-th :props="props">
                {{ props.col.label }}
                <span class="q-ml-xs cursor-help">
                    <FontAwesomeIcon :icon="faCircleQuestion" style="font-size: 18px" />
                    <q-tooltip max-width="300px">
                        How this changeset's metadata changed compared to the previous revision. Snapshots are created
                        when tools are removed or modified, preserving installable history.
                    </q-tooltip>
                </span>
            </q-th>
        </template>
        <template #body-cell-comparison_result="props">
            <q-td :props="props">
                <span v-if="props.value" class="cursor-help">
                    {{ comparisonLabels[props.value] || props.value }}
                    <q-tooltip v-if="comparisonTooltips[props.value]" max-width="300px">
                        {{ comparisonTooltips[props.value] }}
                    </q-tooltip>
                </span>
                <span v-else class="text-grey">—</span>
            </q-td>
        </template>
        <template #header-cell-record_operation="props">
            <q-th :props="props">
                {{ props.col.label }}
                <span class="q-ml-xs cursor-help">
                    <FontAwesomeIcon :icon="faCircleQuestion" style="font-size: 18px" />
                    <q-tooltip max-width="300px">
                        Whether this revision was saved as an installable snapshot. "Created" means a new snapshot was
                        made; "updated" means an existing snapshot was refreshed.
                    </q-tooltip>
                </span>
            </q-th>
        </template>
        <template #body-cell-record_operation="props">
            <q-td :props="props">
                <span
                    v-if="props.value"
                    class="record-operation-badge"
                    :class="
                        props.value === 'created'
                            ? 'record-operation-badge--created'
                            : 'record-operation-badge--updated'
                    "
                >
                    {{ props.value }}
                </span>
                <span v-else class="text-grey">—</span>
            </q-td>
        </template>
        <template #body-cell-tools="props">
            <q-td :props="props">
                <FontAwesomeIcon
                    :icon="props.value ? faCheck : faXmark"
                    :class="props.value ? 'text-positive' : 'text-grey'"
                />
            </q-td>
        </template>
        <template #body-cell-error="props">
            <q-td :props="props">
                <span v-if="props.value" class="text-negative">{{ props.value }}</span>
            </q-td>
        </template>
    </q-table>
</template>

<style scoped>
.record-operation-badge {
    display: inline-block;
    padding: var(--spacing-1) var(--spacing-2);
    border-radius: var(--spacing-4);
    font-size: var(--font-size-small);
    color: var(--color-grey-100);
}

.record-operation-badge--created {
    background-color: var(--color-green-700);
}

.record-operation-badge--updated {
    background-color: var(--color-blue-700);
}
</style>
