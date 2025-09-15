import { defineStore, storeToRefs } from "pinia";
import { computed, readonly, ref, set } from "vue";

import { GalaxyApi, isRegisteredUser } from "@/api";
import type {
    CreateSourceCredentialsPayload,
    SelectCurrentGroupPayload,
    ServiceCredentialsContext,
    ServiceCredentialsDefinition,
    ServiceCredentialsGroup,
    ServiceCredentialsIdentifier,
    ServiceGroupPayload,
    UserSourceService,
    UserToolsServiceCredentialsFull,
} from "@/api/users";
import { useToolsServiceCredentialsDefinitionsStore } from "@/stores/toolsServiceCredentialsDefinitionsStore";
import { useUserStore } from "@/stores/userStore";

export const SECRET_PLACEHOLDER = "********";

export interface ServiceCredentialsCurrentGroupIds {
    [userServiceCredentialsId: string]: string | undefined;
}

export interface ToolsCurrentGroupIds {
    [userToolKey: string]: ServiceCredentialsCurrentGroupIds;
}

export interface ServiceCredentialsGroupDetails extends ServiceCredentialsGroup {
    sourceId: string;
    sourceVersion: string;
    serviceDefinition: ServiceCredentialsDefinition;
}

export const useUserToolsServiceCredentialsStore = defineStore("userToolsServiceCredentialsStore", () => {
    const userStore = useUserStore();
    const { currentUser } = storeToRefs(userStore);

    const userToolsServices = ref<Record<string, UserSourceService[]>>({});
    const userToolServiceCredentialsGroups = ref<Record<string, ServiceCredentialsGroup>>({});

    const { setToolServiceCredentialsDefinitionFor, getToolServiceCredentialsDefinitionsFor } =
        useToolsServiceCredentialsDefinitionsStore();

    const isBusy = ref(false);
    const busyMessage = ref<string>("");

    const userToolsServicesCurrentGroupIds = ref<ToolsCurrentGroupIds>({});

    function updateToolServiceCredentialsCurrentGroupId(
        toolId: string,
        toolVersion: string,
        userServiceCredentialsId: string,
        groupId: string | undefined,
    ) {
        const userToolKey = getUserToolKey(toolId, toolVersion);
        const userToolServiceCurrentGroupIds = userToolsServicesCurrentGroupIds.value[userToolKey];

        if (!userToolServiceCurrentGroupIds) {
            throw new Error(`Current group IDs are not defined for user tool service: ${userToolKey}`);
        }

        userToolServiceCurrentGroupIds[userServiceCredentialsId] = groupId;
        userToolsServicesCurrentGroupIds.value = { ...userToolsServicesCurrentGroupIds.value };
    }

    const userToolsGroups = computed(() => {
        const groups: ServiceCredentialsGroupDetails[] = [];
        for (const userToolKey in userToolsServices.value) {
            const userToolServices = userToolsServices.value[userToolKey];
            if (userToolServices) {
                for (const service of userToolServices) {
                    for (const group of service.groups) {
                        const serviceDefinitions = getToolServiceCredentialsDefinitionsFor(
                            service.source_id,
                            service.source_version,
                        );

                        const serviceDefinition = serviceDefinitions.find(
                            (def) => def.name === service.name && def.version === service.version,
                        );
                        if (!serviceDefinition) {
                            throw new Error(`Service definition not found for ${service.name}:${service.version}`);
                        }
                        groups.push({
                            ...group,
                            sourceId: service.source_id,
                            sourceVersion: service.source_version,
                            serviceDefinition: serviceDefinition,
                        });
                    }
                }
            }
        }
        return groups;
    });

    const getUserToolServiceCurrentGroupId = computed(() => {
        return (toolId: string, toolVersion: string, userServiceCredentialsId: string): string | undefined => {
            if (!isRegisteredUser(currentUser.value)) {
                return undefined;
            }
            const userToolKey = getUserToolKey(toolId, toolVersion);
            if (!userToolsServicesCurrentGroupIds.value[userToolKey]) {
                return undefined;
            }
            return userToolsServicesCurrentGroupIds.value[userToolKey][userServiceCredentialsId];
        };
    });

    const userToolServicesFor = computed(() => (toolId: string, toolVersion: string) => {
        if (!isRegisteredUser(currentUser.value)) {
            return undefined;
        }
        const userToolKey = getUserToolKey(toolId, toolVersion);
        return userToolsServices.value[userToolKey];
    });

    function updateUserToolServiceGroups(userSourceServices: UserSourceService[]) {
        for (const sourceService of userSourceServices) {
            for (const group of sourceService.groups) {
                userToolServiceCredentialsGroups.value[group.id] = group;
            }
        }
    }

    function initToolsCurrentGroupIds() {
        for (const userToolKey in userToolsServices.value) {
            const userToolServices = userToolsServices.value[userToolKey];
            if (userToolServices) {
                userToolsServicesCurrentGroupIds.value[userToolKey] = {};
                for (const service of userToolServices) {
                    userToolsServicesCurrentGroupIds.value[userToolKey][service.id] =
                        service.current_group_id || undefined;
                }
            }
        }
    }

    function getToolService(
        toolId: string,
        toolVersion: string,
        serviceIdentifier: ServiceCredentialsIdentifier,
    ): UserSourceService | undefined {
        const userToolKey = getUserToolKey(toolId, toolVersion);
        const service = userToolsServices.value[userToolKey]?.find(
            (service) => service.name === serviceIdentifier.name && service.version === serviceIdentifier.version,
        );

        return service;
    }

    function updateUserToolServiceGroup(group: ServiceCredentialsGroup) {
        set(userToolServiceCredentialsGroups.value, group.id, group);

        for (const userToolKey in userToolsServices.value) {
            const userToolServices = userToolsServices.value[userToolKey];
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

    async function fetchAllUserToolsServiceCredentials(includeDefinition: boolean = true) {
        if (!isRegisteredUser(currentUser.value)) {
            return [];
        }

        const userId = ensureUserIsRegistered();

        busyMessage.value = "Loading all your service credentials";
        isBusy.value = true;

        try {
            const { data, error } = await GalaxyApi().GET("/api/users/{user_id}/credentials", {
                params: {
                    path: { user_id: userId },
                    query: {
                        include_definition: includeDefinition,
                    },
                },
            });

            if (error) {
                throw Error(`${error.err_msg} - Failed to fetch all user tools service credentials.`);
            }

            for (const usc of data) {
                if (includeDefinition) {
                    const withDefinition = usc as UserToolsServiceCredentialsFull;

                    setToolServiceCredentialsDefinitionFor(withDefinition.source_id, withDefinition.source_version, [
                        withDefinition.definition,
                    ]);
                }

                const userToolKey = getUserToolKey(usc.source_id, usc.source_version);
                const matchingToolServices = data.filter(
                    (d) => d.source_id === usc.source_id && d.source_version === usc.source_version,
                );
                set(userToolsServices.value, userToolKey, matchingToolServices);

                updateUserToolServiceGroups(matchingToolServices);

                initToolsCurrentGroupIds();
            }
        } finally {
            isBusy.value = false;
            busyMessage.value = "";
        }
    }

    async function fetchAllUserToolServices(toolId: string, toolVersion: string): Promise<void> {
        const userId = ensureUserIsRegistered();

        busyMessage.value = "Loading your service credentials for this tool";
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

            const userToolKey = getUserToolKey(toolId, toolVersion);

            if (error) {
                throw Error(`${error.err_msg} - Failed to fetch user credentials for tool ${userToolKey}.`);
            }

            set(userToolsServices.value, userToolKey, data);

            updateUserToolServiceGroups(data);

            initToolsCurrentGroupIds();
        } finally {
            isBusy.value = false;
            busyMessage.value = "";
        }
    }

    async function createNewCredentialsGroupForTool(
        serviceIdentifier: ServiceCredentialsIdentifier,
        createSourceCredentialsPayload: CreateSourceCredentialsPayload,
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
                const userToolKey = getUserToolKey(toolId, toolVersion);
                throw Error(`${error.err_msg} - Failed to create new credentials group for tool ${userToolKey}.`);
            }

            await fetchAllUserToolServices(toolId, toolVersion);

            const toolService = getToolService(toolId, toolVersion, serviceIdentifier);
            if (!toolService?.id) {
                const userToolKey = getUserToolKey(toolId, toolVersion);
                throw new Error(`No service found for tool ${userToolKey}`);
            }

            const userToolServicesCurrentGroupIds =
                userToolsServicesCurrentGroupIds.value[getUserToolKey(toolId, toolVersion)];
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
        serviceGroupPayload: ServiceGroupPayload,
    ): Promise<ServiceCredentialsGroup> {
        const userId = ensureUserIsRegistered();

        const serviceGroupPayloadCopy = structuredClone(serviceGroupPayload);
        removeSecretPlaceholders(serviceGroupPayloadCopy);

        busyMessage.value = "Updating your credentials";
        isBusy.value = true;

        try {
            const { data, error } = await GalaxyApi().PUT("/api/users/{user_id}/credentials/group/{group_id}", {
                params: {
                    path: { user_id: userId, group_id: groupId },
                },
                body: serviceGroupPayloadCopy,
            });

            if (error) {
                const userToolKey = getUserToolKey(toolId, toolVersion);
                throw Error(`${error.err_msg} - Failed to save user credentials ${groupId} for ${userToolKey}.`);
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
        groupId: string,
    ): Promise<void> {
        const userId = ensureUserIsRegistered();
        const group = userToolServiceCredentialsGroups.value[groupId];
        if (!group) {
            return;
        }

        const toolService = getToolService(toolId, toolVersion, serviceIdentifier);
        const toolServicesId = toolService?.id;
        if (!toolServicesId) {
            const userToolKey = getUserToolKey(toolId, toolVersion);
            throw new Error(`No service found for tool ${userToolKey}`);
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
                },
            );

            if (error) {
                const userToolKey = getUserToolKey(toolId, toolVersion);
                throw Error(`${error.err_msg} - Failed to delete user credentials group for tool ${userToolKey}.`);
            }

            await fetchAllUserToolServices(toolId, toolVersion);

            const updatedToolService = getToolService(toolId, toolVersion, serviceIdentifier);
            const updatedToolServicesId = updatedToolService?.id;
            const userToolServicesCurrentGroupIds =
                userToolsServicesCurrentGroupIds.value[getUserToolKey(toolId, toolVersion)];
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
        serviceCredentials: SelectCurrentGroupPayload[],
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
                const userToolKey = getUserToolKey(toolId, toolVersion);
                throw new Error(
                    `Failed to select current credentials groups for tool ${userToolKey}: ${error.err_msg}`,
                );
            }

            await fetchAllUserToolServices(toolId, toolVersion);
        } finally {
            isBusy.value = false;
            busyMessage.value = "";
        }
    }

    /**
     * Get the currently selected credentials provided by the user for a specific tool.
     *
     * This information is used when executing a tool to provide the appropriate credentials.
     * In addition to the corresponding service credentials ID and group ID, the service name and version
     * are also provided to facilitate the identification of the credentials being used.
     */
    function getCredentialsExecutionContextForTool(toolId: string, toolVersion: string) {
        const services = userToolServicesFor.value(toolId, toolVersion);
        if (!services) {
            console.warn(
                "Cannot get selected credentials execution context, no services found for tool",
                toolId,
                toolVersion,
            );
            return [];
        }
        const selectedCredentials: ServiceCredentialsContext[] = [];
        for (const service of services) {
            const currentGroupId = getUserToolServiceCurrentGroupId.value(toolId, toolVersion, service.id);
            if (currentGroupId) {
                const group = userToolServiceCredentialsGroups.value[currentGroupId];
                if (group) {
                    selectedCredentials.push({
                        user_credentials_id: service.id,
                        name: service.name,
                        version: service.version,
                        selected_group: {
                            id: group.id,
                            name: group.name,
                        },
                    });
                } else {
                    console.warn(
                        `Current group ID ${currentGroupId} for service ${service.name}:${service.version} not found in store`,
                    );
                }
            }
        }
        return selectedCredentials;
    }

    function getUserToolKey(toolId: string, toolVersion: string): string {
        const userId = ensureUserIsRegistered();
        return `${userId}-${toolId}-${toolVersion}`;
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
        userToolServicesFor,
        userToolServiceCredentialsGroups,
        userToolsServicesCurrentGroupIds,
        getUserToolServiceCurrentGroupId,
        userToolsGroups,
        initToolsCurrentGroupIds,
        getUserToolKey,
        getToolService,
        fetchAllUserToolsServiceCredentials,
        fetchAllUserToolServices,
        updateToolServiceCredentialsCurrentGroupId,
        createNewCredentialsGroupForTool,
        updateUserCredentialsForTool,
        deleteCredentialsGroupForTool,
        selectCurrentCredentialsGroupsForTool,
        getCredentialsExecutionContextForTool,
    };
});
