<template>
    <div>
        <b-link
            id="dataset-dropdown"
            class="workflow-dropdown font-weight-bold"
            data-toggle="dropdown"
            aria-haspopup="true"
            aria-expanded="false"
        >
            <span
                v-if="isError"
                class="error fa fa-times-circle text-danger mr-1"
                v-b-tooltip.hover
                title="An error occurred for this dataset."
            />
            <span
                v-if="isPaused"
                class="pause fa fa-pause text-info mr-1"
                v-b-tooltip.hover
                title="The creation of this dataset has been paused."
            />
            <span class="fa fa-caret-down" />
            <span class="name">{{ this.getName }}</span>
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
        item: Object
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
