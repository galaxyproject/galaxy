<script setup>
import ToolSource from "./ToolSource.vue";
import { useConfig } from "composables/config";
import { useCurrentUser } from "composables/user";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

const { config } = useConfig(true);
const { currentUser } = useCurrentUser(false, true);

const props = defineProps({
    toolId: {
        type: String,
        required: true,
    },
});
</script>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faEye } from "@fortawesome/free-regular-svg-icons";

library.add(faEye);
</script>

<template>
    <div v-if="config.enable_tool_source_display || (currentUser && currentUser.is_admin)">
        <b-dropdown-item v-b-modal.tool-source-viewer>
            <FontAwesomeIcon icon="far fa-eye" /><span v-localize>View Tool source</span>
        </b-dropdown-item>
        <b-modal id="tool-source-viewer" :title="`Tool Source for ${props.toolId}`" size="lg" ok-only ok-title="Close">
            <ToolSource :tool-id="props.toolId" />
        </b-modal>
    </div>
</template>
