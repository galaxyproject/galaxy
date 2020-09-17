<template>
    <div class="w-50 p-2 float-left">
        <b-card nobody body-class="p-1">
            <b-img :src="imageUrl" fluid />
        </b-card>
    </div>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { getAppRoot } from "onload/loadConfig";

Vue.use(BootstrapVue);

export default {
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
