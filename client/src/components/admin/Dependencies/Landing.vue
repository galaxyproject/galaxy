<template>
    <div>
        <b-nav tabs>
            <b-nav-item :active="mode == 'dependencies'" @click="setMode('dependencies')">依赖</b-nav-item>
            <b-nav-item :active="mode == 'containers'" @click="setMode('containers')">容器</b-nav-item>
            <b-nav-item :active="mode == 'unused'" @click="setMode('unused')">未使用</b-nav-item>
        </b-nav>
        <ResolutionIndex v-if="mode == 'dependencies'" />
        <ContainerIndex v-else-if="mode == 'containers'" />
        <UnusedIndex v-else-if="mode == 'unused'" />
    </div>
</template>
<script>
import BootstrapVue from "bootstrap-vue";
import Vue from "vue";

import ContainerIndex from "./ContainerIndex";
import ResolutionIndex from "./ResolutionIndex";
import UnusedIndex from "./UnusedIndex";

Vue.use(BootstrapVue);

export default {
    components: { ContainerIndex, ResolutionIndex, UnusedIndex },
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
