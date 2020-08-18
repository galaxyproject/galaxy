<template>
    <b-card nobody class="w-50" body-class="p-1">
        <b-img :src="imageUrl" fluid />
    </b-card>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
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
