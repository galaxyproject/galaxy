import { useWorkflowStore } from "@/stores/workflowStore";
import { computed, ref } from "vue";

export function useWorkflowInstance(workflowId: string) {
    const workflowStore = useWorkflowStore();
    const workflow = computed(() => workflowStore.getStoredWorkflowByInstanceId(workflowId));
    const loading = ref(false);

    async function getWorkflowInstance() {
        if (!workflow.value) {
            loading.value = true;
            try {
                await workflowStore.fetchWorkflowForInstanceId(workflowId);
            } catch (e) {
                console.error("unable to fetch workflow \n", e);
            } finally {
                loading.value = false;
            }
        }
    }
    getWorkflowInstance();

    return { workflow, loading };
}
