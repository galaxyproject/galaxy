<template>
    <span class="dependency-status">
        <span v-if="status.dependency_type" :title="title">
            <b>
                <span class="fa fa-check text-success"></span>{{ status.dependency_type }}
                <span v-if="mergedMultiple">(合并)</span>
            </b>
            <span v-if="!compact">{{ description }} <DisplayRaw :object="status" /></span>
        </span>
        <b v-else> <span class="fa fa-times text-danger"></span><i>未解析</i> </b>
    </span>
</template>
<script>
import DisplayRaw from "./DisplayRaw";

const DESCRIPTIONS = {
    conda: "将使用 Conda 包管理器进行解析。 ",
    galaxy_package: "将使用手动配置的 Galaxy 包目录进行解析。 ",
    tool_shed_packages: "将使用旧版 Tool Shed 包安装进行解析。 ",
    docker: "假设由指定的 Docker 容器处理依赖关系解析。 ",
    singularity: "假设由指定的 Singularity 容器处理依赖关系解析。 ",
};

function describeRequirement(status) {
    const exact = status.exact;
    let prefix;
    if (exact) {
        prefix = "此依赖项假定完全匹配要求 ";
    } else {
        prefix = "忽略版本信息，假定此依赖项匹配要求 ";
    }
    let requirement = status.name || "";
    if (status.version) {
        requirement += `，版本为 ${status.version}`;
    }
    return `${prefix}${requirement}. `;
}

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
                `将使用依赖解析器 ${dependencyType} 进行解析。`;
            if (dependencyType == "conda") {
                resolutionDescription += `将使用位于 ${this.status.environment_path} 的 Conda 环境进行解析。 `;
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
