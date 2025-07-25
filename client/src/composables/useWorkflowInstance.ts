import { computed, ref } from "vue";

import { useUserStore } from "@/stores/userStore";
import { useWorkflowStore } from "@/stores/workflowStore";
import { errorMessageAsString } from "@/utils/simple-error";

export function useWorkflowInstance(workflowId: string) {
    const workflowStore = useWorkflowStore();
    const workflow = computed(() => workflowStore.getStoredWorkflowByInstanceId(workflowId));
    const loading = ref(false);
    const error = ref<string | null>(null);

    const userStore = useUserStore();
    const owned = computed(() => workflow.value && userStore.matchesCurrentUsername(workflow.value.owner));

    async function getWorkflowInstance() {
        if (!workflow.value) {
            loading.value = true;
            try {
                await workflowStore.fetchWorkflowForInstanceId(workflowId);
            } catch (e) {
                error.value = errorMessageAsString(e);
            } finally {
                loading.value = false;
            }
        }
    }
    getWorkflowInstance();

    return { workflow, loading, error, owned };
}
