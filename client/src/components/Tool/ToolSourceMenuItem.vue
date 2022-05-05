<template>
    <CurrentUser v-slot="{ user }">
        <ConfigProvider v-slot="{ config }">
            <div v-if="config.enable_tool_source_display || (user && user.is_admin)">
                <b-dropdown-item v-b-modal.tool-source-viewer
                    ><span class="fa fa-eye" /><span v-localize>View Tool source</span>
                </b-dropdown-item>
                <b-modal
                    id="tool-source-viewer"
                    :title="`Tool Source for ${toolId}`"
                    size="lg"
                    ok-only
                    ok-title="Close">
                    <ToolSource :tool-id="toolId" />
                </b-modal>
            </div>
        </ConfigProvider>
    </CurrentUser>
</template>
<script>
import ConfigProvider from "components/providers/ConfigProvider";
import CurrentUser from "components/providers/CurrentUser";
import ToolSource from "./ToolSource.vue";

export default {
    components: {
        ConfigProvider,
        CurrentUser,
        // dynamically import toolsource component
        ToolSource,
    },
    props: {
        toolId: {
            type: String,
            required: true,
        },
    },
};
</script>
