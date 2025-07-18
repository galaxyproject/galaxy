<script setup lang="ts">
import { faCheck, faExclamation, faKey, faWrench } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon, FontAwesomeLayers } from "@fortawesome/vue-fontawesome";
import { BAlert, BModal } from "bootstrap-vue";
import { computed, ref } from "vue";

import {
    type CreateSourceCredentialsPayload,
    getKeyFromCredentialsIdentifier,
    type ServiceCredentialPayload,
    type ServiceCredentialsDefinition,
    type ServiceCredentialsIdentifier,
    type ServiceGroupPayload,
    type SourceCredentialsDefinition,
    transformToSourceCredentials,
    type UserCredentials,
} from "@/api/users";
import { SECRET_PLACEHOLDER, useUserCredentialsStore } from "@/stores/userCredentials";
import { useUserStore } from "@/stores/userStore";

import ServiceCredentials from "../User/Credentials/ServiceCredentials.vue";
import Heading from "./Heading.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface ToolWithCredentialsProps {
    id: string;
    version: string;
    name: string;
    label: string;
    credentialsDefinition: ServiceCredentialsDefinition[];
    toolUserCredentials?: UserCredentials[];
}

interface Props {
    tools: ToolWithCredentialsProps[];
    full?: boolean;
}

const props = defineProps<Props>();

const userStore = useUserStore();
const userCredentialsStore = useUserCredentialsStore();

const hasUserProvidedAllCredentials = true;
const hasSomeOptionalCredentials = true;
const provideCredentialsButtonTitle = "Provide credentials";

const isBusy = ref(true);
const busyMessage = ref("");
const userCredentials = ref<UserCredentials[] | undefined>(undefined);

const bannerVariant = computed(() => {
    if (isBusy.value) {
        return "info";
    }
    return hasUserProvidedRequiredCredentials.value ? "success" : "warning";
});

const hasSomeRequiredCredentials = computed<boolean>(() => {
    // for (const service of credentialsDefinition.value.services.values()) {
    //     if (
    //         service.secrets.some((secret) => !secret.optional) ||
    //         service.variables.some((variable) => !variable.optional)
    //     ) {
    //         return true;
    //     }
    // }
    return false;
});

function areRequiredSetByUser(credentials: UserCredentials): boolean {
    const selectedGroup = credentials.groups[credentials.current_group_name];
    if (!selectedGroup) {
        return false;
    }
    return (
        credentials.credential_definitions.variables.every((v) => {
            const variable = selectedGroup.variables.find((dv) => v.name === dv.name);
            return variable ? variable.is_set : v.optional;
        }) &&
        credentials.credential_definitions.secrets.every((s) => {
            const secret = selectedGroup.secrets.find((ds) => s.name === ds.name);
            return secret ? secret.is_set : s.optional;
        })
    );
}

const hasUserProvidedRequiredCredentials = computed<boolean>(() => {
    if (!userCredentials.value || userCredentials.value.length === 0) {
        return false;
    }
    return userCredentials.value.every((credentials) => areRequiredSetByUser(credentials));
});

const hasError = ref(false);

async function checkUserCredentials() {
    busyMessage.value = "Checking your credentials...";
    isBusy.value = true;

    // const providedCredentials = ref<UserCredentials[] | undefined>(undefined);

    try {
        if (userStore.isAnonymous) {
            return;
        }

        userCredentials.value = await Promise.all(
            props.tools.map(async (tool) => {
                return (
                    userCredentialsStore.getAllUserCredentialsForTool(tool.id) ??
                    (await userCredentialsStore.fetchAllUserCredentialsForTool(tool.id))
                );
            })
        ).then((results) => results.flat());
    } catch (error) {
        hasError.value = true;
        console.error("Error fetching user credentials:", error);
        busyMessage.value = "Error fetching your credentials. Please try again later.";
    } finally {
        isBusy.value = false;
    }
}

checkUserCredentials();

const showModal = ref(false);
function toggleDialog() {
    showModal.value = !showModal.value;
}

function getUserCredentialsForService(
    key: string,
    toolUserCredentials: UserCredentials[]
): UserCredentials | undefined {
    return toolUserCredentials.find((c) => getKeyFromCredentialsIdentifier(c) === key);
}

function getServiceCredentialsDefinition(
    key: string,
    toolId: string,
    toolCredentialsDefinition: SourceCredentialsDefinition
): ServiceCredentialsDefinition {
    const definition = toolCredentialsDefinition.services.get(key);
    if (!definition) {
        throw new Error(`No definition found for credential service '${key}' in tool ${toolId}`);
    }
    return definition;
}

function buildGroupsFromUserCredentials(
    definition: ServiceCredentialsDefinition,
    userCredentials?: UserCredentials
): ServiceGroupPayload[] {
    const groups: ServiceGroupPayload[] = [];
    if (userCredentials) {
        const existingGroups = Object.values(userCredentials.groups);
        for (const group of existingGroups) {
            const newGroup: ServiceGroupPayload = {
                name: group.name,
                variables: definition.variables.map((variable) => ({
                    name: variable.name,
                    value: group.variables.find((v) => v.name === variable.name)?.value ?? null,
                })),
                secrets: definition.secrets.map((secret) => ({
                    name: secret.name,
                    value: group.secrets.find((s) => s.name === secret.name)?.is_set ? SECRET_PLACEHOLDER : null,
                    alreadySet: group.secrets.find((s) => s.name === secret.name)?.is_set ?? false,
                })),
            };
            groups.push(newGroup);
        }
    } else {
        const defaultGroup: ServiceGroupPayload = {
            name: "default",
            variables: definition.variables.map((variable) => ({
                name: variable.name,
                value: null,
            })),
            secrets: definition.secrets.map((secret) => ({
                name: secret.name,
                value: null,
            })),
        };
        groups.push(defaultGroup);
    }
    return groups;
}

type PCFT = {
    toolId: string;
    toolName: string;
    toolLabel: string;
    toolVersion: string;
    serviceCredentials: CreateSourceCredentialsPayload;
    credentialsDefinition: ServiceCredentialsDefinition[];
};

const providedCredentialsForTools = ref<PCFT[]>(initializeCredentials());

function initializeCredentials(): PCFT[] {
    const pCFT: PCFT[] = [];
    for (const tool of props.tools) {
        const serviceCredentials = [];

        const tmp = transformToSourceCredentials(tool.id, tool.credentialsDefinition);

        for (const key of tmp.services?.keys() ?? []) {
            const userCredentialForService = getUserCredentialsForService(key, tool.toolUserCredentials ?? []);
            console.log("User credentials for service:", key, userCredentialForService);
            const currentGroup = userCredentialForService?.current_group_name ?? "default";
            const definition = getServiceCredentialsDefinition(key, tool.id, tmp);
            const groups = buildGroupsFromUserCredentials(definition, userCredentialForService);

            console.log(
                "Service credentials for tool:",
                tool.id,
                tool.version,
                "Definition:",
                definition,
                "Groups:",
                groups
            );

            const credential: ServiceCredentialPayload = {
                name: definition.name,
                version: definition.version,
                current_group: currentGroup,
                groups,
            };

            serviceCredentials.push(credential);
        }

        const providedCredentials: CreateSourceCredentialsPayload = {
            source_type: "tool",
            source_id: tool.id,
            source_version: tool.version,
            credentials: serviceCredentials,
        };

        console.log("Provided credentials for tool:", tool.id, tool.version, serviceCredentials);

        pCFT.push({
            toolId: tool.id,
            toolName: tool.name,
            toolLabel: tool.label,
            toolVersion: tool.version,
            serviceCredentials: providedCredentials,
            credentialsDefinition: tool.credentialsDefinition,
        });
    }

    return pCFT;
}

function sourceData(
    toolId: string,
    toolVersion: string
): { sourceId: string; sourceType: "tool"; sourceVersion: string } {
    return {
        sourceId: toolId,
        sourceType: "tool",
        sourceVersion: toolVersion,
    };
}

const emit = defineEmits<{
    (e: "onUpdateCredentialsList", data?: UserCredentials[]): void;
    (e: "save-credentials", credentials: CreateSourceCredentialsPayload): void;
    (e: "delete-credentials-group", serviceId: ServiceCredentialsIdentifier, groupName: string): void;
    (e: "close"): void;
}>();

function onUpdateCredentialsList(data?: UserCredentials[]) {
    console.log("161 - ManageToolCredentials.vue - onUpdateCredentialsList", data);
    emit("onUpdateCredentialsList", data);
}

function onNewCredentialsSet(credential: ServiceCredentialPayload, newSet: ServiceGroupPayload) {
    // const credentialFound = providedCredentials.value.credentials.find(
    //     (c) => c.name === credential.name && c.version === credential.version
    // );
    // if (credentialFound) {
    //     credentialFound.groups.push(newSet);
    // }
}

function onDeleteCredentialsGroup(serviceId: ServiceCredentialsIdentifier, groupName: string) {
    // const credentialFound = providedCredentials.value.credentials.find(
    //     (c) => c.name === serviceId.name && c.version === serviceId.version
    // );
    // if (credentialFound) {
    //     credentialFound.groups = credentialFound.groups.filter((g) => g.name !== groupName);
    //     emit("delete-credentials-group", serviceId, groupName);
    // }
}

function onCurrentSetChange(credential: ServiceCredentialPayload, newSet?: ServiceGroupPayload) {
    // const credentialFound = providedCredentials.value.credentials.find(
    //     (c) => c.name === credential.name && c.version === credential.version
    // );
    // if (credentialFound) {
    //     credentialFound.current_group = newSet?.name;
    // }
}
</script>

<template>
    <BAlert show :variant="bannerVariant">
        <LoadingSpan v-if="isBusy" :message="busyMessage" />
        <BAlert v-else-if="hasError">
            {{ busyMessage }}
        </BAlert>
        <div v-else-if="userStore.isAnonymous">
            <FontAwesomeIcon :icon="faKey" fixed-width />
            <span v-if="hasSomeRequiredCredentials">
                <strong>
                    Some steps in this workflow require credentials to access its services and you need to be logged in
                    to provide them.
                </strong>
            </span>
            <span v-else>
                Some steps in this workflow <strong>can use additional credentials</strong> to access its services
                <strong>or you can use it anonymously</strong>.
            </span>
            <br />
            Please <a href="/login/start">log in or register here</a>.
        </div>
        <div v-else class="d-flex justify-content-between align-items-center">
            <div>
                <FontAwesomeLayers class="mr-1">
                    <FontAwesomeIcon :icon="faKey" fixed-width />
                    <FontAwesomeIcon
                        v-if="hasUserProvidedRequiredCredentials"
                        :icon="faCheck"
                        fixed-width
                        transform="shrink-6 right-6 down-6" />
                    <FontAwesomeIcon v-else :icon="faExclamation" fixed-width transform="shrink-6 right-8 down-7" />
                </FontAwesomeLayers>

                <span v-if="hasUserProvidedRequiredCredentials">
                    <strong>You have already provided credentials for this workflow.</strong> You can update or delete
                    your credentials, using the <i>{{ provideCredentialsButtonTitle }}</i> button.
                    <span v-if="hasSomeOptionalCredentials && !hasUserProvidedAllCredentials">
                        <br />
                        You can still provide some optional credentials for this workflow.
                    </span>
                </span>
                <span v-else-if="hasSomeRequiredCredentials">
                    This workflow <strong>requires you to enter credentials</strong> to access its services. Please
                    provide your credentials before using the workflow using the
                    <i>{{ provideCredentialsButtonTitle }}</i> button.
                </span>
                <span v-else>
                    This workflow <strong>can use credentials</strong> to access its services. If you don't provide
                    credentials, you can still use the workflow, but you will access its services
                    <strong>anonymously</strong> and in some cases, with limited functionality.
                </span>
            </div>

            <div v-if="props.full" class="ml-2">
                <BButton variant="primary" size="sm" @click="toggleDialog"> Manage credentials </BButton>
            </div>
        </div>

        <BModal
            v-if="props.full"
            v-model="showModal"
            scrollable
            title="Select Credentials for tools in this workflow"
            ok-variant="primary"
            no-close-on-backdrop
            no-close-on-esc
            button-size="md"
            size="lg"
            ok-title="Select Credentials"
            cancel-variant="outline-danger">
            <div v-for="(pc, i) in providedCredentialsForTools" :key="i" class="mb-2">
                <Heading inline h6 size="sm" class="mb-2" separator>
                    <FontAwesomeIcon :icon="faWrench" fixed-width />
                    {{ pc.toolName }} - {{ pc.toolLabel }} ({{ pc.toolVersion }})
                </Heading>

                <div class="px-2">
                    <ServiceCredentials
                        v-for="(credential, k) in pc.serviceCredentials.credentials"
                        :key="credential.name + k"
                        class="mb-2"
                        :source-data="sourceData(pc.toolId, pc.toolVersion)"
                        :credential-definition="
                            getServiceCredentialsDefinition(
                                getKeyFromCredentialsIdentifier(credential),
                                pc.toolId,
                                transformToSourceCredentials(pc.toolId, pc.credentialsDefinition)
                            )
                        "
                        :credential-payload="credential"
                        :is-provided-by-user="hasUserProvidedRequiredCredentials"
                        @update-credentials-list="onUpdateCredentialsList"
                        @new-credentials-set="onNewCredentialsSet"
                        @delete-credentials-group="onDeleteCredentialsGroup"
                        @update-current-set="onCurrentSetChange">
                    </ServiceCredentials>
                </div>
            </div>
        </BModal>
    </BAlert>
</template>
