import { computed, type Ref, ref, watch } from "vue";

import { useToolStore } from "@/stores/toolStore";
import { errorMessageAsString } from "@/utils/simple-error";

/** Resolves whether the tool that ran a job can be rerun (`is_workflow_compatible`), fetching the
 * tool if it isn't cached yet. A failed fetch (e.g. the tool is no longer installed) settles to
 * "cannot rerun" with an `error` instead of leaving the check loading forever. */
export function useRerunnableTool(toolId: Ref<string | undefined>) {
    const toolStore = useToolStore();
    const error = ref<string | null>(null);

    const tool = computed(() => (toolId.value ? toolStore.getToolForId(toolId.value) : undefined));
    const loading = computed(() => !!toolId.value && !tool.value && !error.value);
    const canRerun = computed(() => !!tool.value?.is_workflow_compatible);

    watch(
        toolId,
        async (id, _oldId, onCleanup) => {
            // Ignore a failure from a fetch started for an earlier tool id, even if the id has since
            // changed back to the same tool (with a newer fetch still pending).
            let cancelled = false;
            onCleanup(() => (cancelled = true));
            error.value = null;
            if (!id || toolStore.getToolForId(id)) {
                return;
            }
            try {
                await toolStore.fetchToolForId(id);
            } catch (e) {
                if (!cancelled) {
                    error.value = errorMessageAsString(e);
                }
            }
        },
        { immediate: true },
    );

    return { canRerun, loading, error };
}
