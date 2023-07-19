<template>
    <div>
        <b-nav tabs>
            <GNavItem :active="mode == 'dependencies'" @click="setMode('dependencies')">Dependencies</GNavItem>
            <GNavItem :active="mode == 'containers'" @click="setMode('containers')">Containers</GNavItem>
            <GNavItem :active="mode == 'unused'" @click="setMode('unused')">Unused</GNavItem>
        </b-nav>
        <ResolutionIndex v-if="mode == 'dependencies'" />
        <ContainerIndex v-else-if="mode == 'containers'" />
        <UnusedIndex v-else-if="mode == 'unused'" />
    </div>
</template>
<script>
import BootstrapVue from "bootstrap-vue";
import Vue from "vue";

import { GNavItem } from "@/component-library";

import ContainerIndex from "./ContainerIndex";
import ResolutionIndex from "./ResolutionIndex";
import UnusedIndex from "./UnusedIndex";

Vue.use(BootstrapVue);

export default {
    components: { GNavItem, ContainerIndex, ResolutionIndex, UnusedIndex },
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
