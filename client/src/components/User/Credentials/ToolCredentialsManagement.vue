<script setup lang="ts">
import { BModal } from "bootstrap-vue";
import { computed, ref } from "vue";

import type { SelectCurrentGroupPayload, ServiceCredentialsIdentifier } from "@/api/users";
import { useUserToolCredentials } from "@/composables/userToolCredentials";
import { useToolStore } from "@/stores/toolStore";

import ServiceCredentials from "@/components/User/Credentials/ServiceCredentials.vue";

interface CurrentGroupIds {
    [serviceId: string]: string | undefined;
}

interface Props {
    toolId: string;
    toolVersion: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "close"): void;
}>();

const { getToolNameById } = useToolStore();

const { userServiceFor, sourceCredentialsDefinition, selectCurrentCredentialsGroups } = useUserToolCredentials(
    props.toolId,
    props.toolVersion
);

const okTitle = "Save Group Selection";
const toolName = getToolNameById(props.toolId);

const currentGroupIds = ref<CurrentGroupIds>(initCurrentGroupIds());

const serviceIdFor = computed(() => {
    return (sd: ServiceCredentialsIdentifier): string | undefined => {
        const service = userServiceFor.value(sd);
        return service?.id;
    };
});

function initCurrentGroupIds(): CurrentGroupIds {
    const ids: CurrentGroupIds = {};
    for (const sd of sourceCredentialsDefinition.value.services.values()) {
        const s = userServiceFor.value(sd);
        if (s) {
            ids[s.id] = s.current_group_id || undefined;
        }
    }
    return ids;
}

function onSelectCredentials() {
    const serviceCredentials: SelectCurrentGroupPayload[] = [];
    for (const serviceId of Object.keys(currentGroupIds.value)) {
        const groupId = currentGroupIds.value[serviceId];
        const sc: SelectCurrentGroupPayload = {
            user_credentials_id: serviceId,
            current_group_id: groupId || null,
        };
        serviceCredentials.push(sc);
    }
    selectCurrentCredentialsGroups(serviceCredentials);
}

function onCurrentGroupChange(serviceDefinition: ServiceCredentialsIdentifier, groupId?: string) {
    const serviceId = serviceIdFor.value(serviceDefinition);
    if (serviceId) {
        currentGroupIds.value[serviceId] = groupId;
    }
}

function serviceCurrentGroupFor(sd: ServiceCredentialsIdentifier): string | undefined {
    const serviceId = serviceIdFor.value(sd);
    if (serviceId) {
        return currentGroupIds.value[serviceId];
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
                :key="sd.name"
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

.manage-tool-credentials-footer {
    display: flex;
    gap: 1em;
    justify-content: space-between;
}
</style>
