<script setup lang="ts">
import { faCheck, faExclamation, faKey } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon, FontAwesomeLayers } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton } from "bootstrap-vue";
import { computed, ref } from "vue";

import { isRegisteredUser } from "@/api";
import {
    type CreateSourceCredentialsPayload,
    type ServiceCredentialsDefinition,
    type ServiceCredentialsIdentifier,
    type SourceCredentialsDefinition,
    transformToSourceCredentials,
    type UserCredentials,
} from "@/api/users";
import { useUserCredentialsStore } from "@/stores/userCredentials";
import { useUserStore } from "@/stores/userStore";

import LoadingSpan from "@/components/LoadingSpan.vue";
import ManageToolCredentials from "@/components/User/Credentials/ManageToolCredentials.vue";

interface Props {
    toolId: string;
    toolVersion: string;
    toolCredentialsDefinition: ServiceCredentialsDefinition[];
}

const props = defineProps<Props>();

const userStore = useUserStore();
const userCredentialsStore = useUserCredentialsStore(
    isRegisteredUser(userStore.currentUser) ? userStore.currentUser.id : "anonymous"
);

const isBusy = ref(true);
const busyMessage = ref<string>("");
const userCredentials = ref<UserCredentials[] | undefined>(undefined);

const credentialsDefinition = computed<SourceCredentialsDefinition>(() => {
    return transformToSourceCredentials(props.toolId, props.toolCredentialsDefinition);
});

const hasUserProvidedRequiredCredentials = computed<boolean>(() => {
    if (!userCredentials.value || userCredentials.value.length === 0) {
        return false;
    }
    return userCredentials.value.every((credentials) => areRequiredSetByUser(credentials));
});

const hasUserProvidedAllCredentials = computed<boolean>(() => {
    if (!userCredentials.value || userCredentials.value.length === 0) {
        return false;
    }
    return userCredentials.value.every(areAllSetByUser);
});

const hasSomeOptionalCredentials = computed<boolean>(() => {
    for (const service of credentialsDefinition.value.services.values()) {
        if (
            service.secrets.some((secret) => secret.optional) ||
            service.variables.some((variable) => variable.optional)
        ) {
            return true;
        }
    }
    return false;
});

const hasSomeRequiredCredentials = computed<boolean>(() => {
    for (const service of credentialsDefinition.value.services.values()) {
        if (
            service.secrets.some((secret) => !secret.optional) ||
            service.variables.some((variable) => !variable.optional)
        ) {
            return true;
        }
    }
    return false;
});

const provideCredentialsButtonTitle = computed(() => {
    return hasUserProvidedRequiredCredentials.value ? "Manage credentials" : "Provide credentials";
});

const bannerVariant = computed(() => {
    if (isBusy.value) {
        return "info";
    }
    return hasUserProvidedRequiredCredentials.value ? "success" : "warning";
});

const showModal = ref(false);

/**
 * Check if the user has credentials for the tool.
 * @param providedCredentials - The provided credentials to check. If not provided, the function will fetch the
 * credentials from the store if they exist.
 */
async function checkUserCredentials(providedCredentials?: UserCredentials[]) {
    busyMessage.value = "Checking your credentials...";
    isBusy.value = true;
    try {
        if (userStore.isAnonymous) {
            return;
        }

        if (!providedCredentials) {
            providedCredentials =
                userCredentialsStore.getAllUserCredentialsForTool(props.toolId) ??
                (await userCredentialsStore.fetchAllUserCredentialsForTool(props.toolId));
        }

        userCredentials.value = providedCredentials;
    } catch (error) {
        // TODO: Implement error handling.
        console.error("Error checking user credentials", error);
    } finally {
        isBusy.value = false;
    }
}

function areAllSetByUser(credentials: UserCredentials): boolean {
    const selectedGroup = credentials.groups[credentials.current_group_name];
    if (!selectedGroup) {
        return false;
    }
    return (
        credentials.credential_definitions.variables.every((v) => {
            const variable = selectedGroup.variables.find((dv) => v.name === dv.name);
            return variable?.is_set ?? false;
        }) &&
        credentials.credential_definitions.secrets.every((s) => {
            const secret = selectedGroup.secrets.find((ds) => s.name === ds.name);
            return secret?.is_set ?? false;
        })
    );
}

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

function toggleDialog() {
    showModal.value = !showModal.value;
}

async function onSavedCredentials(providedCredentials: CreateSourceCredentialsPayload) {
    showModal.value = false;
    busyMessage.value = "Saving your credentials...";
    try {
        isBusy.value = true;
        userCredentials.value = await userCredentialsStore.saveUserCredentialsForTool(providedCredentials);
    } catch (error) {
        // TODO: Implement error handling.
        console.error("Error saving user credentials", error);
    } finally {
        isBusy.value = false;
    }
}

async function onDeleteCredentialsGroup(serviceId: ServiceCredentialsIdentifier, groupName: string) {
    busyMessage.value = "Updating your credentials...";
    isBusy.value = true;
    try {
        userCredentialsStore.deleteCredentialsGroupForTool(props.toolId, serviceId, groupName);
    } catch (error) {
        // TODO: Implement error handling.
        console.error("Error deleting user credentials group", error);
    } finally {
        isBusy.value = false;
    }
}

function onUpdateUserCredentials(data?: UserCredentials[]) {
    userCredentials.value = data;
}

checkUserCredentials();
</script>

<template>
    <div class="mt-2">
        <BAlert show :variant="bannerVariant">
            <LoadingSpan v-if="isBusy" :message="busyMessage" />
            <div v-else-if="userStore.isAnonymous">
                <span v-if="hasSomeRequiredCredentials">
                    <strong>
                        This tool requires credentials to access its services and you need to be logged in to provide
                        them.
                    </strong>
                </span>
                <span v-else>
                    This tool <strong>can use additional credentials</strong> to access its services
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
                        <FontAwesomeIcon
                            v-else-if="hasSomeRequiredCredentials"
                            :icon="faExclamation"
                            fixed-width
                            transform="shrink-6 right-8 down-7" />
                    </FontAwesomeLayers>

                    <span v-if="hasUserProvidedRequiredCredentials">
                        <strong>You have already provided credentials for this tool.</strong> You can update or delete
                        your credentials, using the <i>{{ provideCredentialsButtonTitle }}</i> button.
                        <span v-if="hasSomeOptionalCredentials && !hasUserProvidedAllCredentials">
                            <br />
                            You can still provide some optional credentials for this tool.
                        </span>
                    </span>
                    <span v-else-if="hasSomeRequiredCredentials">
                        This tool <strong>requires you to enter credentials</strong> to access its services. Please
                        provide your credentials before using the tool using the
                        <i>{{ provideCredentialsButtonTitle }}</i> button.
                    </span>
                    <span v-else>
                        This tool <strong>can use credentials</strong> to access its services. If you don't provide
                        credentials, you can still use the tool, but you will access its services
                        <strong>anonymously</strong> and in some cases, with limited functionality.
                    </span>
                </div>

                <div>
                    <BButton variant="primary" size="sm" @click="toggleDialog">
                        {{ provideCredentialsButtonTitle }}
                    </BButton>
                </div>
            </div>
        </BAlert>

        <ManageToolCredentials
            v-if="showModal"
            :tool-id="props.toolId"
            :tool-version="props.toolVersion"
            :tool-credentials-definition="credentialsDefinition"
            :tool-user-credentials="userCredentials"
            @onUpdateCredentialsList="onUpdateUserCredentials"
            @delete-credentials-group="onDeleteCredentialsGroup"
            @save-credentials="onSavedCredentials"
            @close="toggleDialog" />
    </div>
</template>
