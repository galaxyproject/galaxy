<template>
    <div>
        <b-link
            id="history-dropdown"
            class="history-dropdown font-weight-bold"
            data-toggle="dropdown"
            aria-haspopup="true"
            aria-expanded="false"
        >
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
    data() {
        return {
            urlView: `${getAppRoot()}histories/view?id=${this.history.id}`,
            urlShowStructure: `${getAppRoot()}histories/show_structure?id=${this.history.id}`,
            urlSharing: `${getAppRoot()}histories/sharing?id=${this.history.id}`
        };
    },
    created() {
        this.root = getAppRoot();
    },
    methods: {
        onSwitch: function() {
            const Galaxy = getGalaxyInstance();
            Galaxy.currHistoryPanel.switchToHistory(this.history.id);
        }
    }
};
</script>
