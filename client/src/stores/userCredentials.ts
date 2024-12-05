import { defineStore } from "pinia";
import { ref } from "vue";

import { isRegisteredUser } from "@/api";
import type { ToolCredentialsDefinition, UserCredentials } from "@/api/users";
import { useUserStore } from "@/stores/userStore";

const SECRET_PLACEHOLDER = "************";

export const useUserCredentialsStore = defineStore("userCredentialsStore", () => {
    const userCredentialsForTools = ref<Record<string, UserCredentials[]>>({});

    const userStore = useUserStore();

    function getAllUserCredentialsForTool(toolId: string): UserCredentials[] | undefined {
        ensureUserIsRegistered();
        return userCredentialsForTools.value[toolId];
    }

    async function fetchAllUserCredentialsForTool(
        toolId: string,
        toolCredentialsDefinitions: ToolCredentialsDefinition[]
    ): Promise<UserCredentials[]> {
        ensureUserIsRegistered();

        //TODO: Implement this. Simulate for now
        await new Promise((resolve) => setTimeout(resolve, 1000));
        const simulatedUserCredentials = [];
        for (const credentials of toolCredentialsDefinitions) {
            const fetchedCredentials = {
                ...credentials,
                secrets: credentials.secrets.map((secret) => ({
                    ...secret,
                    alreadySet: false,
                    value: SECRET_PLACEHOLDER, //This value is never set for real
                })),
                variables: credentials.variables.map((variable) => ({ ...variable })),
            };
            simulatedUserCredentials.push(fetchedCredentials);
        }
        userCredentialsForTools.value[toolId] = simulatedUserCredentials;
        return simulatedUserCredentials;
    }

    async function saveUserCredentialsForTool(
        toolId: string,
        userCredentials: UserCredentials[]
    ): Promise<UserCredentials[]> {
        ensureUserIsRegistered();
        //TODO: Implement this. Simulate for now
        await new Promise((resolve) => setTimeout(resolve, 1000));

        const savedUserCredentials: UserCredentials[] = [];
        for (const credentials of userCredentials) {
            const savedCredentials = {
                ...credentials,
                secrets: credentials.secrets.map((secret) => ({
                    ...secret,
                    alreadySet: true,
                    value: SECRET_PLACEHOLDER,
                })),
                variables: credentials.variables.map((variable) => ({ ...variable, value: variable.value ?? "test" })),
            };
            savedUserCredentials.push(savedCredentials);
        }
        userCredentialsForTools.value[toolId] = savedUserCredentials;
        return savedUserCredentials;
    }

    function ensureUserIsRegistered() {
        if (!isRegisteredUser(userStore.currentUser)) {
            throw new Error("Only registered users can have tool credentials");
        }
    }

    return {
        getAllUserCredentialsForTool,
        fetchAllUserCredentialsForTool,
        saveUserCredentialsForTool,
    };
});
