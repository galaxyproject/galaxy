<script setup>
import { faEye } from "@fortawesome/free-regular-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";

import { useConfig } from "@/composables/config";
import { useUserStore } from "@/stores/userStore";

import ToolSource from "./ToolSource.vue";

const { config } = useConfig(true);
const { currentUser } = storeToRefs(useUserStore());

const props = defineProps({
    toolId: {
        type: String,
        required: true,
    },
    toolUuid: {
        type: String,
        default: null,
    },
});
</script>

<template>
    <div v-if="config.enable_tool_source_display || (currentUser && currentUser.is_admin)">
        <b-dropdown-item v-b-modal.tool-source-viewer>
            <FontAwesomeIcon :icon="faEye" /><span v-localize>View Tool source</span>
        </b-dropdown-item>
        <b-modal
            id="tool-source-viewer"
            modal-class="tool-source-modal"
            :title="`Tool Source for ${props.toolId}`"
            ok-only
            ok-title="Close">
            <ToolSource :tool-id="props.toolId" :tool-uuid="props.toolUuid" />
        </b-modal>
    </div>
</template>

<style lang="scss">
#tool-source-viewer {
    .modal-dialog {
        width: 85%;
        max-width: 100%;
    }
}
</style>
