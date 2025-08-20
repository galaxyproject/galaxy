<script setup lang="ts">
import { faCheck, faExclamation, faKey } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon, FontAwesomeLayers } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton } from "bootstrap-vue";
import { computed, onMounted, ref } from "vue";

import type { CreateSourceCredentialsPayload, ServiceCredentialsIdentifier, UserCredentials } from "@/api/users";
import { Toast } from "@/composables/toast";
import { useUserToolCredentials } from "@/composables/userToolCredentials";
import { useUserCredentialsStore } from "@/stores/userCredentials";
import { useUserStore } from "@/stores/userStore";
import { errorMessageAsString } from "@/utils/simple-error";

import LoadingSpan from "@/components/LoadingSpan.vue";
import ManageToolCredentials from "@/components/User/Credentials/ManageToolCredentials.vue";

interface Props {
    toolId: string;
    toolVersion: string;
}

const props = defineProps<Props>();

const userStore = useUserStore();
const userCredentialsStore = useUserCredentialsStore();
const {
    isBusy,
    hasUserProvidedRequiredCredentials,
    hasUserProvidedAllCredentials,
    hasSomeOptionalCredentials,
    hasSomeRequiredCredentials,
    checkUserCredentials,
} = useUserToolCredentials(props.toolId, props.toolVersion);

const busyMessage = ref<string>("");
const userCredentials = ref<UserCredentials[] | undefined>(undefined);

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

function toggleDialog() {
    showModal.value = !showModal.value;
}

async function onSavedCredentials(providedCredentials: CreateSourceCredentialsPayload) {
    showModal.value = false;
    busyMessage.value = "Saving your credentials";
    try {
        userCredentials.value = await userCredentialsStore.saveUserCredentialsForTool(providedCredentials);
    } catch (e) {
        Toast.error(`Error saving user credentials: ${errorMessageAsString(e)}`);
    }
}

async function onDeleteCredentialsGroup(serviceId: ServiceCredentialsIdentifier, groupName: string) {
    busyMessage.value = "Updating your credentials";
    try {
        userCredentialsStore.deleteCredentialsGroupForTool(props.toolId, props.toolVersion, serviceId, groupName);
    } catch (e) {
        Toast.error(`Error deleting user credentials group: ${errorMessageAsString(e)}`);
    }
}

function onUpdateUserCredentials(data?: UserCredentials[]) {
    userCredentials.value = data;
}

onMounted(async () => {
    if (userStore.isAnonymous) {
        return;
    }

    await checkUserCredentials();
});
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
            @onUpdateCredentialsList="onUpdateUserCredentials"
            @delete-credentials-group="onDeleteCredentialsGroup"
            @save-credentials="onSavedCredentials"
            @close="toggleDialog" />
    </div>
</template>
