<script setup>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faEye } from "@fortawesome/free-regular-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useConfig } from "composables/config";
import { storeToRefs } from "pinia";

import { useUserStore } from "@/stores/userStore";

import ToolSource from "./ToolSource.vue";

library.add(faEye);

const { config } = useConfig(true);
const { currentUser } = storeToRefs(useUserStore());

const props = defineProps({
    toolId: {
        type: String,
        required: true,
    },
});
</script>

<template>
    <div v-if="config.enable_tool_source_display || (currentUser && currentUser.is_admin)">
        <b-dropdown-item v-b-modal.tool-source-viewer>
            <FontAwesomeIcon icon="far fa-eye" /><span v-localize>查看工具源码</span>
        </b-dropdown-item>
        <b-modal id="tool-source-viewer" :title="`工具源码: ${props.toolId}`" size="lg" ok-only ok-title="关闭">
            <ToolSource :tool-id="props.toolId" />
        </b-modal>
    </div>
</template>
