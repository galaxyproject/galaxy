<script setup lang="ts">
import { BAlert, BButton, BModal } from "bootstrap-vue";
import { computed, ref } from "vue";

import { isRegisteredUser } from "@/api";
import {
    type CreateSourceCredentialsPayload,
    type ServiceCredentialsDefinition,
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

    return userCredentials.value.every((credentials) => areOptional(credentials) || areSetByUser(credentials));
});

const hasUserProvidedAllCredentials = computed<boolean>(() => {
    if (!userCredentials.value || userCredentials.value.length === 0) {
        return false;
    }
    return userCredentials.value.every(areSetByUser);
});

const hasSomeOptionalCredentials = computed<boolean>(() => {
    for (const credentials of credentialsDefinition.value.services.values()) {
        if (credentials.optional) {
            return true;
        }
    }
    return false;
});

const hasSomeRequiredCredentials = computed<boolean>(() => {
    for (const credentials of credentialsDefinition.value.services.values()) {
        if (!credentials.optional) {
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

function areSetByUser(credentials: UserCredentials): boolean {
    return Object.values(credentials.groups).every((set) => {
        return set.variables.every((variable) => variable.value) && set.secrets.every((secret) => secret.already_set);
    });
}

function areOptional(credentials: UserCredentials): boolean {
    const matchingDefinition = credentialsDefinition.value.services.get(credentials.reference);
    if (!matchingDefinition) {
        return false;
    }
    return matchingDefinition.optional;
}

function provideCredentials() {
    showModal.value = true;
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

async function onDeleteCredentialsGroup(reference: string, groupName: string) {
    busyMessage.value = "Updating your credentials...";
    isBusy.value = true;
    try {
        userCredentialsStore.deleteCredentialsGroupForTool(props.toolId, reference, groupName);
    } catch (error) {
        // TODO: Implement error handling.
        console.error("Error deleting user credentials group", error);
    } finally {
        isBusy.value = false;
    }
}

checkUserCredentials();
</script>

<template>
    <div>
        <BAlert show :variant="bannerVariant" class="tool-credentials-banner">
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
                <div class="credentials-info">
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

                <BButton variant="primary" size="sm" class="provide-credentials-btn" @click="provideCredentials">
                    {{ provideCredentialsButtonTitle }}
                </BButton>
            </div>
        </BAlert>
        <BModal v-model="showModal" title="Manage Tool Credentials" hide-footer>
            <ManageToolCredentials
                :tool-id="props.toolId"
                :tool-version="props.toolVersion"
                :tool-credentials-definition="credentialsDefinition"
                :user-tool-credentials="userCredentials"
                @delete-credentials-group="onDeleteCredentialsGroup"
                @save-credentials="onSavedCredentials" />
        </BModal>
    </div>
</template>

<style scoped>
.tool-credentials-banner {
    margin-bottom: 1rem;
}
</style>
