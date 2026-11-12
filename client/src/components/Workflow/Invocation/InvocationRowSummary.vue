<script setup lang="ts">
import type { WorkflowInvocation } from "@/api/invocations";

import CopyToClipboard from "@/components/CopyToClipboard.vue";
import UtcDate from "@/components/UtcDate.vue";

const props = defineProps<{
    /** The invocation in the expanded row */
    invocation: WorkflowInvocation;
}>();
</script>

<template>
    <div class="invocation-row-summary d-flex flex-column" :data-invocation-id="props.invocation.id">
        <table class="tabletip invocation-row-summary-table">
            <tbody>
                <tr>
                    <td>Invocation ID</td>
                    <td>
                        <code>{{ props.invocation.id }}</code>
                        <CopyToClipboard
                            :text="props.invocation.id"
                            message="Invocation ID copied to clipboard"
                            title="Copy invocation ID"
                            size="small" />
                    </td>
                </tr>
                <tr>
                    <td>Invoked</td>
                    <td><UtcDate :date="props.invocation.create_time" mode="pretty" /></td>
                </tr>
                <tr>
                    <td>Last updated</td>
                    <td><UtcDate :date="props.invocation.update_time" mode="elapsed" /></td>
                </tr>
            </tbody>
        </table>

        <div class="invocation-row-summary-actions d-flex flex-wrap flex-gapx-1 flex-gapy-1 mt-auto pt-2">
            <slot name="actions" />
        </div>
    </div>
</template>

<style scoped lang="scss">
.invocation-row-summary {
    padding: 0.75rem;
    border: 1px solid var(--color-grey-300);
    border-radius: 0.25rem;
    background: var(--color-grey-100);
}

// the same label / value table look as `JobInformation`
.invocation-row-summary-table {
    tr {
        // the expanded row sits in GTable, whose striping would reach these rows
        background-color: transparent;

        td {
            padding: 0.25rem 0.5rem;
            vertical-align: top;
            border-bottom: none;
        }

        &:hover td {
            background-color: var(--color-blue-100);
        }

        td:first-child {
            font-size: 0.78rem;
            font-weight: 700;
            white-space: nowrap;
            color: var(--color-grey-600);
        }

        td:last-child {
            color: var(--color-blue-700);
        }
    }
}
</style>
