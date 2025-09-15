<script setup lang="ts">
import { faWrench } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BModal } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed } from "vue";

import type { ToolIdentifier } from "@/api/tools";
import type { SelectCurrentGroupPayload, ServiceCredentialsIdentifier } from "@/api/users";
import { useUserMultiToolCredentials } from "@/composables/userMultiToolCredentials";
import { useToolStore } from "@/stores/toolStore";
import { useUserToolsServiceCredentialsStore } from "@/stores/userToolsServiceCredentialsStore";

import Heading from "@/components/Common/Heading.vue";
import ServiceCredentials from "@/components/User/Credentials/ServiceCredentials.vue";

interface Props {
    toolIdentifiers: ToolIdentifier[];
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "close"): void;
}>();

const { getToolNameById } = useToolStore();

const userToolsServiceCredentialsStore = useUserToolsServiceCredentialsStore();
const { userToolsServicesCurrentGroupIds } = storeToRefs(userToolsServiceCredentialsStore);

const { userServiceForTool, sourceCredentialsDefinitionFor, selectCurrentCredentialsGroupsForTool } =
    useUserMultiToolCredentials(props.toolIdentifiers);

const okTitle = "Save Group Selection";

const userToolServiceIdFor = computed(() => {
    return (toolId: string, toolVersion: string, sd: ServiceCredentialsIdentifier): string | undefined => {
        const userToolService = userServiceForTool.value(toolId, toolVersion, sd);
        return userToolService?.id;
    };
});

function onToolServiceCurrentGroupChange(
    toolId: string,
    toolVersion: string,
    serviceDefinition: ServiceCredentialsIdentifier,
    groupId?: string,
) {
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

function onSelectCredentials() {
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
    <BModal
        visible
        scrollable
        no-close-on-backdrop
        no-close-on-esc
        button-size="md"
        size="lg"
        modal-class="manage-workflow-credentials-modal"
        body-class="manage-workflow-credentials-body"
        title="Manage & Select Credentials Groups for This Workflow"
        :ok-title="okTitle"
        cancel-title="Close"
        cancel-variant="outline-danger"
        @ok="onSelectCredentials"
        @close="emit('close')">
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
    </BModal>
</template>

<style>
.manage-workflow-credentials-body {
    height: 80vh;
}
</style>
