<script setup lang="ts">
import { faCheck, faExclamation, faKey } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon, FontAwesomeLayers } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, onMounted, ref } from "vue";

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

const { isAnonymous } = storeToRefs(useUserStore());

const { isBusy, busyMessage } = storeToRefs(useUserToolsServiceCredentialsStore());

const {
    statusVariant,
    someToolsHasRequiredServiceCredentials,
    hasUserProvidedAllToolsServiceCredentials,
    hasUserProvidedAllRequiredToolsServiceCredentials,
    hasUserProvidedSomeOptionalToolsServiceCredentials,
    checkAllUserCredentials,
} = useUserMultiToolCredentials(props.toolIdentifiers);

const showModal = ref(false);

const provideCredentialsButtonTitle = computed(() => {
    return hasUserProvidedAllToolsServiceCredentials.value ? "Manage credentials" : "Provide credentials";
});

function toggleDialog() {
    showModal.value = !showModal.value;
}

onMounted(async () => {
    await checkAllUserCredentials();
});
</script>

<template>
    <div>
        <BAlert show :variant="statusVariant">
            <LoadingSpan v-if="isBusy" :message="busyMessage" />
            <div v-else-if="isAnonymous">
                <FontAwesomeIcon :icon="faKey" fixed-width />
                <span v-if="someToolsHasRequiredServiceCredentials">
                    Some steps in this workflow <strong>require credentials</strong> to access its services and you need
                    to be logged in to provide them.
                </span>
                <span v-else>
                    Some steps in this workflow <strong>can use additional credentials</strong> to access its services
                    <strong>or tools will use their default values</strong>.
                </span>
                Please <a href="/login/start">log in or register here</a>.
            </div>
            <div v-else class="d-flex justify-content-between align-items-center">
                <div>
                    <FontAwesomeLayers class="mr-1">
                        <FontAwesomeIcon :icon="faKey" fixed-width />
                        <FontAwesomeIcon
                            v-if="hasUserProvidedAllToolsServiceCredentials"
                            :icon="faCheck"
                            fixed-width
                            transform="shrink-6 right-6 down-6" />
                        <FontAwesomeIcon
                            v-else-if="hasUserProvidedAllRequiredToolsServiceCredentials"
                            :icon="faExclamation"
                            fixed-width
                            transform="shrink-6 right-8 down-7" />
                    </FontAwesomeLayers>

                    <span v-if="hasUserProvidedAllToolsServiceCredentials">
                        <strong>You have already provided credentials for this workflow.</strong> You can update or
                        delete your credentials, using the <i>{{ provideCredentialsButtonTitle }}</i> button.
                    </span>
                    <span v-else-if="someToolsHasRequiredServiceCredentials">
                        <span v-if="hasUserProvidedAllRequiredToolsServiceCredentials">
                            You have provided <strong>all the required credentials</strong> for this workflow, but you
                            can still provide some other optional credentials for this workflow.
                        </span>
                        <span v-else>
                            This workflow <strong>requires you to enter credentials</strong> to access its services.
                            Please provide your credentials before using the workflow using the
                            <i>{{ provideCredentialsButtonTitle }}</i> button.
                        </span>
                    </span>
                    <span v-else-if="hasUserProvidedSomeOptionalToolsServiceCredentials">
                        You have provided <strong>some optional credentials</strong> for this workflow, but you can
                        still provide more optional credentials for this workflow.
                    </span>
                    <span v-else>
                        This workflow <strong>can use credentials</strong> to access its services. If you don't provide
                        credentials, you can still use the workflow, and the tools will use their default values.
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
