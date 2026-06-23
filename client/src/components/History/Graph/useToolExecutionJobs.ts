import { type Ref, ref, watch } from "vue";

import { GalaxyApi } from "@/api";
import type { components } from "@/api/schema";

type ExecutionJob = components["schemas"]["ToolRequestJobReference"];

/**
 * Loads the jobs produced by a single tool execution (tool_request).
 * Refetches when the input id changes. Race-safe via the watcher's
 * cancel-on-rerun semantics.
 */
export function useToolExecutionJobs(toolExecutionId: Ref<string>) {
    const jobs = ref<ExecutionJob[]>([]);
    const loading = ref(false);
    const error = ref<string | null>(null);

    watch(
        toolExecutionId,
        async (id) => {
            jobs.value = [];
            error.value = null;
            if (!id) {
                return;
            }
            loading.value = true;
            try {
                const { data, error: apiError } = await GalaxyApi().GET("/api/tool_requests/{id}", {
                    params: { path: { id } },
                });
                if (apiError) {
                    error.value = "Failed to load tool execution details.";
                } else if (data.jobs && data.jobs.length > 0) {
                    jobs.value = data.jobs;
                } else {
                    error.value = "No job associated with this tool execution.";
                }
            } catch (e) {
                error.value = "Failed to load tool execution details.";
            } finally {
                loading.value = false;
            }
        },
        { immediate: true },
    );

    return { jobs, loading, error };
}
