<script setup lang="ts">
/**
 * ToolCredentialsManagement Component
 *
 * A modal component for managing user service credentials for a specific tool.
 * This component provides an interface for users to create, edit, and select
 * credential groups for various services required by a tool.
 *
 * Features:
 * - Modal interface for credential management
 * - Service credentials creation and editing
 * - Current group selection for tool execution
 * - Accordion layout for multiple service credentials
 * - Persistent credential group changes
 * - Selective group assignment for tool execution
 * - Real-time validation and state management
 *
 * @component ToolCredentialsManagement
 * @example
 * <ToolCredentialsManagement
 *   :tool-id="toolId"
 *   :tool-version="toolVersion"
 *   @close="onModalClose" />
 */

import { BModal } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, onBeforeMount } from "vue";

import type { SelectCurrentGroupPayload, ServiceCredentialsIdentifier } from "@/api/userCredentials";
import { useUserToolCredentials } from "@/composables/userToolCredentials";
import { useToolStore } from "@/stores/toolStore";
import { useUserToolsServiceCredentialsStore } from "@/stores/userToolsServiceCredentialsStore";

import ServiceCredentials from "@/components/User/Credentials/ServiceCredentials.vue";

interface Props {
    /**
     * The ID of the tool for which to manage credentials
     * @type {string}
     */
    toolId: string;

    /**
     * The version of the tool for which to manage credentials
     * @type {string}
     */
    toolVersion: string;
}

const props = defineProps<Props>();

/**
 * Events emitted to parent components
 */
const emit = defineEmits<{
    /**
     * Emitted when the modal should be closed
     * @event close
     */
    (e: "close"): void;
}>();

const { getToolNameById } = useToolStore();

const userToolsServiceCredentialsStore = useUserToolsServiceCredentialsStore();
const { userToolsServicesCurrentGroupIds } = storeToRefs(userToolsServiceCredentialsStore);

const { userServiceFor, sourceCredentialsDefinition, selectCurrentCredentialsGroups } = useUserToolCredentials(
    props.toolId,
    props.toolVersion,
);

/** Button text for saving group selection. */
const okTitle = "Save Group Selection";

/** Display name of the tool. */
const toolName = getToolNameById(props.toolId);

/** Unique key for the current tool. */
const userToolKey = userToolsServiceCredentialsStore.getUserToolKey(props.toolId, props.toolVersion);

/** Current group IDs for services of this tool. */
const userToolServicesCurrentGroupIds = computed(() => {
    return userToolsServicesCurrentGroupIds.value[userToolKey] || {};
});

/** Gets user service ID for a specific service credentials identifier. */
const userToolServiceIdFor = computed(() => {
    /**
     * @param {ServiceCredentialsIdentifier} sci - Service credentials identifier.
     * @returns {string | undefined} User service ID or undefined if not found.
     */
    return (sci: ServiceCredentialsIdentifier): string | undefined => {
        const userToolService = userServiceFor.value(sci);
        return userToolService?.id;
    };
});

/**
 * Handles the selection of current credentials groups for the tool.
 * Builds the payload from current group selections and submits it.
 * @function onSelectCredentials
 */
function onSelectCredentials(): void {
    if (Object.keys(userToolServicesCurrentGroupIds.value).length === 0) {
        return;
    }

    const serviceCredentials: SelectCurrentGroupPayload[] = [];
    for (const userToolServiceId of Object.keys(userToolServicesCurrentGroupIds.value)) {
        const newUserToolServiceGroupId = userToolServicesCurrentGroupIds.value[userToolServiceId];
        const sc: SelectCurrentGroupPayload = {
            user_credentials_id: userToolServiceId,
            current_group_id: newUserToolServiceGroupId || null,
        };
        serviceCredentials.push(sc);
    }
    selectCurrentCredentialsGroups(serviceCredentials);
}

/**
 * Handles changes to the current group selection for a service.
 * Updates the store with the new group selection.
 * @param {ServiceCredentialsIdentifier} serviceDefinition - The service definition.
 * @param {string} [groupId] - The selected group ID (undefined to deselect).
 * @function onCurrentGroupChange
 */
function onCurrentGroupChange(serviceDefinition: ServiceCredentialsIdentifier, groupId?: string): void {
    const userServiceCredentialsId = userToolServiceIdFor.value(serviceDefinition);
    if (userServiceCredentialsId) {
        userToolsServiceCredentialsStore.updateToolServiceCredentialsCurrentGroupId(
            props.toolId,
            props.toolVersion,
            userServiceCredentialsId,
            groupId,
        );
    }
}

/**
 * Initialize current group IDs before component mounts
 */
onBeforeMount(() => {
    userToolsServiceCredentialsStore.initToolsCurrentGroupIds();
});
</script>

<template>
    <BModal
        visible
        scrollable
        no-close-on-backdrop
        no-close-on-esc
        button-size="md"
        size="lg"
        modal-class="manage-tool-credentials-modal"
        body-class="manage-tool-credentials-body"
        :title="`Manage & Select Credentials Groups for: ${toolName} (${props.toolVersion})`"
        :ok-title="okTitle"
        cancel-title="Close"
        cancel-variant="outline-danger"
        @ok="onSelectCredentials"
        @hide="emit('close')">
        <p>
            You can manage your credentials here. Any changes to credential groups will persist, but changes to the
            current group selection for services will only be saved when you click "{{ okTitle }}".
        </p>

        <div class="accordion">
            <ServiceCredentials
                v-for="sd in sourceCredentialsDefinition.services.values()"
                :id="`service-credentials-${sd.name}-${sd.version}`"
                :key="sd.name + sd.version"
                class="mb-2"
                :source-id="props.toolId"
                :source-version="props.toolVersion"
                :service-definition="sd"
                @update-current-group="(groupId) => onCurrentGroupChange(sd, groupId)" />
        </div>
    </BModal>
</template>

<style>
.manage-tool-credentials-body {
    height: 80vh;
}
</style>
