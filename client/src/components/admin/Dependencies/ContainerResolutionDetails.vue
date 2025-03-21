<template>
    <b-card>
        <div class="row">
            <div class="col">
                <span v-if="singleTool || resolution.tool_ids.length == 1">工具</span>
                <span v-else>工具列表</span>
            </div>
            <div class="col-8">
                <div v-if="singleTool">
                    <ToolDisplay :tool-id="resolution.tool_id" />
                </div>
                <div v-else>
                    <Tools :tool-ids="resolution.tool_ids" :compact="false" />
                </div>
            </div>
        </div>
        <div class="row">
            <div class="col">需求</div>
            <div class="col-8">
                <Requirements :requirements="resolution.requirements" />
            </div>
        </div>
        <div class="row">
            <div class="col">状态展示</div>
            <div class="col-8">
                <StatusDisplay :status="resolution.status" :compact="false" />
            </div>
        </div>
        <div class="row">
            <div class="col">容器</div>
            <div class="col-8">
                <ContainerDescription
                    :container-description="resolution.status.container_description"
                    :compact="false" />
            </div>
        </div>
        <div class="row">
            <div class="col">容器解析器</div>
            <div class="col-8">
                <ContainerResolver :container-resolver="resolution.status.container_resolver" :compact="false" />
            </div>
        </div>
    </b-card>
</template>


<script>
import ContainerDescription from "./ContainerDescription";
import ContainerResolver from "./ContainerResolver";
import Requirements from "./Requirements";
import StatusDisplay from "./StatusDisplay";
import ToolDisplay from "./ToolDisplay";
import Tools from "./Tools";

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
