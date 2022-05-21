<template>
    <div>
        <b-link
            id="dataset-dropdown"
            class="workflow-dropdown font-weight-bold p-2"
            data-toggle="dropdown"
            aria-haspopup="true"
            aria-expanded="false">
            <span
                v-if="isError"
                v-b-tooltip.hover
                class="dataset-icon error fa fa-times-circle text-danger"
                title="An error occurred for this dataset." />
            <span
                v-else-if="isPaused"
                v-b-tooltip.hover
                class="dataset-icon pause fa fa-pause text-info"
                title="The creation of this dataset has been paused." />
            <span v-else class="dataset-icon fa fa-caret-down" />
            <span class="name">{{ getName }}</span>
        </b-link>
        <div class="dropdown-menu" aria-labelledby="dataset-dropdown">
            <a class="dropdown-item" href="#" @click.prevent="showDataset">
                <span class="fa fa-eye fa-fw mr-1" />
                <span>Show in History</span>
            </a>
            <a class="dropdown-item" href="#" @click.prevent="copyDataset">
                <span class="fa fa-copy fa-fw mr-1" />
                <span>Copy to History</span>
            </a>
        </div>
    </div>
</template>
<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

Vue.use(BootstrapVue);

export default {
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
