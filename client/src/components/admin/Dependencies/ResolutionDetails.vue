<template>
    <div v-if="isContainerResolution">
        <container-resolution-details :resolution="containerResolution" />
    </div>
    <b-card v-else>
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
        <div v-if="resolution.status.length == 0" class="row">
            <i><b>No requirements to resolve, no explicit dependency resolution configured.</b></i>
        </div>
        <span v-else-if="!separateDetails">
            <div class="row">
                <div class="col">Requirements</div>
                <div class="col-8">
                    <requirements :requirements="resolution.requirements" />
                </div>
            </div>
            <div class="row">
                <div class="col">Status</div>
                <div class="col-8">
                    <status-display :status="resolution.status[0]" :compact="false" :all-statuses="resolution.status" />
                </div>
            </div>
            <div class="row">
                <div class="col">Dependency Resolver</div>
                <div class="col-8">
                    <dependency-resolver :dependency-resolver="resolution.status[0].dependency_resolver" />
                </div>
            </div>
        </span>
        <div v-else>
            <span v-for="(requirements, index) in resolution.requirements" :key="index">
                <div class="row">
                    <div class="col">
                        <requirement :requirement="resolution.requirements[index]" />
                    </div>
                    <div class="col">
                        <div class="row">
                            <div class="col">Status</div>
                            <div class="col">
                                <status-display :status="resolution.status[index]" :compact="false" />
                            </div>
                        </div>
                        <div class="row">
                            <div class="col">Dependency Resolver</div>
                            <div class="col">
                                <dependency-resolver
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
import DependencyResolver from "./DependencyResolver";
import Requirements from "./Requirements";
import Requirement from "./Requirement";
import StatusDisplay from "./StatusDisplay";
import ContainerResolutionDetails from "./ContainerResolutionDetails";
import Tools from "./Tools";
import ToolDisplay from "./ToolDisplay";

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
