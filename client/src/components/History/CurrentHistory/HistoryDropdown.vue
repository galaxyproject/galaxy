<template>
    <div>
        <b-link
            id="history-dropdown"
            class="history-dropdown font-weight-bold"
            data-toggle="dropdown"
            aria-haspopup="true"
            aria-expanded="false">
            {{ history.name }}
        </b-link>
        <div class="dropdown-menu" aria-labelledby="history-dropdown">
            <a class="dropdown-item" :href="urlView">View</a>
            <a class="dropdown-item" href="#" @click="onSwitch">Switch To</a>
            <a class="dropdown-item" :href="urlShowStructure">Structure</a>
            <a class="dropdown-item" :href="urlSharing">Sharing</a>
        </div>
    </div>
</template>
<script>
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";

export default {
    props: ["history"],
    created() {
        this.root = getAppRoot();
    },
    computed: {
        urlView() {
            return `${getAppRoot()}histories/view?id=${this.history.id}`;
        },
        urlShowStructure() {
            return `${getAppRoot()}histories/show_structure?id=${this.history.id}`;
        },
        urlSharing() {
            return `${getAppRoot()}histories/sharing?id=${this.history.id}`;
        },
    },
    methods: {
        onSwitch() {
            const Galaxy = getGalaxyInstance();
            Galaxy.currHistoryPanel.switchToHistory(this.history.id);
        },
    },
};
</script>
