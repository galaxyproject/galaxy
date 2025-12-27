import type { Ref } from "vue";
import { ref, watch } from "vue";

import { isWorkflowInvocationElementView } from "@/api/invocations";
import { useInvocationStore } from "@/stores/invocationStore";
import { useWorkflowStore } from "@/stores/workflowStore";
import { errorMessageAsString } from "@/utils/simple-error";

export interface EnrichedStepInfo {
    workflowStepId: number; // Step order_index
    orderIndex: number; // Same as workflowStepId for clarity
    label: string; // "Step {orderIndex + 1}" or enriched label with step name/tool
    stepType?: string; // "tool", "subworkflow", etc.
    invocationStepId?: string; // Invocation step ID for navigation
    subworkflowInvocationId?: string | null; // For navigating to subworkflow (can be null)
    parentInvocationId?: string; // If this step is in a subworkflow, the parent invocation ID
    isFinalStep?: boolean; // True if this is the failing step
    subworkflowData?: {
        // If this is a subworkflow step
        invocationId: string;
        workflowId: string;
        steps: Record<number, unknown>; // Subworkflow step definitions keyed by order_index
    };
}

interface WorkflowStep {
    type: string;
    label?: string;
    tool_id?: string;
    [key: string]: unknown;
}

/**
 * Generate a descriptive label for a workflow step
 */
function generateStepLabel(orderIndex: number, workflowStep: WorkflowStep): string {
    let label = `Step ${orderIndex + 1}`;
    if (workflowStep) {
        // Try to get label from the workflow step
        if ("label" in workflowStep && workflowStep.label) {
            label = `${orderIndex + 1}:${workflowStep.label}`;
        } else if (workflowStep.type === "tool" && "tool_id" in workflowStep && workflowStep.tool_id) {
            // Extract tool name from tool_id (e.g., "toolshed.../owner/name/tool" -> "tool")
            const toolName = workflowStep.tool_id.split("/").pop() || workflowStep.tool_id;
            label = `${orderIndex + 1}:${toolName}`;
        } else if (workflowStep.type === "subworkflow") {
            label = `${orderIndex + 1}:subworkflow`;
        }
    }
    return label;
}

/**
 * Composable for fetching enriched step data for workflow invocation error messages.
 *
 * This composable takes an invocation ID and arrays of step order indices and eagerly fetches
 * the necessary invocation and workflow data to properly display step information in error messages.
 *
 * @param invocationId - The workflow invocation ID
 * @param pathStepOrderIndices - Array of step order indices from workflow_step_id_path
 * @param finalStepOrderIndex - The failing step order index from workflow_step_id
 * @returns Object containing stepData array, loading state, and error message
 */
export function useInvocationMessageStepData(
    invocationId: Ref<string>,
    pathStepOrderIndices: Ref<number[]>,
    finalStepOrderIndex?: Ref<number | undefined>,
) {
    const invocationStore = useInvocationStore();
    const workflowStore = useWorkflowStore();

    const stepData = ref<EnrichedStepInfo[]>([]);
    const loading = ref(false);
    const error = ref<string>();

    // Track the last fetched parameters to avoid duplicate fetches
    let lastFetchedKey = "";

    async function fetchStepData() {
        if (!invocationId.value) {
            stepData.value = [];
            return;
        }

        // Create a unique key for this fetch to deduplicate requests
        const fetchKey = `${invocationId.value}:${JSON.stringify(pathStepOrderIndices.value)}:${finalStepOrderIndex?.value}`;
        if (fetchKey === lastFetchedKey) {
            // Already fetched this exact data, skip
            return;
        }
        lastFetchedKey = fetchKey;

        loading.value = true;
        error.value = undefined;

        try {
            // 1. Fetch parent invocation (uses cache if available)
            const invocation = await invocationStore.fetchInvocationById({ id: invocationId.value });

            if (!invocation) {
                throw new Error(`Invocation ${invocationId.value} not found`);
            }

            // Check if invocation has the detailed view (with steps)
            if (!isWorkflowInvocationElementView(invocation)) {
                throw new Error(`Invocation ${invocationId.value} does not have step details. This should not happen.`);
            }

            // 2. Fetch parent workflow definition
            // First get the workflow by instance ID to get the stored workflow ID
            await workflowStore.fetchWorkflowForInstanceIdCached(invocation.workflow_id);
            const storedWorkflowId = workflowStore.getStoredWorkflowIdByInstanceId(invocation.workflow_id);

            if (!storedWorkflowId) {
                throw new Error(`Could not find stored workflow ID for instance ${invocation.workflow_id}`);
            }

            // Now fetch the full workflow using the stored workflow ID
            const workflow = await workflowStore.getFullWorkflowCached(storedWorkflowId);

            if (!workflow) {
                throw new Error(`Workflow ${storedWorkflowId} not found`);
            }

            const enrichedSteps: EnrichedStepInfo[] = [];

            // 3. Process each step in the path (EAGER FETCHING with nested navigation)
            // The path represents nested subworkflows: each element navigates one level deeper
            // e.g., [1, 1] means: parent step 1 (subworkflow) -> that subworkflow's step 1

            let currentWorkflow = workflow;
            let currentInvocation = invocation;

            for (let i = 0; i < pathStepOrderIndices.value.length; i++) {
                const orderIndex = pathStepOrderIndices.value[i];

                // Type guard: ensure orderIndex is a valid number
                if (orderIndex === undefined || typeof orderIndex !== "number") {
                    console.warn(`Invalid order_index at path level ${i}: ${orderIndex}`);
                    continue;
                }

                // Look up step in the current workflow level
                const workflowStep = currentWorkflow.steps[orderIndex] as WorkflowStep | undefined;
                if (!workflowStep) {
                    console.warn(`Step with order_index ${orderIndex} not found in workflow at path level ${i}`);
                    continue;
                }

                // Get invocation step from current invocation level
                const invocationStep = currentInvocation.steps[orderIndex];

                // Build basic step info with descriptive label
                const stepInfo: EnrichedStepInfo = {
                    workflowStepId: orderIndex,
                    orderIndex: orderIndex,
                    label: generateStepLabel(orderIndex, workflowStep),
                    stepType: workflowStep.type,
                    invocationStepId: invocationStep?.id,
                    subworkflowInvocationId: invocationStep?.subworkflow_invocation_id,
                };

                // EAGER FETCH: If this is a subworkflow, fetch its invocation data for the next level
                if (workflowStep.type === "subworkflow" && invocationStep?.subworkflow_invocation_id) {
                    try {
                        const subInvocation = await invocationStore.fetchInvocationById({
                            id: invocationStep.subworkflow_invocation_id,
                        });

                        if (subInvocation && isWorkflowInvocationElementView(subInvocation)) {
                            // Get the stored workflow ID for the subworkflow
                            await workflowStore.fetchWorkflowForInstanceIdCached(subInvocation.workflow_id);
                            const subStoredWorkflowId = workflowStore.getStoredWorkflowIdByInstanceId(
                                subInvocation.workflow_id,
                            );

                            if (subStoredWorkflowId) {
                                const subWorkflow = await workflowStore.getFullWorkflowCached(subStoredWorkflowId);

                                if (subWorkflow) {
                                    stepInfo.subworkflowData = {
                                        invocationId: subInvocation.id,
                                        workflowId: subInvocation.workflow_id,
                                        steps: subWorkflow.steps,
                                    };

                                    // Navigate into the subworkflow for the next iteration
                                    currentWorkflow = subWorkflow;
                                    currentInvocation = subInvocation;
                                }
                            }
                        }
                    } catch (subError) {
                        console.warn(
                            `Failed to fetch subworkflow invocation ${invocationStep.subworkflow_invocation_id}:`,
                            subError,
                        );
                        // Continue processing even if subworkflow fetch fails
                    }
                }

                enrichedSteps.push(stepInfo);
            }

            // 4. Process the final failing step if provided
            // The final step is in the currentWorkflow/currentInvocation (which may be a subworkflow)
            if (finalStepOrderIndex?.value !== undefined) {
                const finalStepIndex = finalStepOrderIndex.value;
                const workflowStep = currentWorkflow.steps[finalStepIndex] as WorkflowStep | undefined;
                const invocationStep = currentInvocation.steps[finalStepIndex];

                if (workflowStep) {
                    enrichedSteps.push({
                        workflowStepId: finalStepIndex,
                        orderIndex: finalStepIndex,
                        label: generateStepLabel(finalStepIndex, workflowStep),
                        stepType: workflowStep.type,
                        invocationStepId: invocationStep?.id,
                        // If currentInvocation is different from the parent invocation, set parentInvocationId
                        parentInvocationId: currentInvocation.id !== invocation.id ? currentInvocation.id : undefined,
                        isFinalStep: true,
                    });
                }
            }

            stepData.value = enrichedSteps;
        } catch (e) {
            error.value = errorMessageAsString(e);
            stepData.value = [];
        } finally {
            loading.value = false;
        }
    }

    // Auto-fetch when inputs change
    // Note: We don't use deep: true because we handle deduplication manually via fetchKey
    watch([invocationId, pathStepOrderIndices, finalStepOrderIndex], fetchStepData, { immediate: true });

    return { stepData, loading, error };
}
