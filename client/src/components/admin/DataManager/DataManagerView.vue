<template>
    <div aria-labelledby="data-managers-title">
        <span class="mb-3">
            <h1 id="data-managers-title" class="h-lg">Local Data</h1>
            <p>
                Data Managers are used to manage Galaxy's local data. They can be installed manually, or via the
                <GLink :href="toolShedLink">ToolShed</GLink>. For more comprehensive information
                <GLink href="https://galaxyproject.org/admin/tools/data-managers/" target="_blank"> See the Wiki </GLink
                >.
            </p>
        </span>
        <router-view />
    </div>
</template>
<script>
import { getAppRoot } from "onload/loadConfig";

import GLink from "@/component-library/GLink.vue";

export default {
    components: { GLink },
    computed: {
        toolShedLink() {
            return `${getAppRoot()}admin/toolshed`;
        },
    },
};
</script>
