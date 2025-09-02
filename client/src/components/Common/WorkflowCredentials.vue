<script setup lang="ts">
import { faCheck, faExclamation, faKey } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon, FontAwesomeLayers } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, onBeforeMount, ref } from "vue";

import type { ToolIdentifier } from "@/api/tools";
import { useUserMultiToolCredentials } from "@/composables/userMultiToolCredentials";
import { useUserStore } from "@/stores/userStore";
import { useUserToolsServiceCredentialsStore } from "@/stores/userToolsServiceCredentialsStore";

import WorkflowCredentialsManagement from "@/components/Common/WorkflowCredentialsManagement.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    toolIdentifiers: ToolIdentifier[];
}

const props = defineProps<Props>();

const userStore = useUserStore();

const { isBusy, busyMessage } = storeToRefs(useUserToolsServiceCredentialsStore());

const {
    hasUserProvidedAllRequiredToolsCredentials,
    hasUserProvidedAllToolsCredentials,
    hasSomeToolWithOptionalCredentials,
    hasSomeToolWithRequiredCredentials,
    statusVariant,
    checkAllUserCredentials,
} = useUserMultiToolCredentials(props.toolIdentifiers);

const showModal = ref(false);

const provideCredentialsButtonTitle = computed(() => {
    return hasUserProvidedAllRequiredToolsCredentials.value ? "Manage credentials" : "Provide credentials";
});

function toggleDialog() {
    showModal.value = !showModal.value;
}

onBeforeMount(async () => {
    if (userStore.isAnonymous) {
        return;
    }

    await checkAllUserCredentials();
});
</script>

<template>
    <div>
        <BAlert show :variant="statusVariant">
            <LoadingSpan v-if="isBusy" :message="busyMessage" />
            <div v-else-if="userStore.isAnonymous">
                <FontAwesomeIcon :icon="faKey" fixed-width />
                <span v-if="hasSomeToolWithRequiredCredentials">
                    <strong>
                        Some steps in this workflow require credentials to access its services and you need to be logged
                        in to provide them.
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
                            v-if="hasUserProvidedAllRequiredToolsCredentials"
                            :icon="faCheck"
                            fixed-width
                            transform="shrink-6 right-6 down-6" />
                        <FontAwesomeIcon v-else :icon="faExclamation" fixed-width transform="shrink-6 right-8 down-7" />
                    </FontAwesomeLayers>

                    <span v-if="hasUserProvidedAllRequiredToolsCredentials">
                        <strong>You have already provided credentials for this workflow.</strong> You can update or
                        delete your credentials, using the <i>{{ provideCredentialsButtonTitle }}</i> button.
                        <span v-if="hasSomeToolWithOptionalCredentials && !hasUserProvidedAllToolsCredentials">
                            <br />
                            You can still provide some optional credentials for this workflow.
                        </span>
                    </span>
                    <span v-else-if="hasSomeToolWithRequiredCredentials">
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

                <BButton variant="primary" size="sm" @click="toggleDialog">
                    {{ provideCredentialsButtonTitle }}
                </BButton>
            </div>
        </BAlert>
        <WorkflowCredentialsManagement
            v-if="showModal"
            :tool-identifiers="props.toolIdentifiers"
            @close="toggleDialog" />
    </div>
</template>
