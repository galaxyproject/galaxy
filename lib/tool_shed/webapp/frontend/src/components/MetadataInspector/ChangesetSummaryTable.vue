<script setup lang="ts">
import type { components } from "@/schema"

type ChangesetMetadataStatus = components["schemas"]["ChangesetMetadataStatus"]

interface Props {
    changesets: ChangesetMetadataStatus[]
}
defineProps<Props>()

const actionColors: Record<string, string> = {
    created: "positive",
    updated: "info",
    unchanged: "grey",
    skipped: "grey-6",
    error: "negative",
}

const actionIcons: Record<string, string> = {
    created: "sym_r_add_circle",
    updated: "sym_r_edit",
    unchanged: "sym_r_check",
    skipped: "sym_r_skip_next",
    error: "sym_r_error",
}

const columns = [
    {
        name: "revision",
        label: "Revision",
        field: (row: ChangesetMetadataStatus) => `${row.numeric_revision}:${row.changeset_revision.substring(0, 7)}`,
        align: "left" as const,
    },
    { name: "action", label: "Action", field: "action", align: "center" as const },
    { name: "tools", label: "Tools", field: "has_tools", align: "center" as const },
    { name: "error", label: "Error", field: "error", align: "left" as const },
]
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
        <template #body-cell-action="props">
            <q-td :props="props">
                <q-chip
                    :color="actionColors[props.value] || 'grey'"
                    :icon="actionIcons[props.value]"
                    text-color="white"
                    size="sm"
                >
                    {{ props.value }}
                </q-chip>
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
