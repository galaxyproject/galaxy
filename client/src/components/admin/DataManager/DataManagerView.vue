<template>
    <div>
        <span class="mb-3">
            <h2 id="data-managers-title">Local Data</h2>
            <p>
                Data Managers are used to manage Galaxy's local data. They can be installed manually, or via the
                <b-link :href="toolShedLink">ToolShed</b-link>. For more comprehensive information
                <b-link href="https://galaxyproject.org/admin/tools/data-managers/" target="_blank">See the Wiki</b-link
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
