<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { faCheck, faCircleQuestion, faXmark } from "@fortawesome/free-solid-svg-icons"
import { GTable, GTooltip, type TableField } from "@galaxyproject/galaxy-ui"
import { ref } from "vue"
import type { components } from "@/schema"

type ChangesetMetadataStatus = components["schemas"]["ChangesetMetadataStatus"]

interface Props {
    changesets: ChangesetMetadataStatus[]
}
defineProps<Props>()

const fields: TableField[] = [
    {
        key: "revision",
        label: "Revision",
        formatter: (_value, _key, item: ChangesetMetadataStatus) =>
            `${item.numeric_revision}:${item.changeset_revision.substring(0, 7)}`,
    },
    { key: "comparison_result", label: "Change Type" },
    { key: "record_operation", label: "Snapshot" },
    { key: "has_tools", label: "Tools", align: "center" },
    { key: "error", label: "Error" },
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

// Single static instances per column header, so one template ref each is enough. The
// per-row comparison_result tooltip below can't share this pattern -- the table renders that
// slot once per row -- so it falls back to a native title attribute instead.
const comparisonHeaderHelpRef = ref<HTMLElement | null>(null)
const recordOperationHeaderHelpRef = ref<HTMLElement | null>(null)
</script>

<template>
    <GTable :items="changesets" :fields="fields" primary-key="changeset_revision" compact>
        <template #head(comparison_result)="{ field }">
            {{ field.label }}
            <span
                ref="comparisonHeaderHelpRef"
                class="header-help"
                tabindex="0"
                role="img"
                aria-label="About comparison results"
            >
                <FontAwesomeIcon :icon="faCircleQuestion" />
            </span>
            <GTooltip
                class="changeset-help-tooltip"
                :reference="comparisonHeaderHelpRef"
                text="How this changeset's metadata changed compared to the previous revision. Snapshots are created when tools are removed or modified, preserving installable history."
            />
        </template>
        <template #cell(comparison_result)="{ value }">
            <span v-if="value" class="comparison-result" :title="comparisonTooltips[value]">
                {{ comparisonLabels[value] || value }}
            </span>
            <span v-else class="no-value">—</span>
        </template>
        <template #head(record_operation)="{ field }">
            {{ field.label }}
            <span
                ref="recordOperationHeaderHelpRef"
                class="header-help"
                tabindex="0"
                role="img"
                aria-label="About record operations"
            >
                <FontAwesomeIcon :icon="faCircleQuestion" />
            </span>
            <GTooltip
                class="changeset-help-tooltip"
                :reference="recordOperationHeaderHelpRef"
                text='Whether this revision was saved as an installable snapshot. "Created" means a new snapshot was made; "updated" means an existing snapshot was refreshed.'
            />
        </template>
        <template #cell(record_operation)="{ value }">
            <span
                v-if="value"
                class="record-operation-badge"
                :class="value === 'created' ? 'record-operation-badge--created' : 'record-operation-badge--updated'"
            >
                {{ value }}
            </span>
            <span v-else class="no-value">—</span>
        </template>
        <template #cell(has_tools)="{ value }">
            <FontAwesomeIcon :icon="value ? faCheck : faXmark" :class="value ? 'has-tools' : 'no-value'" />
        </template>
        <template #cell(error)="{ value }">
            <span v-if="value" class="changeset-error">{{ value }}</span>
        </template>
    </GTable>
</template>

<style scoped>
.header-help {
    margin-left: var(--spacing-1);
    font-size: 1.1rem;
    cursor: help;
}

.comparison-result {
    cursor: help;
}

.no-value {
    color: var(--color-grey-500);
}

.has-tools {
    color: var(--color-green-700);
}

.changeset-error {
    color: var(--color-red-700);
}

/* Paragraph-length help reads as a block, as the q-tooltips did at 300px */
.changeset-help-tooltip {
    max-width: min(300px, calc(100vw - 2rem));
}

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
