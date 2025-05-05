import { defineStore } from "pinia";
import { ref } from "vue";

import { GalaxyApi } from "@/api";
import { errorMessageAsString } from "@/utils/simple-error";

interface ClaimState {
    workflowId: string | null;
    instance: boolean;
    requestState: { [key: string]: unknown } | null;
    errorMessage: string | null;
}

export const useWorkflowLandingStore = defineStore("workflowLanding", () => {
    const claimState = ref<ClaimState>({
        workflowId: null,
        instance: false,
        requestState: null,
        errorMessage: null,
    });

    async function claimWorkflow(uuid: string, isPublic: boolean, secret?: string) {
        let claim;
        let claimError;

        if (isPublic) {
            const { data, error } = await GalaxyApi().GET("/api/workflow_landings/{uuid}", {
                params: {
                    path: { uuid },
                },
            });
            claim = data;
            claimError = error;
        } else {
            const { data, error } = await GalaxyApi().POST("/api/workflow_landings/{uuid}/claim", {
                params: {
                    path: { uuid },
                },
                body: {
                    client_secret: secret,
                },
            });
            claim = data;
            claimError = error;
        }

        if (claim) {
            claimState.value = {
                workflowId: claim.workflow_id,
                instance: claim.workflow_target_type === "workflow",
                requestState: claim.request_state,
                errorMessage: null,
            };
        } else {
            claimState.value = {
                workflowId: null,
                instance: false,
                requestState: null,
                errorMessage: errorMessageAsString(claimError),
            };
        }
    }

    return {
        claimState,
        claimWorkflow,
    };
});
