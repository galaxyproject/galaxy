<script setup lang="ts">
import { computed } from "vue";

import { isWorkflowInvocationElementView, type WorkflowInvocation } from "@/api/invocations";
import { useInvocationProgress } from "@/components/WorkflowInvocationState/useInvocationProgress";
import { useInvocationStore } from "@/stores/invocationStore";

import CopyToClipboard from "@/components/CopyToClipboard.vue";
import ProgressBar from "@/components/ProgressBar.vue";
import UtcDate from "@/components/UtcDate.vue";

const props = defineProps<{
    /** The invocation in the expanded row */
    invocation: WorkflowInvocation;
}>();

const invocationStore = useInvocationStore();

/** The invocation's full view, which the expanded row's `WorkflowInvocationState` loads and polls */
const invocationDetails = computed(() => {
    const stored = invocationStore.getInvocationById(props.invocation.id);
    return isWorkflowInvocationElementView(stored) ? stored : null;
});

const { invocationState, jobCount, stateCounts, stepStates, stepCount } = useInvocationProgress(
    () => props.invocation.id,
    invocationDetails,
);

/** Scheduling stopped early, shown as a failed steps bar */
const schedulingStopped = computed(() => ["cancelled", "failed"].includes(invocationState.value));

const stepsText = computed(() =>
    schedulingStopped.value
        ? `Scheduling ${invocationState.value}`
        : `${stepStates.value.scheduled || 0} of ${stepCount.value} scheduled`,
);

/** The job counts worth showing, in the order the full page's jobs bar uses */
const jobCounts = computed(() => {
    const counts = stateCounts.value;
    if (!counts) {
        return [];
    }
    return [
        { label: "ok", count: counts.okCount, failed: false },
        { label: "running", count: counts.runningCount, failed: false },
        { label: "failed", count: counts.errorCount, failed: true },
        { label: "waiting", count: counts.newCount, failed: false },
    ].filter(({ count }) => count > 0);
});
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
                <tr v-if="stepCount">
                    <td>Steps</td>
                    <td>
                        <ProgressBar
                            v-if="schedulingStopped"
                            class="invocation-row-summary-progress"
                            :error-count="1" />
                        <ProgressBar
                            v-else
                            class="invocation-row-summary-progress"
                            :total="stepCount"
                            :ok-count="stepStates.scheduled" />
                        <small>{{ stepsText }}</small>
                    </td>
                </tr>
                <tr v-if="stateCounts">
                    <td>Jobs</td>
                    <td>
                        <ProgressBar
                            class="invocation-row-summary-progress"
                            :total="jobCount"
                            :ok-count="stateCounts.okCount"
                            :running-count="stateCounts.runningCount"
                            :new-count="stateCounts.newCount"
                            :error-count="stateCounts.errorCount" />
                        <small v-if="jobCounts.length">
                            <template v-for="({ label, count, failed }, index) in jobCounts" :key="label">
                                <span v-if="index"> · </span>
                                <span :class="{ 'text-danger': failed }">{{ count }} {{ label }}</span>
                            </template>
                        </small>
                        <small v-else>No jobs</small>
                    </td>
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

    // Make the progress bar slim
    .invocation-row-summary-progress {
        :deep(.progress) {
            height: 0.5rem;
        }
    }
}
</style>
