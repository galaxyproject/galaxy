<script setup lang="ts">
/**
 * ToolCredentials Component
 *
 * A comprehensive tool credentials interface that displays credential status,
 * provides management capabilities, and shows service-specific information.
 * Handles both required and optional credentials with visual indicators.
 *
 * Features:
 * - Credential status display with visual indicators
 * - Anonymous user handling with login prompts
 * - Required vs optional credential differentiation
 * - Service-specific credential group management
 * - Modal-based credential management interface
 * - Real-time credential status updates
 * - Contextual messaging based on credential state
 * - Job credentials context validation
 *
 * @component ToolCredentials
 * @example
 * <ToolCredentials
 *   :tool-id="toolId"
 *   :tool-version="toolVersion"
 *   :job-credentials-context="jobContext" />
 */

import { faCaretRight, faCheck, faExclamation, faKey } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon, FontAwesomeLayers } from "@fortawesome/vue-fontawesome";
import { BAlert, BBadge, BButton } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, onMounted, ref } from "vue";

import type { ServiceCredentialsContext } from "@/api/userCredentials";
import { Toast } from "@/composables/toast";
import { useUserToolCredentials } from "@/composables/userToolCredentials";
import { useUserStore } from "@/stores/userStore";
import { useUserToolsServiceCredentialsStore } from "@/stores/userToolsServiceCredentialsStore";

import LoadingSpan from "@/components/LoadingSpan.vue";
import ToolCredentialsContextCheck from "@/components/Tool/ToolCredentialsContextCheck.vue";
import ToolCredentialsManagement from "@/components/User/Credentials/ToolCredentialsManagement.vue";

/** Maps service names to their groups and requirements. */
type ServiceGroupMapping = {
    serviceName: string;
    isRequired: boolean;
    groupName?: string;
};

interface Props {
    /**
     * The ID of the tool to manage credentials for
     * @type {string}
     */
    toolId: string;

    /**
     * The version of the tool to manage credentials for
     * @type {string}
     */
    toolVersion: string;

    /**
     * Job credentials context from when a job was created
     * @type {ServiceCredentialsContext[] | undefined}
     */
    jobCredentialsContext?: ServiceCredentialsContext[];
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

/** Controls modal visibility for credential management. */
const showModal = ref(false);

/**
 * Dynamic button title based on credential state.
 * @returns {string} Button text for credential management.
 */
const provideCredentialsButtonTitle = computed(() => {
    return hasUserProvidedAllServiceCredentials.value ? "Manage credentials" : "Provide credentials";
});

/**
 * Service group mappings with selection status.
 * @returns {Array} Service definitions with current group selections.
 */
const currentServiceGroups = computed(() => {
    const mappings: ServiceGroupMapping[] = [];

    for (const serviceDefinition of sourceCredentialsDefinition.value.services.values()) {
        const userService = userServiceFor.value(serviceDefinition);

        let selectedGroup;
        if (userService?.current_group_id) {
            const group = userToolServiceCredentialsGroups.value[userService.current_group_id];
            selectedGroup = group?.name;
        }

        const serviceGroupMapping: ServiceGroupMapping = {
            serviceName: serviceDefinition.label || serviceDefinition.name,
            isRequired: !serviceDefinition.optional,
            groupName: selectedGroup,
        };

        mappings.push(serviceGroupMapping);
    }

    return mappings;
});

/**
 * Generates tooltip text for service badges.
 * @param {ServiceGroupMapping} serviceGroupMapping - Mapping of service to its group and requirement status.
 * @returns {string} Tooltip text describing the service status.
 */
function getBadgeTitle(serviceGroupMapping: ServiceGroupMapping): string {
    return `This service is ${serviceGroupMapping.isRequired ? "required" : "optional"} and you ${serviceGroupMapping.groupName ? "have selected the credentials group: " + serviceGroupMapping.groupName : "have not selected a credentials group for it."}`;
}

/**
 * Toggles the credential management modal.
 * @returns {void}
 */
function toggleDialog(): void {
    showModal.value = !showModal.value;
}

/**
 * Refreshes user credentials data.
 * @returns {Promise<void>}
 * @throws {Error} When credential loading fails.
 */
async function refreshCredentials(): Promise<void> {
    try {
        await checkUserCredentials();
    } catch (err) {
        Toast.error(`Could not load your credentials: ${err}`);
    }
}

/**
 * Loads credentials on component mount
 */
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
                            v-else-if="
                                !hasUserProvidedAllRequiredServiceCredentials ||
                                !hasUserProvidedSomeOptionalServiceCredentials
                            "
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

            <ToolCredentialsContextCheck
                :tool-id="props.toolId"
                :tool-version="props.toolVersion"
                :job-credentials-context="props.jobCredentialsContext" />

            <div v-if="!isAnonymous && currentServiceGroups" class="d-flex flex-wrap flex-gapx-1 flex-gapy-1">
                <div v-for="csg in currentServiceGroups" :key="csg.serviceName" class="d-flex align-items-center">
                    <BBadge
                        v-b-tooltip.hover
                        :title="getBadgeTitle(csg)"
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
