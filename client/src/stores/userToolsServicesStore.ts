import { defineStore, storeToRefs } from "pinia";
import { computed, readonly, ref, set } from "vue";

import { GalaxyApi, isRegisteredUser } from "@/api";
import type {
    CreateSourceCredentialsPayload,
    SelectCurrentGroupPayload,
    ServiceCredentialsGroup,
    ServiceCredentialsIdentifier,
    ServiceGroupPayload,
    UserSourceService,
} from "@/api/users";
import { useUserStore } from "@/stores/userStore";

export const SECRET_PLACEHOLDER = "********";

export const useUserToolsServicesStore = defineStore("userToolsServicesStore", () => {
    const userStore = useUserStore();
    const { currentUser } = storeToRefs(userStore);

    const userToolsServices = ref<Record<string, UserSourceService[]>>({});
    const userToolServiceGroups = ref<Record<string, ServiceCredentialsGroup>>({});

    const isBusy = ref(false);
    const busyMessage = ref<string>("");

    const userServicesExistForTool = computed(() => {
        return (toolId: string, toolVersion: string) => {
            const key = getKey(toolId, toolVersion);
            return userToolsServices.value[key];
        };
    });

    const userToolServicesFor = computed(() => (toolId: string, toolVersion: string) => {
        const key = getKey(toolId, toolVersion);
        return userToolsServices.value[key];
    });

    function getKey(toolId: string, toolVersion: string): string {
        const userId = ensureUserIsRegistered();
        return `${userId}-${toolId}-${toolVersion}`;
    }

    function updateUserToolServiceGroups(userSourceServices: UserSourceService[]) {
        for (const sourceService of userSourceServices) {
            for (const group of sourceService.groups) {
                userToolServiceGroups.value[group.id] = group;
            }
        }
    }

    function getToolService(
        toolId: string,
        toolVersion: string,
        serviceIdentifier: ServiceCredentialsIdentifier
    ): UserSourceService | undefined {
        const key = getKey(toolId, toolVersion);
        const service = userToolsServices.value[key]?.find(
            (service) => service.name === serviceIdentifier.name && service.version === serviceIdentifier.version
        );

        return service;
    }

    function updateUserToolServiceGroup(group: ServiceCredentialsGroup) {
        set(userToolServiceGroups.value, group.id, group);

        for (const key in userToolsServices.value) {
            const services = userToolsServices.value[key];
            if (services) {
                for (const service of services) {
                    const groupIndex = service.groups.findIndex((g) => g.id === group.id);
                    if (groupIndex !== -1) {
                        set(service.groups, groupIndex, group);
                        break;
                    }
                }
            }
        }
    }

    async function fetchAllUserToolServices(toolId: string, toolVersion: string): Promise<UserSourceService[]> {
        const userId = ensureUserIsRegistered();

        busyMessage.value = "Checking your credentials";
        isBusy.value = true;

        try {
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

            const key = getKey(toolId, toolVersion);

            if (error) {
                throw Error(`Failed to fetch user credentials for tool ${key}: ${error.err_msg}`);
            }

            set(userToolsServices.value, key, data);

            updateUserToolServiceGroups(data);

            return data;
        } finally {
            isBusy.value = false;
            busyMessage.value = "";
        }
    }

    async function createNewCredentialsGroupForTool(
        createSourceCredentialsPayload: CreateSourceCredentialsPayload
    ): Promise<ServiceCredentialsGroup> {
        const userId = ensureUserIsRegistered();

        busyMessage.value = "Creating your credentials";
        isBusy.value = true;

        try {
            const toolId = createSourceCredentialsPayload.source_id;
            const toolVersion = createSourceCredentialsPayload.source_version;

            const { data, error } = await GalaxyApi().POST("/api/users/{user_id}/credentials", {
                params: {
                    path: { user_id: userId },
                },
                body: {
                    source_id: toolId,
                    source_type: createSourceCredentialsPayload.source_type,
                    source_version: toolVersion,
                    service_credential: createSourceCredentialsPayload.service_credential,
                },
            });

            if (error) {
                const key = getKey(toolId, toolVersion);
                throw Error(`Failed to create new credentials group for tool ${key}: ${error.err_msg}`);
            }

            await fetchAllUserToolServices(toolId, toolVersion);

            return data;
        } finally {
            isBusy.value = false;
            busyMessage.value = "";
        }
    }

    async function updateUserCredentialsForTool(
        toolId: string,
        toolVersion: string,
        groupId: string,
        serviceGroupPayload: ServiceGroupPayload
    ): Promise<ServiceCredentialsGroup> {
        const userId = ensureUserIsRegistered();

        removeSecretPlaceholders(serviceGroupPayload);

        busyMessage.value = "Updating your credentials";
        isBusy.value = true;

        try {
            const { data, error } = await GalaxyApi().PUT("/api/users/{user_id}/credentials/group/{group_id}", {
                params: {
                    path: { user_id: userId, group_id: groupId },
                },
                body: serviceGroupPayload,
            });

            if (error) {
                const key = getKey(toolId, toolVersion);
                throw Error(`Failed to save user credentials ${groupId} for ${key} : ${error.err_msg}`);
            }

            updateUserToolServiceGroup(data);

            return data;
        } finally {
            isBusy.value = false;
            busyMessage.value = "";
        }
    }

    async function deleteCredentialsGroupForTool(
        toolId: string,
        toolVersion: string,
        serviceIdentifier: ServiceCredentialsIdentifier,
        groupId: string
    ): Promise<void> {
        const userId = ensureUserIsRegistered();
        const group = userToolServiceGroups.value[groupId];
        if (!group) {
            return;
        }

        const toolServicesId = getToolService(toolId, toolVersion, serviceIdentifier)?.id;
        if (!toolServicesId) {
            const key = getKey(toolId, toolVersion);
            throw new Error(`No service found for tool ${key}`);
        }

        busyMessage.value = "Updating your credentials";
        isBusy.value = true;

        try {
            const { error } = await GalaxyApi().DELETE(
                "/api/users/{user_id}/credentials/{user_credentials_id}/{group_id}",
                {
                    params: {
                        path: { user_id: userId, user_credentials_id: toolServicesId!, group_id: groupId },
                    },
                }
            );

            if (error) {
                const key = getKey(toolId, toolVersion);
                throw Error(`Failed to delete user credentials group for tool ${key}: ${error.err_msg}`);
            }
        } finally {
            isBusy.value = false;
            busyMessage.value = "";
        }
    }

    async function selectCurrentCredentialsGroupsForTool(
        toolId: string,
        toolVersion: string,
        serviceCredentials: SelectCurrentGroupPayload[]
    ) {
        const userId = ensureUserIsRegistered();

        busyMessage.value = "Selecting current credentials groups";
        isBusy.value = true;

        try {
            const { error } = await GalaxyApi().PUT("/api/users/{user_id}/credentials", {
                params: {
                    path: {
                        user_id: userId,
                    },
                },
                body: {
                    source_id: toolId,
                    source_type: "tool",
                    source_version: toolVersion,
                    service_credentials: serviceCredentials,
                },
            });

            if (error) {
                const key = getKey(toolId, toolVersion);
                throw new Error(`Failed to select current credentials groups for tool ${key}: ${error.err_msg}`);
            }

            await fetchAllUserToolServices(toolId, toolVersion);
        } finally {
            isBusy.value = false;
            busyMessage.value = "";
        }
    }

    function ensureUserIsRegistered(): string {
        if (!isRegisteredUser(currentUser.value)) {
            throw new Error("Only registered users can have tool credentials");
        }
        return currentUser.value.id;
    }

    function removeSecretPlaceholders(serviceGroupPayload: ServiceGroupPayload) {
        serviceGroupPayload.secrets.forEach((secret) => {
            if (secret.value === SECRET_PLACEHOLDER) {
                secret.value = null;
            }
        });
    }

    return {
        isBusy: readonly(isBusy),
        busyMessage: readonly(busyMessage),
        userToolsServices,
        userServicesExistForTool,
        userToolServicesFor,
        userToolServiceGroups,
        getToolService,
        fetchAllUserToolServices,
        createNewCredentialsGroupForTool,
        updateUserCredentialsForTool,
        deleteCredentialsGroupForTool,
        selectCurrentCredentialsGroupsForTool,
    };
});
