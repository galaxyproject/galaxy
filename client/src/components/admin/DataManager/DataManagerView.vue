<template>
    <div aria-labelledby="data-managers-title">
        <span class="mb-3">
            <h1 id="data-managers-title" class="h-lg">Local Data</h1>
            <p>
                Data Managers are used to manage Galaxy's local data. They can be installed manually, or via the
                <BLink :href="toolShedLink">ToolShed</BLink>. For more comprehensive information
                <BLink href="https://galaxyproject.org/admin/tools/data-managers/" target="_blank">See the Wiki</BLink>.
            </p>
        </span>
        <router-view />
    </div>
</template>
<script>
import { BLink } from "bootstrap-vue";

import { getAppRoot } from "@/onload/loadConfig";

export default {
    components: { BLink },
    computed: {
        toolShedLink() {
            return `${getAppRoot()}admin/toolshed`;
        },
    },
};
</script>
