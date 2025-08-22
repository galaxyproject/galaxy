<script setup lang="ts">
import { faCheck, faExclamation, faKey } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon, FontAwesomeLayers } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton } from "bootstrap-vue";
import { computed, onMounted, ref } from "vue";

import type { ToolIdentifier } from "@/composables/userMultiToolCredentials";
import { useUserMultiToolCredentials } from "@/composables/userMultiToolCredentials";
import { useUserStore } from "@/stores/userStore";

import WorkflowCredentialsManagement from "@/components/Common/WorkflowCredentialsManagement.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    toolIdentifiers: ToolIdentifier[];
}

const props = defineProps<Props>();

const userStore = useUserStore();

const {
    isAnyBusy,
    // TODO: Implement logic for aggregating credential states
    hasUserProvidedRequiredCredentials,
    hasUserProvidedAllCredentials,
    hasSomeOptionalCredentials,
    hasSomeRequiredCredentials,
    checkAllUserCredentials,
} = useUserMultiToolCredentials(props.toolIdentifiers);

const showModal = ref(false);

const provideCredentialsButtonTitle = computed(() => {
    return hasUserProvidedRequiredCredentials.value ? "Manage credentials" : "Provide credentials";
});
const bannerVariant = computed(() => {
    if (isAnyBusy.value) {
        return "info";
    }
    return hasUserProvidedRequiredCredentials.value ? "success" : "warning";
});

function toggleDialog() {
    showModal.value = !showModal.value;
}

onMounted(async () => {
    if (userStore.isAnonymous) {
        return;
    }

    await checkAllUserCredentials();
});
</script>

<template>
    <BAlert show :variant="bannerVariant">
        <LoadingSpan v-if="isAnyBusy" message="Processing credentials" />
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

            <BButton variant="primary" size="sm" @click="toggleDialog"> {{ provideCredentialsButtonTitle }} </BButton>

            <WorkflowCredentialsManagement
                v-if="showModal"
                :tool-identifiers="props.toolIdentifiers"
                @close="toggleDialog" />
        </div>
    </BAlert>
</template>
