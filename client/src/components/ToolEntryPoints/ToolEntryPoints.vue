<template>
    <div class="infomessagelarge">
        <p v-if="entryPointsForJob(jobId).length == 0">
            正在等待交互式工具结果视图可用。
        </p>
        <p v-else-if="entryPointsForJob(jobId).length == 1">
            <span v-if="entryPointsForJob(jobId)[0].active">
                有一个交互式工具结果视图可用，
                <a v-b-tooltip title="打开交互式工具" :href="entryPointsForJob(jobId)[0].target" target="_blank">
                    打开
                    <FontAwesomeIcon icon="external-link-alt" />
                </a>
            </span>
            <span v-else>
                有一个交互式工具结果视图可用，正在等待视图激活...
            </span>
        </p>
        <div v-else>
            有多个交互式工具结果视图可用：
            <ul>
                <li v-for="entryPoint of entryPointsForJob(jobId)" :key="entryPoint.id">
                    {{ entryPoint.name }}
                    <span v-if="entryPoint.active">
                        <a v-b-tooltip title="打开交互式工具" :href="entryPoint.target" target="_blank">
                            (打开
                            <FontAwesomeIcon icon="external-link-alt" />)
                        </a>
                    </span>
                    <span v-else> (等待激活中...) </span>
                </li>
            </ul>
        </div>

        您也可以通过
        <a :href="interactiveToolsLink">用户菜单</a>访问所有激活的交互式工具。
    </div>
</template>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faExternalLinkAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { getAppRoot } from "onload/loadConfig";
import { mapState } from "pinia";
import { useEntryPointStore } from "stores/entryPointStore";

library.add(faExternalLinkAlt);

export default {
    components: {
        FontAwesomeIcon,
    },
    props: {
        jobId: {
            type: String,
            required: true,
        },
    },
    computed: {
        ...mapState(useEntryPointStore, ["entryPointsForJob"]),
        interactiveToolsLink: function () {
            return getAppRoot() + "interactivetool_entry_points/list";
        },
    },
};
</script>
