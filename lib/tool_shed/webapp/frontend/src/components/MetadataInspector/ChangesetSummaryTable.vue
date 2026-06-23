<script setup lang="ts">
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
                <q-icon name="sym_r_help" size="xs" class="q-ml-xs cursor-help">
                    <q-tooltip max-width="300px">
                        How this changeset's metadata changed compared to the previous revision. Snapshots are created
                        when tools are removed or modified, preserving installable history.
                    </q-tooltip>
                </q-icon>
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
                <q-icon name="sym_r_help" size="xs" class="q-ml-xs cursor-help">
                    <q-tooltip max-width="300px">
                        Whether this revision was saved as an installable snapshot. "Created" means a new snapshot was
                        made; "updated" means an existing snapshot was refreshed.
                    </q-tooltip>
                </q-icon>
            </q-th>
        </template>
        <template #body-cell-record_operation="props">
            <q-td :props="props">
                <q-chip
                    v-if="props.value"
                    :color="props.value === 'created' ? 'positive' : 'info'"
                    text-color="white"
                    size="sm"
                >
                    {{ props.value }}
                </q-chip>
                <span v-else class="text-grey">—</span>
            </q-td>
        </template>
        <template #body-cell-tools="props">
            <q-td :props="props">
                <q-icon
                    :name="props.value ? 'sym_r_check' : 'sym_r_close'"
                    :color="props.value ? 'positive' : 'grey'"
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
