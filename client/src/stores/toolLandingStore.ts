import { defineStore } from "pinia";
import { ref } from "vue";

import { GalaxyApi } from "@/api";
import { errorMessageAsString } from "@/utils/simple-error";

interface ClaimState {
    toolId: string | null;
    toolVersion: string | null;
    requestState: { [key: string]: unknown } | null;
    errorMessage: string | null;
}

export const useToolLandingStore = defineStore("toolLanding", () => {
    const claimState = ref<ClaimState>({
        toolId: null,
        toolVersion: null,
        requestState: null,
        errorMessage: null,
    });

    async function claimTool(uuid: string, isPublic: boolean, secret?: string) {
        let claim;
        let claimError;

        if (isPublic) {
            const { data, error } = await GalaxyApi().GET("/api/tool_landings/{uuid}", {
                params: {
                    path: { uuid },
                },
            });
            claim = data;
            claimError = error;
        } else {
            const { data, error } = await GalaxyApi().POST("/api/tool_landings/{uuid}/claim", {
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
                toolId: claim.tool_id,
                toolVersion: claim.tool_version ?? null,
                requestState: claim.request_state ?? null,
                errorMessage: null,
            };
        } else {
            claimState.value = {
                toolId: null,
                toolVersion: null,
                requestState: null,
                errorMessage: errorMessageAsString(claimError),
            };
        }
    }

    return {
        claimState,
        claimTool,
    };
});
