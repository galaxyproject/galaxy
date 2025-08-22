import { defineStore, storeToRefs } from "pinia";
import { computed, ref, set } from "vue";

import { GalaxyApi, isRegisteredUser } from "@/api";
import type { CreateSourceCredentialsPayload, ServiceCredentialsIdentifier, UserCredentials } from "@/api/users";
import { useUserStore } from "@/stores/userStore";

export const SECRET_PLACEHOLDER = "********";

export const useUserCredentialsStore = defineStore("userCredentialsStore", () => {
    const userStore = useUserStore();
    const { currentUser } = storeToRefs(userStore);

    const userCredentialsForTools = ref<Record<string, UserCredentials[]>>({});

    const userToolCredentials = computed(() => (toolId: string, toolVersion: string) => {
        return userCredentialsForTools.value[getKey(toolId, toolVersion)];
    });

    function getKey(toolId: string, toolVersion: string): string {
        const userId = ensureUserIsRegistered();
        return `${userId}-${toolId}-${toolVersion}`;
    }

    function getAllUserCredentialsForTool(toolId: string, toolVersion: string): UserCredentials[] | undefined {
        ensureUserIsRegistered();
        return userCredentialsForTools.value[getKey(toolId, toolVersion)];
    }

    async function fetchAllUserCredentialsForTool(toolId: string, toolVersion: string): Promise<UserCredentials[]> {
        const userId = ensureUserIsRegistered();

        const { data, error } = await GalaxyApi().GET("/api/users/{user_id}/credentials", {
            params: {
                path: { user_id: userId },
                query: {
                    source_version: toolVersion,
                    source_type: "tool",
                    source_id: toolId,
                },
            },
        });

        if (error) {
            throw Error(`Failed to fetch user credentials for tool ${toolId}: ${error.err_msg}`);
        }

        const key = getKey(toolId, toolVersion);
        set(userCredentialsForTools.value, key, data);
        return data;
    }

    async function saveUserCredentialsForTool(
        providedCredentials: CreateSourceCredentialsPayload
    ): Promise<UserCredentials[]> {
        const userId = ensureUserIsRegistered();
        const toolId = providedCredentials.source_id;
        const toolVersion = providedCredentials.source_version;

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

        const key = getKey(toolId, toolVersion);
        set(userCredentialsForTools.value, key, data);
        return data;
    }

    async function deleteCredentialsGroupForTool(
        toolId: string,
        toolVersion: string,
        serviceIdentifier: ServiceCredentialsIdentifier,
        groupName: string
    ): Promise<void> {
        const userId = ensureUserIsRegistered();
        const key = getKey(toolId, toolVersion);
        const credentials = userCredentialsForTools.value[key];

        if (credentials) {
            const serviceCredentials = credentials.find(
                (credential) =>
                    credential.name === serviceIdentifier.name && credential.version === serviceIdentifier.version
            );
            if (!serviceCredentials) {
                return;
            }
            const group = serviceCredentials.groups[groupName];
            if (!group) {
                // Group does not exist, nothing to delete
                return;
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
                if (credential.name === serviceIdentifier.name && credential.version === serviceIdentifier.version) {
                    const updatedCredential = { ...credential };
                    delete updatedCredential.groups[groupName];
                    return updatedCredential;
                }
                return credential;
            });
            set(userCredentialsForTools.value, key, updatedCredentials);
        }
    }

    function ensureUserIsRegistered(): string {
        if (!isRegisteredUser(currentUser.value)) {
            throw new Error("Only registered users can have tool credentials");
        }
        return currentUser.value.id;
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
        userCredentialsForTools,
        userToolCredentials,
        getAllUserCredentialsForTool,
        fetchAllUserCredentialsForTool,
        saveUserCredentialsForTool,
        deleteCredentialsGroupForTool,
    };
});
