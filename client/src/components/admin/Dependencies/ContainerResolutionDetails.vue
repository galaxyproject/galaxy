<template>
    <b-card>
        <div class="row">
            <div class="col">
                <span v-if="singleTool || resolution.tool_ids.length == 1">Tool</span>
                <span v-else>Tools</span>
            </div>
            <div class="col-8">
                <div v-if="singleTool">
                    <tool-display :tool-id="resolution.tool_id" />
                </div>
                <div v-else>
                    <tools :tool-ids="resolution.tool_ids" :compact="false" />
                </div>
            </div>
        </div>
        <div class="row">
            <div class="col">Requirements</div>
            <div class="col-8">
                <requirements :requirements="resolution.requirements" />
            </div>
        </div>
        <div class="row">
            <div class="col">Status Display</div>
            <div class="col-8">
                <status-display :status="resolution.status" :compact="false" />
            </div>
        </div>
        <div class="row">
            <div class="col">Container</div>
            <div class="col-8">
                <container-description
                    :container-description="resolution.status.container_description"
                    :compact="false" />
            </div>
        </div>
        <div class="row">
            <div class="col">Container Resolver</div>
            <div class="col-8">
                <container-resolver :container-resolver="resolution.status.container_resolver" :compact="false" />
            </div>
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
            required: true,
        },
    },
    computed: {
        singleTool: function () {
            return this.resolution.tool_id != undefined;
        },
    },
};
</script>
