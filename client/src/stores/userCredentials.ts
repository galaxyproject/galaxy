import { ref, set } from "vue";

import { GalaxyApi } from "@/api";
import type { CreateSourceCredentialsPayload, UserCredentials } from "@/api/users";

import { defineScopedStore } from "./scopedStore";

export const SECRET_PLACEHOLDER = "********";

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

        removeSecretPlaceholders(providedCredentials);

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

    async function deleteCredentialsGroupForTool(toolId: string, service_reference: string, groupName: string): Promise<void> {
        const userId = ensureUserIsRegistered();
        const key = getKey(toolId);
        const credentials = userCredentialsForTools.value[key];

        if (credentials) {
            const serviceCredentials = credentials.find((credential) => credential.service_reference === service_reference);
            if (!serviceCredentials) {
                throw new Error(`No credentials found for service reference ${service_reference}`);
            }
            const group = serviceCredentials.groups[groupName];
            if (!group) {
                throw new Error(`No group found for name ${groupName}`);
            }
            const { error } = await GalaxyApi().DELETE(
                "/api/users/{user_id}/credentials/{user_credentials_id}/{group_id}",
                {
                    params: {
                        path: { user_id: userId, user_credentials_id: serviceCredentials.id, group_id: group.id },
                    },
                }
            );

            if (error) {
                throw Error(`Failed to delete user credentials group for tool ${toolId}: ${error.err_msg}`);
            }
            // Remove the group from the credentials
            const updatedCredentials = credentials.map((credential) => {
                if (credential.id === service_reference) {
                    delete credential.groups[groupName];
                }
                return credential;
            });
            set(userCredentialsForTools.value, key, updatedCredentials);
        }
    }

    function ensureUserIsRegistered(): string {
        if (currentUserId === "anonymous") {
            throw new Error("Only registered users can have tool credentials");
        }
        return currentUserId;
    }

    function removeSecretPlaceholders(providedCredentials: CreateSourceCredentialsPayload) {
        providedCredentials.credentials.forEach((credential) => {
            credential.groups.forEach((group) => {
                group.secrets.forEach((secret) => {
                    if (secret.value === SECRET_PLACEHOLDER) {
                        secret.value = null;
                    }
                });
            });
        });
    }

    return {
        getAllUserCredentialsForTool,
        fetchAllUserCredentialsForTool,
        saveUserCredentialsForTool,
        deleteCredentialsGroupForTool,
    };
});
