<template>
    <b-card>
        <div v-if="singleTool">Tool: <tool-display :tool-id="resolution.tool_id" /></div>
        <div v-else>Tools: <tools :tool-ids="resolution.tool_ids" :compact="false" /></div>
        <div>Requirements: <requirements :requirements="resolution.requirements" /></div>
        <div>
            <status-display :status="resolution.status" :compact="false" />
        </div>
        <div>
            Container Description:
            <container-description :container-description="resolution.status.container_description" :compact="false" />
        </div>
        <div>
            Container Resolver:
            <container-resolver :container-resolver="resolution.status.container_resolver" :compact="false" />
        </div>
    </b-card>
</template>

<script>
import Requirements from "./Requirements";
import StatusDisplay from "./StatusDisplay";
import ContainerDescription from "./ContainerDescription";
import ContainerResolver from "./ContainerResolver";
import Tools from "./Tools";
import ToolDisplay from "./ToolDisplay";

export default {
    components: { ContainerDescription, ContainerResolver, Requirements, StatusDisplay, ToolDisplay, Tools },
    props: {
        resolution: {
            type: Object,
            required: true
        }
    },
    computed: {
        singleTool: function() {
            return this.resolution.tool_id != undefined;
        }
    }
};
</script>
