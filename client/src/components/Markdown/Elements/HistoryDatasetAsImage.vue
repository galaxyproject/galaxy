<template>
    <div>
        <DatasetAsImage :path="args.path" :history_dataset_id="args.history_dataset_id" />
    </div>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { getAppRoot } from "onload/loadConfig";
import DatasetAsImage from "components/Dataset/DatasetAsImage/DatasetAsImage";

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
