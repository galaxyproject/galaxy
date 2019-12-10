<template>
    <div>
        <b-link
            id="dataset-dropdown"
            class="workflow-dropdown font-weight-bold"
            data-toggle="dropdown"
            aria-haspopup="true"
            aria-expanded="false"
        >
            <span v-if="isError" class="fa fa-times-circle text-danger mr-1" />
            <span v-if="isPaused" class="fa fa-pause text-info mr-1" />
            <span>{{ item.name }}</span>
        </b-link>
        <div class="dropdown-menu" aria-labelledby="dataset-dropdown">
            <a class="dropdown-item" href="#" @click.prevent="showDataset">Show in History</a>
            <a class="dropdown-item" href="#" @click.prevent="copyDataset">Copy to History</a>
        </div>
    </div>
</template>
<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

Vue.use(BootstrapVue);

export default {
    props: {
        item: Object
    },
    computed: {
        isError() {
            return this.item.state === "error";
        },
        isPaused() {
            return this.item.state === "paused";
        }
    },
    methods: {
        copyDataset(item) {
            this.$emit("copyDataset", this.item);
        },
        showDataset(item) {
            this.$emit("showDataset", this.item);
        }
    }
};
</script>
