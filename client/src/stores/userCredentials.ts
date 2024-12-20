import { ref, set } from "vue";

import { GalaxyApi } from "@/api";
import type { CreateSourceCredentialsPayload, UserCredentials } from "@/api/users";

import { defineScopedStore } from "./scopedStore";

export const useUserCredentialsStore = defineScopedStore("userCredentialsStore", (currentUserId: string) => {
    const userCredentialsForTools = ref<Record<string, UserCredentials[]>>({});

    function getKey(toolId: string): string {
        const userId = ensureUserIsRegistered();
        return `${userId}-${toolId}`;
    }

    function getAllUserCredentialsForTool(toolId: string): UserCredentials[] | undefined {
        ensureUserIsRegistered();
        return userCredentialsForTools.value[toolId];
    }

    async function fetchAllUserCredentialsForTool(toolId: string): Promise<UserCredentials[]> {
        const userId = ensureUserIsRegistered();

        const { data, error } = await GalaxyApi().GET("/api/users/{user_id}/credentials", {
            params: {
                path: { user_id: userId },
                query: {
                    source_type: "tool",
                    source_id: toolId,
                },
            },
        });

        if (error) {
            throw Error(`Failed to fetch user credentials for tool ${toolId}: ${error.err_msg}`);
        }

        const key = getKey(toolId);
        set(userCredentialsForTools.value, key, data);
        return data;
    }

    async function saveUserCredentialsForTool(
        providedCredentials: CreateSourceCredentialsPayload
    ): Promise<UserCredentials[]> {
        const userId = ensureUserIsRegistered();
        const toolId = providedCredentials.source_id;

        const { data, error } = await GalaxyApi().POST("/api/users/{user_id}/credentials", {
            params: {
                path: { user_id: userId },
            },
            body: providedCredentials,
        });

        if (error) {
            throw Error(`Failed to save user credentials for tool ${toolId}: ${error.err_msg}`);
        }

        const key = getKey(toolId);
        set(userCredentialsForTools.value, key, data);
        return data;
    }

    function ensureUserIsRegistered(): string {
        if (currentUserId === "anonymous") {
            throw new Error("Only registered users can have tool credentials");
        }
        return currentUserId;
    }

    return {
        getAllUserCredentialsForTool,
        fetchAllUserCredentialsForTool,
        saveUserCredentialsForTool,
    };
});
