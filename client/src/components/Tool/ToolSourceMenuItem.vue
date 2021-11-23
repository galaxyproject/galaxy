<template>
    <CurrentUser v-slot="{ user }">
        <ConfigProvider v-slot="{ config }">
            <template v-if="config.enable_tool_source_display || (user && user.is_admin)">
                <b-dropdown-item v-b-modal.tool-source-viewer
                    ><span class="fa fa-eye" /><span v-localize>View Tool source</span>
                </b-dropdown-item>
                <b-modal
                    id="tool-source-viewer"
                    :title="`Tool Source for ${toolId}`"
                    size="lg"
                    ok-only
                    ok-title="Close"
                >
                    <ToolSource :tool-id="toolId" />
                </b-modal>
            </template>
        </ConfigProvider>
    </CurrentUser>
</template>
<script>
import ConfigProvider from "components/providers/ConfigProvider";
import CurrentUser from "components/providers/CurrentUser";
import ToolSource from "components/Tool/ToolSource";

export default {
    components: {
        ConfigProvider,
        CurrentUser,
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
