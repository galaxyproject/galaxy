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

const actionDescriptions: Record<string, string> = {
    created: "New metadata record created for this changeset",
    updated: "Existing metadata record was updated",
    unchanged: "Metadata matches existing record, no changes",
    skipped: "No metadata to record (equal, subset, or initial)",
    error: "Failed to process this changeset",
}

const headerDescriptions: Record<string, string> = {
    revision: "Mercurial changeset revision number and hash",
    action: "What happened to metadata for this changeset",
    tools: "Whether this changeset contains tool definitions",
    error: "Errors encountered processing this changeset",
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
        <template #header-cell="props">
            <q-th :props="props">
                {{ props.col.label }}
                <q-tooltip v-if="headerDescriptions[props.col.name]">
                    {{ headerDescriptions[props.col.name] }}
                </q-tooltip>
            </q-th>
        </template>
        <template #body-cell-action="props">
            <q-td :props="props">
                <q-chip
                    :color="actionColors[props.value] || 'grey'"
                    :icon="actionIcons[props.value]"
                    text-color="white"
                    size="sm"
                >
                    {{ props.value }}
                    <q-tooltip v-if="actionDescriptions[props.value]">
                        {{ actionDescriptions[props.value] }}
                    </q-tooltip>
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
