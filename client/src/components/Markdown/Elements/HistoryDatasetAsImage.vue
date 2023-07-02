<template>
    <div>
        <DatasetAsImage :path="args.path" :history_dataset_id="args.history_dataset_id" />
    </div>
</template>

<script>
import BootstrapVue from "bootstrap-vue";
import DatasetAsImage from "components/Dataset/DatasetAsImage/DatasetAsImage";
import { getAppRoot } from "onload/loadConfig";
import Vue from "vue";

Vue.use(BootstrapVue);

export default {
    components: {
        DatasetAsImage,
    },
    props: {
        args: {
            type: Object,
            default: null,
        },
    },
    computed: {
        imageUrl() {
            return `${getAppRoot()}dataset/display?dataset_id=${this.args.history_dataset_id}`;
        },
    },
};
</script>
