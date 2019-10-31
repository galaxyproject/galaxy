<template>
    <div v-if="isContainerResolution">
        <container-resolution-details :resolution="containerResolution" />
    </div>
    <b-card v-else>
        <div>
            <div v-if="singleTool">Tool: <tool-display :tool-id="resolution.tool_id" /></div>
            <div v-else>Tools: <tools :tool-ids="resolution.tool_ids" :compact="false" /></div>
            <div v-if="resolution.status.length == 0">
                <i><b>No requirements to resolve, no explicit dependency resolution configured.</b></i>
            </div>
            <div v-else-if="!separateDetails">
                <div>Requirements: <requirements :requirements="resolution.requirements" /></div>
                <status-display :status="resolution.status[0]" :compact="false" :all-statuses="resolution.status" />
                <div>
                    Dependency Resolver:
                    <dependency-resolver :dependency-resolver="resolution.status[0].dependency_resolver" />
                </div>
            </div>
            <div v-else>
                <div :key="index" v-for="(requirements, index) in resolution.requirements">
                    Requirement: <requirement :requirement="resolution.requirements[index]" />
                    <status-display :status="resolution.status[index]" :compact="false" />
                    Dependency Resolver:
                    <dependency-resolver :dependency-resolver="resolution.status[index].dependency_resolver" />
                </div>
                <div></div>
            </div>
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
        Tools
    },
    props: {
        resolution: {
            type: Object,
            required: true
        }
    },
    computed: {
        singleTool: function() {
            return this.resolution.tool_id != undefined;
        },
        isContainerResolution: function() {
            return this.resolution.status.length >= 1 && this.resolution.status[0].model_class == "ContainerDependency";
        },
        containerResolution: function() {
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
        separateDetails: function() {
            return (
                this.resolution.status.length > 1 && this.resolution.status[0].model_class != "MergedCondaDependency"
            );
        }
    }
};
</script>
