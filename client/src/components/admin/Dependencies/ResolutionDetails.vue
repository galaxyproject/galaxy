<template>
    <div v-if="isContainerResolution">
        <ContainerResolutionDetails :resolution="containerResolution" />
    </div>
    <b-card v-else>
        <div class="row">
            <div class="col">
                <span v-if="singleTool || resolution.tool_ids.length == 1">工具</span>
                <span v-else>工具集</span>
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
        <div v-if="resolution.status.length == 0" class="row">
            <i><b>没有需要解决的需求，未配置显式的依赖解析。</b></i>
        </div>
        <span v-else-if="!separateDetails">
            <div class="row">
                <div class="col">需求</div>
                <div class="col-8">
                    <Requirements :requirements="resolution.requirements" />
                </div>
            </div>
            <div class="row">
                <div class="col">状态</div>
                <div class="col-8">
                    <StatusDisplay :status="resolution.status[0]" :compact="false" :all-statuses="resolution.status" />
                </div>
            </div>
            <div class="row">
                <div class="col">依赖解析器</div>
                <div class="col-8">
                    <DependencyResolver :dependency-resolver="resolution.status[0].dependency_resolver" />
                </div>
            </div>
        </span>
        <div v-else>
            <span v-for="(requirements, index) in resolution.requirements" :key="index">
                <div class="row">
                    <div class="col">
                        <Requirement :requirement="resolution.requirements[index]" />
                    </div>
                    <div class="col">
                        <div class="row">
                            <div class="col">状态</div>
                            <div class="col">
                                <StatusDisplay :status="resolution.status[index]" :compact="false" />
                            </div>
                        </div>
                        <div class="row">
                            <div class="col">依赖解析器</div>
                            <div class="col">
                                <DependencyResolver
                                    :dependency-resolver="resolution.status[index].dependency_resolver" />
                            </div>
                        </div>
                    </div>
                </div>
            </span>
        </div>
    </b-card>
</template>
<script>
import ContainerResolutionDetails from "./ContainerResolutionDetails";
import DependencyResolver from "./DependencyResolver";
import Requirement from "./Requirement";
import Requirements from "./Requirements";
import StatusDisplay from "./StatusDisplay";
import ToolDisplay from "./ToolDisplay";
import Tools from "./Tools";

export default {
    components: {
        ContainerResolutionDetails,
        DependencyResolver,
        Requirement,
        Requirements,
        StatusDisplay,
        ToolDisplay,
        Tools,
    },
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
        isContainerResolution: function () {
            return this.resolution.status.length >= 1 && this.resolution.status[0].model_class == "ContainerDependency";
        },
        containerResolution: function () {
            return { ...this.resolution, status: this.resolution.status[0] };
        },
        /*
        resolutionOkay: function() {
            let anyUnresolved = this.resolution.status.length != 0;  // odd logic here, but we call no requirements unresolved in the GUI :(
            for( const status of this.resolution.status ) {
                anyUnresolved = anyUnresolved || status.dependency_type == null;                    
            }
            return !anyUnresolved;
        },
        */
        separateDetails: function () {
            return (
                this.resolution.status.length > 1 && this.resolution.status[0].model_class != "MergedCondaDependency"
            );
        },
    },
};
</script>
