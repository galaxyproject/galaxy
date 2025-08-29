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

export interface CurrentGroupIds {
    [serviceId: string]: string | undefined;
}

export interface ToolsCurrentGroupIds {
    [toolKey: string]: CurrentGroupIds;
}

export const useUserToolsServicesStore = defineStore("userToolsServicesStore", () => {
    const userStore = useUserStore();
    const { currentUser } = storeToRefs(userStore);

    const userToolsServices = ref<Record<string, UserSourceService[]>>({});
    const userToolServiceGroups = ref<Record<string, ServiceCredentialsGroup>>({});

    const isBusy = ref(false);
    const busyMessage = ref<string>("");

    const userToolsServicesCurrentGroupIds = ref<ToolsCurrentGroupIds>({});

    const userServicesExistForTool = computed(() => {
        return (toolId: string, toolVersion: string) => {
            const userToolServiceKey = getUserToolServiceKey(toolId, toolVersion);
            return userToolsServices.value[userToolServiceKey];
        };
    });

    const userToolServicesFor = computed(() => (toolId: string, toolVersion: string) => {
        const userToolServiceKey = getUserToolServiceKey(toolId, toolVersion);
        return userToolsServices.value[userToolServiceKey];
    });

    function getUserToolServiceKey(toolId: string, toolVersion: string): string {
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

    function initToolsCurrentGroupIds() {
        for (const toolKey in userToolsServices.value) {
            const userToolServices = userToolsServices.value[toolKey];
            if (userToolServices) {
                userToolsServicesCurrentGroupIds.value[toolKey] = {};
                for (const service of userToolServices) {
                    userToolsServicesCurrentGroupIds.value[toolKey][service.id] = service.current_group_id || undefined;
                }
            }
        }
    }

    function getToolService(
        toolId: string,
        toolVersion: string,
        serviceIdentifier: ServiceCredentialsIdentifier
    ): UserSourceService | undefined {
        const userToolServiceKey = getUserToolServiceKey(toolId, toolVersion);
        const service = userToolsServices.value[userToolServiceKey]?.find(
            (service) => service.name === serviceIdentifier.name && service.version === serviceIdentifier.version
        );

        return service;
    }

    function updateUserToolServiceGroup(group: ServiceCredentialsGroup) {
        set(userToolServiceGroups.value, group.id, group);

        for (const userToolServiceKey in userToolsServices.value) {
            const userToolServices = userToolsServices.value[userToolServiceKey];
            if (userToolServices) {
                for (const userToolService of userToolServices) {
                    const currentUserToolServiceGroup = userToolService.groups.findIndex((g) => g.id === group.id);
                    if (currentUserToolServiceGroup !== -1) {
                        set(userToolService.groups, currentUserToolServiceGroup, group);
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

            const userToolServiceKey = getUserToolServiceKey(toolId, toolVersion);

            if (error) {
                throw Error(`Failed to fetch user credentials for tool ${userToolServiceKey}: ${error.err_msg}`);
            }

            set(userToolsServices.value, userToolServiceKey, data);

            updateUserToolServiceGroups(data);

            initToolsCurrentGroupIds();

            return data;
        } finally {
            isBusy.value = false;
            busyMessage.value = "";
        }
    }

    async function createNewCredentialsGroupForTool(
        serviceIdentifier: ServiceCredentialsIdentifier,
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
                const userToolServiceKey = getUserToolServiceKey(toolId, toolVersion);
                throw Error(`Failed to create new credentials group for tool ${userToolServiceKey}: ${error.err_msg}`);
            }

            await fetchAllUserToolServices(toolId, toolVersion);

            const toolService = getToolService(toolId, toolVersion, serviceIdentifier);
            if (!toolService?.id) {
                const userToolServiceKey = getUserToolServiceKey(toolId, toolVersion);
                throw new Error(`No service found for tool ${userToolServiceKey}`);
            }

            const userToolServicesCurrentGroupIds =
                userToolsServicesCurrentGroupIds.value[getUserToolServiceKey(toolId, toolVersion)];
            if (userToolServicesCurrentGroupIds && !userToolServicesCurrentGroupIds[toolService.id]) {
                userToolServicesCurrentGroupIds[toolService.id] = undefined;
            }

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
                const userToolServiceKey = getUserToolServiceKey(toolId, toolVersion);
                throw Error(`Failed to save user credentials ${groupId} for ${userToolServiceKey} : ${error.err_msg}`);
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

        const toolService = getToolService(toolId, toolVersion, serviceIdentifier);
        const toolServicesId = toolService?.id;
        if (!toolServicesId) {
            const userToolServiceKey = getUserToolServiceKey(toolId, toolVersion);
            throw new Error(`No service found for tool ${userToolServiceKey}`);
        }

        busyMessage.value = "Updating your credentials";
        isBusy.value = true;

        try {
            const { error } = await GalaxyApi().DELETE(
                "/api/users/{user_id}/credentials/{user_credentials_id}/{group_id}",
                {
                    params: {
                        path: { user_id: userId, user_credentials_id: toolServicesId, group_id: groupId },
                    },
                }
            );

            if (error) {
                const userToolServiceKey = getUserToolServiceKey(toolId, toolVersion);
                throw Error(`Failed to delete user credentials group for tool ${userToolServiceKey}: ${error.err_msg}`);
            }

            await fetchAllUserToolServices(toolId, toolVersion);

            const updatedToolService = getToolService(toolId, toolVersion, serviceIdentifier);
            const updatedToolServicesId = updatedToolService?.id;
            const userToolServicesCurrentGroupIds =
                userToolsServicesCurrentGroupIds.value[getUserToolServiceKey(toolId, toolVersion)];
            if (!updatedToolServicesId && userToolServicesCurrentGroupIds) {
                delete userToolServicesCurrentGroupIds[toolServicesId];
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
                const userToolServiceKey = getUserToolServiceKey(toolId, toolVersion);
                throw new Error(
                    `Failed to select current credentials groups for tool ${userToolServiceKey}: ${error.err_msg}`
                );
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
        userToolsServicesCurrentGroupIds,
        initToolsCurrentGroupIds,
        getToolService,
        fetchAllUserToolServices,
        createNewCredentialsGroupForTool,
        updateUserCredentialsForTool,
        deleteCredentialsGroupForTool,
        selectCurrentCredentialsGroupsForTool,
    };
});
