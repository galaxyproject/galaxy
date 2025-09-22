<script setup lang="ts">
import { faExclamation } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert } from "bootstrap-vue";
import { computed } from "vue";

import type { ServiceCredentialsContext } from "@/api/userCredentials";
import { useToolsServiceCredentialsDefinitionsStore } from "@/stores/toolsServiceCredentialsDefinitionsStore";
import { useUserToolsServiceCredentialsStore } from "@/stores/userToolsServiceCredentialsStore";

interface Props {
    toolId: string;
    toolVersion: string;
    jobCredentialsContext?: ServiceCredentialsContext[];
}

const props = defineProps<Props>();

const { getToolServiceCredentialsDefinitionLabelFor } = useToolsServiceCredentialsDefinitionsStore();

const { getToolService } = useUserToolsServiceCredentialsStore();

const currentSelectedIdsAreDifferent = computed(() => {
    if (!props.jobCredentialsContext) {
        return false;
    }
    for (const value of props.jobCredentialsContext) {
        const selectedGroup = value.selected_group;
        if (!selectedGroup.id) {
            return true;
        }
        const toolService = getToolService(props.toolId, props.toolVersion, {
            name: value.name,
            version: value.version,
        });
        if (toolService && toolService.current_group_id !== selectedGroup.id) {
            return true;
        }
    }
    return false;
});
</script>

<template>
    <BAlert v-if="currentSelectedIdsAreDifferent" show variant="warning" class="my-2">
        <FontAwesomeIcon :icon="faExclamation" fixed-width />

        <span v-for="value in props.jobCredentialsContext" :key="value.name + value.version">
            <template v-if="!value.selected_group.id">
                The <b>{{ value.selected_group.name }}</b> for
                <b>{{ getToolServiceCredentialsDefinitionLabelFor(props.toolId, props.toolVersion, value) }}</b>
                no longer exists. The current credentials group will be used instead.
            </template>
            <template v-else>
                Credential group changed for
                <b> {{ getToolServiceCredentialsDefinitionLabelFor(props.toolId, props.toolVersion, value) }}</b
                >. Previously used <b>{{ value.selected_group.name }} </b>.
            </template>
        </span>
    </BAlert>
</template>
