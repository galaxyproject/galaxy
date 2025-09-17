<script setup lang="ts">
import { faCaretRight, faCheck, faExclamation, faKey } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon, FontAwesomeLayers } from "@fortawesome/vue-fontawesome";
import { BAlert, BBadge, BButton } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, onMounted, ref } from "vue";

import { Toast } from "@/composables/toast";
import { useUserToolCredentials } from "@/composables/userToolCredentials";
import { useUserStore } from "@/stores/userStore";
import { useUserToolsServiceCredentialsStore } from "@/stores/userToolsServiceCredentialsStore";

import LoadingSpan from "@/components/LoadingSpan.vue";
import ToolCredentialsManagement from "@/components/User/Credentials/ToolCredentialsManagement.vue";

interface Props {
    toolId: string;
    toolVersion: string;
}

const props = defineProps<Props>();

const { isAnonymous } = storeToRefs(useUserStore());

const { isBusy, busyMessage, userToolServiceCredentialsGroups } = storeToRefs(useUserToolsServiceCredentialsStore());

const {
    statusVariant,
    userServiceFor,
    sourceCredentialsDefinition,
    toolHasRequiredServiceCredentials,
    hasUserProvidedAllServiceCredentials,
    hasUserProvidedAllRequiredServiceCredentials,
    hasUserProvidedSomeOptionalServiceCredentials,
    checkUserCredentials,
} = useUserToolCredentials(props.toolId, props.toolVersion);

const showModal = ref(false);

const provideCredentialsButtonTitle = computed(() => {
    return hasUserProvidedAllServiceCredentials.value ? "Manage credentials" : "Provide credentials";
});

const currentServiceGroups = computed(() => {
    const mappings: {
        serviceName: string;
        isRequired: boolean;
        groupName?: string;
    }[] = [];

    for (const serviceDefinition of sourceCredentialsDefinition.value.services.values()) {
        const userService = userServiceFor.value(serviceDefinition);

        let selectedGroup;
        if (userService?.current_group_id) {
            const group = userToolServiceCredentialsGroups.value[userService.current_group_id];
            selectedGroup = group?.name;
        }

        mappings.push({
            serviceName: serviceDefinition.label || serviceDefinition.name,
            isRequired: !serviceDefinition.optional,
            groupName: selectedGroup,
        });
    }

    return mappings;
});

function getBadgeTitle(isRequired: boolean, groupName?: string) {
    return `This service is ${isRequired ? "required" : "optional"} and you ${groupName ? "have selected the credentials group: " + groupName : "have not selected a credentials group for it."}`;
}

function toggleDialog() {
    showModal.value = !showModal.value;
}

async function refreshCredentials() {
    try {
        await checkUserCredentials();
    } catch (err) {
        Toast.error(`Could not load your credentials: ${err}`);
    }
}

onMounted(async () => {
    await refreshCredentials();
});
</script>

<template>
    <div class="mt-2">
        <BAlert show :variant="statusVariant" class="d-flex flex-column flex-gapy-1">
            <LoadingSpan v-if="isBusy" :message="busyMessage" />
            <div v-else-if="isAnonymous">
                <span v-if="toolHasRequiredServiceCredentials">
                    This tool <strong>requires credentials</strong> to access its services and you need to be logged in
                    to provide them.
                </span>
                <span v-else>
                    This tool <strong>can use additional credentials</strong> to access its services
                    <strong>or the tool will use its default values.</strong>
                </span>
                Please <a href="/login/start">log in or register here</a>.
            </div>
            <div v-else class="d-flex justify-content-between align-items-center">
                <div>
                    <FontAwesomeLayers class="mr-1">
                        <FontAwesomeIcon :icon="faKey" fixed-width />
                        <FontAwesomeIcon
                            v-if="hasUserProvidedAllServiceCredentials"
                            :icon="faCheck"
                            fixed-width
                            transform="shrink-6 right-6 down-6" />
                        <FontAwesomeIcon
                            v-else-if="hasUserProvidedAllRequiredServiceCredentials"
                            :icon="faExclamation"
                            fixed-width
                            transform="shrink-6 right-8 down-7" />
                    </FontAwesomeLayers>

                    <span v-if="hasUserProvidedAllServiceCredentials">
                        <strong>You have already provided credentials for this tool.</strong> You can update or delete
                        your credentials using the <i>{{ provideCredentialsButtonTitle }}</i> button.
                    </span>
                    <span v-else-if="toolHasRequiredServiceCredentials">
                        <span v-if="hasUserProvidedAllRequiredServiceCredentials">
                            You have provided <strong>all the required credentials</strong> for this tool, but you can
                            still provide some other optional credentials for this tool.
                        </span>
                        <span v-else>
                            This tool <strong>requires you to enter credentials</strong> to access its services. Please
                            provide your credentials before using the tool using the
                            <i>{{ provideCredentialsButtonTitle }}</i> button.
                        </span>
                    </span>
                    <span v-else-if="hasUserProvidedSomeOptionalServiceCredentials">
                        You have provided <strong>some optional credentials</strong> for this tool, but you can still
                        provide more optional credentials for this tool.
                    </span>
                    <span v-else>
                        This tool <strong>can use credentials</strong> to access its services. If you don't provide
                        credentials, you can still use the tool, and the tool will use its default values.
                    </span>
                </div>

                <div>
                    <BButton variant="primary" size="sm" @click="toggleDialog">
                        {{ provideCredentialsButtonTitle }}
                    </BButton>
                </div>
            </div>

            <div v-if="!isAnonymous && currentServiceGroups" class="d-flex flex-wrap flex-gapx-1 flex-gapy-1">
                <div v-for="csg in currentServiceGroups" :key="csg.serviceName" class="d-flex align-items-center">
                    <BBadge
                        v-b-tooltip.hover
                        :title="getBadgeTitle(csg.isRequired, csg.groupName)"
                        :variant="csg.isRequired ? 'primary' : 'secondary'">
                        <FontAwesomeIcon :icon="csg.groupName ? faCheck : faExclamation" fixed-width />
                        {{ csg.serviceName }}
                        <FontAwesomeIcon :icon="faCaretRight" class="mx-1" />
                        <span v-if="csg.groupName">{{ csg.groupName }}</span>
                        <em v-else>
                            {{ csg.isRequired ? "Required - No group selected" : "Optional - No group selected" }}
                        </em>
                    </BBadge>
                </div>
            </div>
        </BAlert>

        <ToolCredentialsManagement
            v-if="showModal"
            :tool-id="props.toolId"
            :tool-version="props.toolVersion"
            @close="toggleDialog" />
    </div>
</template>
