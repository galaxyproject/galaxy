<template>
    <div>
        <BNav tabs>
            <BNavItem :active="mode == 'dependencies'" @click="setMode('dependencies')">Dependencies</BNavItem>
            <BNavItem :active="mode == 'containers'" @click="setMode('containers')">Containers</BNavItem>
            <BNavItem :active="mode == 'unused'" @click="setMode('unused')">Unused</BNavItem>
        </BNav>
        <ResolutionIndex v-if="mode == 'dependencies'" />
        <ContainerIndex v-else-if="mode == 'containers'" />
        <UnusedIndex v-else-if="mode == 'unused'" />
    </div>
</template>
<script>
import { BNav, BNavItem } from "bootstrap-vue";

import ContainerIndex from "./ContainerIndex.vue";
import ResolutionIndex from "./ResolutionIndex.vue";
import UnusedIndex from "./UnusedIndex.vue";

export default {
    components: {
        BNav,
        BNavItem,
        ContainerIndex,
        ResolutionIndex,
        UnusedIndex,
    },
    data: function () {
        return {
            mode: "dependencies",
        };
    },
    methods: {
        setMode(mode) {
            this.mode = mode;
        },
    },
};
</script>
