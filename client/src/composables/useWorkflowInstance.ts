import { useWorkflowStore } from "@/stores/workflowStore";
import { ref } from "vue";

export function useWorkflowInstance(workflowId: string) {
    const workflowStore = useWorkflowStore();
    const workflow = ref(workflowStore.getWorkflowByInstanceId(workflowId));
    const loading = ref(false);

    async function getWorkflowInstance() {
        if (!workflow.value) {
            loading.value = true;
            try {
                await workflowStore.fetchWorkflowForInstanceId(workflowId);
            } catch (e) {
                loading.value = false;
                console.error("unable to fetch workflow \n", e);
            }
        }
    }
    getWorkflowInstance();

    return { workflow, loading };
}
