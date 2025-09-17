<script setup lang="ts">
import { BModal } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, onBeforeMount } from "vue";

import type { SelectCurrentGroupPayload, ServiceCredentialsIdentifier } from "@/api/userCredentials";
import { useUserToolCredentials } from "@/composables/userToolCredentials";
import { useToolStore } from "@/stores/toolStore";
import { useUserToolsServiceCredentialsStore } from "@/stores/userToolsServiceCredentialsStore";

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

const userToolsServiceCredentialsStore = useUserToolsServiceCredentialsStore();
const { userToolsServicesCurrentGroupIds } = storeToRefs(userToolsServiceCredentialsStore);

const { userServiceFor, sourceCredentialsDefinition, selectCurrentCredentialsGroups } = useUserToolCredentials(
    props.toolId,
    props.toolVersion,
);

const okTitle = "Save Group Selection";
const toolName = getToolNameById(props.toolId);
const userToolKey = userToolsServiceCredentialsStore.getUserToolKey(props.toolId, props.toolVersion);

const userToolServicesCurrentGroupIds = computed(() => {
    return userToolsServicesCurrentGroupIds.value[userToolKey] || {};
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
                @update-current-group="(groupId) => onCurrentGroupChange(sd, groupId)" />
        </div>
    </BModal>
</template>

<style>
.manage-tool-credentials-body {
    height: 80vh;
}
</style>
