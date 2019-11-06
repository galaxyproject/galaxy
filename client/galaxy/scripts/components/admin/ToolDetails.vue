<template>
    <b-card>
        Tool Details for Tool {{ toolId }} at version {{ toolVersion }}.
        <div v-if="repo">
            <b>Installation Repository Details:</b>
            <repository-details :repo="repo" />
        </div>
        <div v-else>
            <b>Not a Tool Shed installed tool.</b>
        </div>
        <div v-if="containerResolution">
            <b>Container Resolution Details:</b>
            <container-resolution-details :resolution="containerResolution" :includeToolContext="false" />
        </div>
        <div v-if="dependencyResolution">
            <b>Dependency Resolution Details:</b>
            <resolution-details :resolution="dependencyResolution" :includeToolContext="false" />
        </div>
    </b-card>
</template>

<script>
import RepositoryDetails from "components/Toolshed/InstalledList/Details";
import ContainerResolutionDetails from "./Dependencies/ContainerResolutionDetails";
import ResolutionDetails from "./Dependencies/ResolutionDetails";
import { getToolboxDependencies, getContainerResolutionToolbox } from "./AdminServices";

export default {
    components: { RepositoryDetails, ContainerResolutionDetails, ResolutionDetails },
    props: {
        toolId: {
            type: String,
            required: true
        },
        toolVersion: {
            type: String,
            required: true
        },
        repo: {
            type: Object,
            default: null
        }
    },
    data() {
        return {
            dependencyResolution: null,
            containerResolution: null
        };
    },
    created()  {
        // TODO: handle tool_version...
        const dependencyResolutionParams = { "tool_ids": [this.toolId], "index_by": "tools" };
        getToolboxDependencies( dependencyResolutionParams )
                .then(resolutions => {
                    if( resolutions && resolutions.length > 0 ) {
                        this.dependencyResolution = resolutions[0];
                    }
                })
                .catch(this.handleError);
        const containerResolutionParams = { "tool_ids": [this.toolId] };        
        getContainerResolutionToolbox( containerResolutionParams )
                .then(resolutions => {
                    if( resolutions && resolutions.length > 0 ) {
                        this.containerResolution = resolutions[0];
                    }
                })
                .catch(this.handleError);
    },
    computed: {
    },
    methods: {
        handleError(e) {
            console.error(e);
        }
    }
};
</script>
