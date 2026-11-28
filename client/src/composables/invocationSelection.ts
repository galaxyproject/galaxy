import { computed, inject, type InjectionKey, provide, type Ref, ref, watch } from "vue";
import { type LocationQuery, useRoute, useRouter } from "vue-router";

import type { WorkflowInvocationElementView } from "@/api/invocations";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import { useWorkflowStore } from "@/stores/workflowStore";

export type StepTab = "jobs" | "outputs" | "config";
export interface SelectionStep {
    id: number;
    label?: string | null;
}
export interface InvocationSelection {
    stepIndex: Ref<number | null>;
    stepTab: Ref<StepTab | undefined>;
    job: Ref<string | undefined>;
    output: Ref<string | undefined>;
}
const selectionKey: InjectionKey<InvocationSelection | undefined> = Symbol("invocation selection");
const selectionKeys = ["step_index", "step_number", "step_label", "step_tab", "job", "output", "success"];

export function queryString(value: LocationQuery[string] | undefined): string | undefined {
    return typeof value === "string" && value.length > 0 ? value : undefined;
}

/** Resolve explicit selectors in precedence order, without interpreting numeric labels as positions. */
export function resolveStep(query: LocationQuery, steps: SelectionStep[]): number | null {
    for (const key of ["step_index", "step_number", "step_label"] as const) {
        if (!(key in query)) {
            continue;
        }
        const value = queryString(query[key]);
        if (value === undefined) {
            return null;
        }
        if (key === "step_label") {
            const matches = steps.filter((step) => step.label === value);
            return matches.length === 1 ? matches[0]!.id : null;
        }
        if (!/^\d+$/.test(value)) {
            return null;
        }
        const index = Number(value) - (key === "step_number" ? 1 : 0);
        return Number.isSafeInteger(index) && steps.some((step) => step.id === index) ? index : null;
    }
    return null;
}

export function selectionQuery(
    query: LocationQuery,
    steps: SelectionStep[],
    selection: {
        stepIndex: number | null;
        stepTab?: StepTab;
        job?: string;
        output?: string;
    },
): LocationQuery {
    const result = { ...query };
    selectionKeys.forEach((key) => delete result[key]);
    const step = steps.find((step) => step.id === selection.stepIndex);
    if (step) {
        if (step.label && steps.filter((candidate) => candidate.label === step.label).length === 1) {
            result.step_label = step.label;
        } else {
            result.step_number = String(step.id + 1);
        }
        if (selection.stepTab) {
            result.step_tab = selection.stepTab;
        }
        if (selection.job) {
            result.job = selection.job;
        }
    }
    if (selection.output) {
        result.output = selection.output;
    }
    return result;
}

export function useInvocationSelection() {
    return inject(selectionKey, undefined);
}

/** Only the route component provides URL synchronization; embedded invocation views stay local. */
export function provideInvocationSelection(invocation: Ref<WorkflowInvocationElementView | null>, enabled: boolean) {
    if (!enabled) {
        provide(selectionKey, undefined);
        return;
    }
    const route = useRoute();
    const router = useRouter();
    const workflowStore = useWorkflowStore();
    const workflow = computed(() =>
        invocation.value ? workflowStore.getStoredWorkflowByInstanceId(invocation.value.workflow_id) : undefined,
    );
    const loadedSteps = ref<SelectionStep[] | null>(null);
    const steps = computed(() => loadedSteps.value ?? []);
    const stepIndex = computed({
        get: () => (invocation.value ? useWorkflowStateStore(`invocation-${invocation.value.id}`).activeNodeId : null),
        set: (index: number | null) => {
            if (invocation.value) {
                useWorkflowStateStore(`invocation-${invocation.value.id}`).activeNodeId = index;
            }
        },
    });
    const selectionView = computed(() => {
        const tab = route.path.split("/").slice(4).join("/");
        return !tab || tab === "steps";
    });
    const outputView = computed(() => route.path.endsWith("/outputs"));
    watch(
        [workflow, selectionView],
        async ([summary, inSelectionView], _previous, onCleanup) => {
            loadedSteps.value = null;
            if (!summary || !inSelectionView) {
                return;
            }
            let current = true;
            onCleanup(() => (current = false));
            try {
                // Graph/list loading shares this cache; full steps include labels before scheduling.
                const fullWorkflow: { steps: Record<string, SelectionStep> } | undefined =
                    await workflowStore.getFullWorkflowCached(summary.id, summary.version);
                if (current && fullWorkflow) {
                    loadedSteps.value = Object.values(fullWorkflow.steps);
                }
            } catch {
                // Graph/list loading displays the shared workflow request's error.
            }
        },
        { immediate: true },
    );
    const stepTab = ref<StepTab>();
    const job = ref<string>();
    const output = ref<string>();
    provide(selectionKey, { stepIndex, stepTab, job, output });

    watch(
        [() => route.query, loadedSteps],
        () => {
            if (selectionView.value && loadedSteps.value === null) {
                return;
            }
            const hasSelector = ["step_index", "step_number", "step_label"].some((key) => key in route.query);
            if (hasSelector && selectionView.value) {
                stepIndex.value = resolveStep(route.query, steps.value);
            }
            const tab = queryString(route.query.step_tab);
            stepTab.value = tab === "jobs" || tab === "outputs" || tab === "config" ? tab : undefined;
            job.value =
                selectionView.value && resolveStep(route.query, steps.value) !== null
                    ? queryString(route.query.job)
                    : undefined;
            output.value =
                outputView.value || resolveStep(route.query, steps.value) !== null
                    ? queryString(route.query.output)
                    : undefined;
            if (job.value) {
                stepTab.value = "jobs";
            } else if (output.value && selectionView.value && stepIndex.value !== null) {
                stepTab.value = "outputs";
            }
        },
        { immediate: true },
    );

    watch(
        stepIndex,
        (index, previous) => {
            // A graph/list navigation starts a fresh selection within that step.
            if (previous !== index && resolveStep(route.query, steps.value) !== index) {
                stepTab.value = undefined;
                job.value = undefined;
                output.value = undefined;
            }
        },
        { flush: "sync" },
    );
    watch(
        [stepIndex, stepTab, job, output, loadedSteps],
        () => {
            if (selectionView.value && loadedSteps.value === null) {
                return;
            }
            if (!selectionView.value && !outputView.value) {
                return;
            }
            const query = selectionQuery(route.query, steps.value, {
                stepIndex: selectionView.value ? stepIndex.value : null,
                stepTab: selectionView.value ? stepTab.value : undefined,
                job: selectionView.value ? job.value : undefined,
                output: output.value,
            });
            if (JSON.stringify(query) !== JSON.stringify(route.query)) {
                void router.replace({ path: route.path, query, hash: route.hash });
            }
        },
        { immediate: true, flush: "post" },
    );
}
