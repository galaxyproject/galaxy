<script setup lang="ts">
import { BModal } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, onBeforeMount } from "vue";

import { getToolKey } from "@/api/tools";
import type { SelectCurrentGroupPayload, ServiceCredentialsIdentifier } from "@/api/users";
import { useUserToolCredentials } from "@/composables/userToolCredentials";
import { useToolStore } from "@/stores/toolStore";
import { useUserToolsServicesStore } from "@/stores/userToolsServicesStore";

import ServiceCredentials from "@/components/User/Credentials/ServiceCredentials.vue";

interface Props {
    toolId: string;
    toolVersion: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "close"): void;
}>();

const { getToolNameById } = useToolStore();

const userToolsServicesStore = useUserToolsServicesStore();
const { userToolsServicesCurrentGroupIds } = storeToRefs(userToolsServicesStore);

const { userServiceFor, sourceCredentialsDefinition, selectCurrentCredentialsGroups } = useUserToolCredentials(
    props.toolId,
    props.toolVersion
);

const okTitle = "Save Group Selection";
const toolName = getToolNameById(props.toolId);
const toolKey = getToolKey(props.toolId, props.toolVersion);

const userToolServicesCurrentGroupIds = computed(() => {
    return userToolsServicesCurrentGroupIds.value[toolKey] || {};
});

const userToolServiceIdFor = computed(() => {
    return (sd: ServiceCredentialsIdentifier): string | undefined => {
        const userToolService = userServiceFor.value(sd);
        return userToolService?.id;
    };
});

function onSelectCredentials() {
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

function onCurrentGroupChange(serviceDefinition: ServiceCredentialsIdentifier, groupId?: string) {
    const userToolServiceId = userToolServiceIdFor.value(serviceDefinition);
    const userToolServiceCurrentGroupIds = userToolsServicesCurrentGroupIds.value[toolKey];
    if (userToolServiceId && userToolServiceCurrentGroupIds) {
        userToolServiceCurrentGroupIds[userToolServiceId] = groupId;
    }
}

const serviceCurrentGroupFor = computed(() => (sd: ServiceCredentialsIdentifier): string | undefined => {
    const userToolServiceId = userToolServiceIdFor.value(sd);
    if (userToolServiceId) {
        return userToolServicesCurrentGroupIds.value[userToolServiceId];
    }
});

onBeforeMount(() => {
    userToolsServicesStore.initToolsCurrentGroupIds();
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
        @close="emit('close')">
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
                :service-current-group-id="serviceCurrentGroupFor(sd)"
                @update-current-group="(groupId) => onCurrentGroupChange(sd, groupId)" />
        </div>
    </BModal>
</template>

<style>
.manage-tool-credentials-body {
    height: 80vh;
}
</style>
