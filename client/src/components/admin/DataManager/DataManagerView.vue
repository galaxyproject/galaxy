<template>
    <div aria-labelledby="data-managers-title">
        <span class="mb-3">
            <h1 id="data-managers-title" class="h-lg">Local Data</h1>
            <p>
                数据管理器用于管理本地数据。可以手动安装，也可以通过
                <b-link :href="toolShedLink">ToolShed</b-link> 安装。欲了解更多详细信息，
                <b-link href="https://galaxyproject.org/admin/tools/data-managers/" target="_blank">请参见Wiki</b-link>
                >.
            </p>
        </span>
        <router-view />
    </div>
</template>
<script>
import { getAppRoot } from "onload/loadConfig";

export default {
    computed: {
        toolShedLink() {
            return `${getAppRoot()}admin/toolshed`;
        },
    },
};
</script>
