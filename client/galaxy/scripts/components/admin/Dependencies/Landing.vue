<template>
    <div>
        <b-nav tabs>
            <b-nav-item v-bind:active="mode == 'resolution'" @click="setMode('resolution')">Resolution</b-nav-item>
            <b-nav-item v-bind:active="mode == 'container'" @click="setMode('container')">Container</b-nav-item>
            <b-nav-item v-bind:active="mode == 'unused'" @click="setMode('unused')">Unused</b-nav-item>
        </b-nav>
        <resolution-index v-if="mode == 'resolution'" />
        <container-index v-else-if="mode == 'container'" />
        <unused-index v-else-if="mode == 'unused'" />
    </div>
</template>
<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

import ContainerIndex from "./ContainerIndex";
import ResolutionIndex from "./ResolutionIndex";
import UnusedIndex from "./UnusedIndex";

Vue.use(BootstrapVue);

export default {
    components: { ContainerIndex, ResolutionIndex, UnusedIndex },
    data: function() {
        return {
            mode: "resolution"
        };
    },
    methods: {
        setMode(mode) {
            this.mode = mode;
        }
    }
};
</script>
