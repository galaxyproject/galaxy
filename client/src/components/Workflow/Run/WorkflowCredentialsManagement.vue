<script setup lang="ts">
/**
 * WorkflowCredentialsManagement Component
 *
 * A modal component for managing credentials across multiple tools in a workflow.
 * Provides functionality to view, edit, and select credential groups for all tools
 * used in a workflow with batch operations and persistent selection.
 *
 * Features:
 * - Multi-tool credential management in a single interface
 * - Tool-specific credential group selection
 * - Batch credential group selection saving
 * - Service credentials creation and editing for each tool
 * - Persistent credential group changes
 * - Workflow-level credential coordination
 * - Modal interface with scrollable content
 *
 * @component WorkflowCredentialsManagement
 * @example
 * <WorkflowCredentialsManagement :show.sync="showModal" :tool-identifiers="toolIdentifiers" />
 */

import { faWrench } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed } from "vue";

import type { ToolIdentifier } from "@/api/tools";
import type { SelectCurrentGroupPayload, ServiceCredentialsIdentifier } from "@/api/userCredentials";
import { useUserMultiToolCredentials } from "@/composables/userMultiToolCredentials";
import { useToolStore } from "@/stores/toolStore";
import { useUserToolsServiceCredentialsStore } from "@/stores/userToolsServiceCredentialsStore";

import GModal from "@/components/BaseComponents/GModal.vue";
import Heading from "@/components/Common/Heading.vue";
import ServiceCredentials from "@/components/User/Credentials/ServiceCredentials.vue";

interface Props {
    /**
     * Whether to show the modal for managing credentials
     * @type {boolean}
     */
    show: boolean;
    /**
     * Array of tool identifiers for the workflow
     * @type {ToolIdentifier[]}
     */
    toolIdentifiers: ToolIdentifier[];
}

const props = defineProps<Props>();

/**
 * Events emitted to parent components
 */
const emit = defineEmits<{
    /**
     * Used to sync the prop `show` with the parent component when the modal is closed.
     * @event update:show
     */
    (e: "update:show", value: boolean): void;
}>();

const { getToolNameById } = useToolStore();

const userToolsServiceCredentialsStore = useUserToolsServiceCredentialsStore();
const { userToolsServicesCurrentGroupIds } = storeToRefs(userToolsServiceCredentialsStore);

const { userServiceForTool, sourceCredentialsDefinitionFor, selectCurrentCredentialsGroupsForTool } =
    useUserMultiToolCredentials(props.toolIdentifiers);

/** Button text for saving group selection */
const okTitle = "Save Group Selection";

/** Computed toggle that handles showing and hiding the modal */
const localShowToggle = computed({
    get: () => props.show,
    set: (value: boolean) => {
        emit("update:show", value);
    },
});

/**
 * Gets user service ID for a specific tool and service definition
 * @param {string} toolId - Tool ID
 * @param {string} toolVersion - Tool version
 * @param {ServiceCredentialsIdentifier} sd - Service credentials identifier
 * @returns {string | undefined} User service ID or undefined if not found
 */
const userToolServiceIdFor = computed(() => {
    return (toolId: string, toolVersion: string, sd: ServiceCredentialsIdentifier): string | undefined => {
        const userToolService = userServiceForTool.value(toolId, toolVersion, sd);
        return userToolService?.id;
    };
});

/**
 * Handles current group changes for a specific tool service
 * @param {string} toolId - Tool ID
 * @param {string} toolVersion - Tool version
 * @param {ServiceCredentialsIdentifier} serviceDefinition - Service definition
 * @param {string} [groupId] - New group ID, undefined to clear selection
 * @returns {void}
 */
function onToolServiceCurrentGroupChange(
    toolId: string,
    toolVersion: string,
    serviceDefinition: ServiceCredentialsIdentifier,
    groupId?: string,
): void {
    const userToolServiceCredentialsId = userToolServiceIdFor.value(toolId, toolVersion, serviceDefinition);
    if (userToolServiceCredentialsId) {
        userToolsServiceCredentialsStore.updateToolServiceCredentialsCurrentGroupId(
            toolId,
            toolVersion,
            userToolServiceCredentialsId,
            groupId,
        );
    }
}

/**
 * Saves credential group selections for all tools in the workflow
 * @returns {void}
 */
function onSelectCredentials(): void {
    for (const ti of props.toolIdentifiers) {
        const userToolKey = userToolsServiceCredentialsStore.getUserToolKey(ti.toolId, ti.toolVersion);
        const userToolServiceCurrentGroupIds = userToolsServicesCurrentGroupIds.value[userToolKey];
        if (userToolServiceCurrentGroupIds) {
            const serviceCredentials: SelectCurrentGroupPayload[] = [];
            for (const userToolServiceId of Object.keys(userToolServiceCurrentGroupIds)) {
                const newUserToolServiceGroupId = userToolServiceCurrentGroupIds[userToolServiceId];
                const sc: SelectCurrentGroupPayload = {
                    user_credentials_id: userToolServiceId,
                    current_group_id: newUserToolServiceGroupId || null,
                };
                serviceCredentials.push(sc);
            }
            selectCurrentCredentialsGroupsForTool(ti.toolId, ti.toolVersion, serviceCredentials);
        }
    }
}
</script>

<template>
    <GModal
        confirm
        :show.sync="localShowToggle"
        size="small"
        title="Manage & Select Credentials Groups for This Workflow"
        :ok-text="okTitle"
        fixed-height
        @ok="onSelectCredentials">
        <p class="mb-0">
            You can manage your credentials groups for each tool used in this workflow below. Any changes to credential
            groups will persist, but changes to the current group selection for services will only be saved when you
            click "{{ okTitle }}".
        </p>

        <div v-for="(ti, i) in props.toolIdentifiers" :key="i" class="mb-2">
            <Heading inline h6 size="sm" class="mb-2" separator>
                <FontAwesomeIcon :icon="faWrench" fixed-width />
                {{ getToolNameById(ti.toolId) }} - ({{ ti.toolVersion }})
            </Heading>

            <div class="px-2">
                <ServiceCredentials
                    v-for="sd in sourceCredentialsDefinitionFor(ti.toolId, ti.toolVersion).services.values()"
                    :id="`service-credentials-${sd.name}-${sd.version}`"
                    :key="sd.name + sd.version"
                    class="mb-2"
                    :source-id="ti.toolId"
                    :source-version="ti.toolVersion"
                    :service-definition="sd"
                    @update-current-group="
                        (groupId) => onToolServiceCurrentGroupChange(ti.toolId, ti.toolVersion, sd, groupId)
                    ">
                </ServiceCredentials>
            </div>
        </div>
    </GModal>
</template>
