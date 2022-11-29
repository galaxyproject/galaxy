<template>
    <div>
        <b-link
            id="dataset-dropdown"
            class="workflow-dropdown font-weight-bold p-2"
            data-toggle="dropdown"
            aria-haspopup="true"
            aria-expanded="false">
            <FontAwesomeIcon
                v-if="isError"
                v-b-tooltip.hover
                icon="fa-times-circle"
                class="dataset-icon error text-danger"
                title="An error occurred for this dataset." />
            <FontAwesomeIcon
                v-else-if="isPaused"
                v-b-tooltip.hover
                icon="fa-pause"
                class="dataset-icon pause text-info"
                title="The creation of this dataset has been paused." />
            <FontAwesomeIcon v-else icon="fa-caret-down" class="dataset-icon" />
            <span class="name">{{ getName }}</span>
        </b-link>
        <div class="dropdown-menu" aria-labelledby="dataset-dropdown">
            <a class="dropdown-item" href="#" @click.prevent="showDataset">
                <FontAwesomeIcon icon="fa-eye" fixed-width class="mr-1" />
                <span>Show in History</span>
            </a>
            <a class="dropdown-item" href="#" @click.prevent="copyDataset">
                <FontAwesomeIcon icon="fa-copy" fixed-width class="mr-1" />
                <span>Copy to History</span>
            </a>
        </div>
    </div>
</template>
<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCaretDown, faEye, faCopy, faTimesCircle, faPause } from "@fortawesome/free-solid-svg-icons";

library.add(faCaretDown, faEye, faCopy, faTimesCircle, faPause);

Vue.use(BootstrapVue);

export default {
    components: { FontAwesomeIcon },
    props: {
        item: Object,
    },
    computed: {
        getName() {
            return this.item.name || "Unavailable";
        },
        isError() {
            return this.item.state === "error";
        },
        isPaused() {
            return this.item.state === "paused";
        },
    },
    methods: {
        copyDataset(item) {
            this.$emit("copyDataset", this.item);
        },
        showDataset(item) {
            this.$emit("showDataset", this.item);
        },
    },
};
</script>

<style scoped>
.dataset-icon {
    position: relative;
    margin-left: -1rem;
}
</style>
