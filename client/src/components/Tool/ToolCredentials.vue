<script setup lang="ts">
import { BAlert, BButton, BModal } from "bootstrap-vue";
import { computed, ref } from "vue";

import type { ToolCredentials, UserCredentials } from "@/api/users";
import { useUserStore } from "@/stores/userStore";

import LoadingSpan from "@/components/LoadingSpan.vue";
import ManageToolCredentials from "@/components/User/Credentials/ManageToolCredentials.vue";

interface Props {
    toolId: string;
    toolVersion: string;
    toolCredentials: ToolCredentials[];
}

const props = defineProps<Props>();

const userStore = useUserStore();

const isBusy = ref(true);
const busyMessage = ref<string>("");
const userCredentials = ref<UserCredentials[] | undefined>(undefined);

const hasUserProvidedCredentials = computed<boolean>(() => {
    if (!userCredentials.value) {
        return false;
    }
    return userCredentials.value.every(
        (credentials) =>
            !credentials.optional &&
            credentials.secrets.every((secret) => secret.alreadySet) &&
            credentials.variables.every((variable) => variable.value !== undefined)
    );
});

const credentialsRequired = computed<boolean>(() => {
    return props.toolCredentials.every((credentials) => !credentials.optional);
});

const provideCredentialsButtonTitle = computed(() => {
    return hasUserProvidedCredentials.value ? "Manage credentials" : "Provide credentials";
});

const bannerVariant = computed(() => {
    if (isBusy.value) {
        return "info";
    }
    return hasUserProvidedCredentials.value ? "success" : "warning";
});

const showModal = ref(false);

/**
 * Check if the user has credentials for the tool.
 */
async function checkUserCredentials(providedCredentials?: UserCredentials[]) {
    busyMessage.value = "Checking your credentials...";
    isBusy.value = true;
    try {
        if (userStore.isAnonymous) {
            return;
        }
        // TODO: Implement store and real API request to check if the user has credentials for the tool.
        await new Promise((resolve) => setTimeout(resolve, 1000));
        if (!providedCredentials) {
            providedCredentials = [];
            for (const credentials of props.toolCredentials) {
                providedCredentials.push({
                    ...credentials,
                    secrets: credentials.secrets.map((secret) => ({
                        ...secret,
                        alreadySet: false,
                        value: "placeholder",
                    })),
                    variables: credentials.variables.map((variable) => ({ ...variable, value: "test" })),
                });
            }
        }
        //----------------------------------------------
        userCredentials.value = providedCredentials;
    } catch (error) {
        // TODO: Implement error handling.
        console.error("Error checking user credentials", error);
    } finally {
        isBusy.value = false;
    }
}

function provideCredentials() {
    showModal.value = true;
}

async function onSavedCredentials(providedCredentials: UserCredentials[]) {
    showModal.value = false;
    busyMessage.value = "Saving your credentials...";
    try {
        isBusy.value = true;
        userCredentials.value = await saveCredentials(providedCredentials);
    } catch (error) {
        // TODO: Implement error handling.
        console.error("Error saving user credentials", error);
    } finally {
        isBusy.value = false;
    }
}

async function saveCredentials(providedCredentials: UserCredentials[]): Promise<UserCredentials[]> {
    // TODO: Implement store and real API request to save the provided credentials.
    console.log("SAVING CREDENTIALS", providedCredentials);
    await new Promise((resolve) => setTimeout(resolve, 1000));
    for (const credentials of providedCredentials) {
        for (const secret of credentials.secrets) {
            secret.alreadySet = true;
        }
    }
    return providedCredentials;
}

checkUserCredentials();
</script>

<template>
    <div>
        <BAlert show :variant="bannerVariant" class="tool-credentials-banner">
            <LoadingSpan v-if="isBusy" :message="busyMessage" />
            <div v-else-if="userStore.isAnonymous">
                <span v-if="credentialsRequired">
                    <strong>
                        This tool requires credentials to access its services and you need to be logged in to provide
                        credentials.
                    </strong>
                </span>
                <span v-else>
                    This tool <strong>can use additional credentials</strong> to access its services
                    <strong>or you can use it anonymously</strong>.
                </span>
                <br />
                If you want to provide credentials, please <a href="/login/start">log in or register here</a>.
            </div>
            <div v-else class="d-flex justify-content-between align-items-center">
                <div class="credentials-info">
                    <span v-if="hasUserProvidedCredentials">
                        <strong>You have already provided credentials for this tool.</strong> You can update or delete
                        your credentials, using the <i>{{ provideCredentialsButtonTitle }}</i> button.
                    </span>
                    <span v-else-if="credentialsRequired">
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
                :credentials="userCredentials"
                @save-credentials="onSavedCredentials" />
        </BModal>
    </div>
</template>

<style scoped>
.tool-credentials-banner {
    margin-bottom: 1rem;
}
</style>
