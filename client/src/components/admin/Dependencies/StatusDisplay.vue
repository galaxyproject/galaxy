<template>
    <span class="dependency-status">
        <span v-if="status.dependency_type" :title="title">
            <b>
                <span class="fa fa-check text-success"></span>{{ status.dependency_type }}
                <span v-if="mergedMultiple">(merged)</span>
            </b>
            <span v-if="!compact">{{ description }} <display-raw :object="status" /></span>
        </span>
        <b v-else> <span class="fa fa-times text-danger"></span><i>unresolved</i> </b>
    </span>
</template>
<script>
const DESCRIPTIONS = {
    conda: "The Conda package manager will be used for resolution. ",
    galaxy_package: "A manually configured Galaxy package directory will be used for resolution. ",
    tool_shed_packages: "Legacy Tool Shed package installations will be used for resolution. ",
    docker: "Resolution of dependencies is assumed to be handled by specified Docker container. ",
    singularity: "Resolution of dependencies is assumed to be handled by specified Singularity container. ",
};

function describeRequirement(status) {
    const exact = status.exact;
    let prefix;
    if (exact) {
        prefix = "This dependency is assumed to exactly match the requirement ";
    } else {
        prefix = "Ignoring version information this dependency is assumed to match the requirement ";
    }
    let requirement = status.name || "";
    if (status.version) {
        requirement += ` at version ${status.version}`;
    }
    return `${prefix}${requirement}. `;
}

import DisplayRaw from "./DisplayRaw";

export default {
    components: { DisplayRaw },
    props: {
        status: {
            type: Object,
            required: true,
        },
        allStatuses: {
            type: Array,
            default: null,
        },
        compact: {
            type: Boolean,
            default: true,
        },
    },
    computed: {
        merged: function () {
            return (
                this.status.model_class == "MergedCondaDependency" || this.status.model_class == "ContainerDependency"
            );
        },
        mergedMultiple: function () {
            return this.merged && this.allStatuses != null && this.allStatuses.length > 1;
        },
        description: function () {
            const dependencyType = this.status.dependency_type;
            let resolutionDescription =
                DESCRIPTIONS[dependencyType] ||
                `The dependency resolver ${dependencyType} will be used for resolution.`;
            if (dependencyType == "conda") {
                resolutionDescription += `The Conda environment found at ${this.status.environment_path} will be used for resolution. `;
            }
            if (this.mergedMultiple) {
                for (const status of this.allStatuses) {
                    resolutionDescription += describeRequirement(status);
                }
            } else if (this.status.name) {
                resolutionDescription += describeRequirement(this.status);
            }
            return resolutionDescription;
        },
        title: function () {
            return this.compact ? this.description : "";
        },
    },
};
</script>
