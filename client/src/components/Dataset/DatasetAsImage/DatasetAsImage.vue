<template>
    <div>
        <img v-if="imgUrl" :src="imgUrl" />
        <div v-else>
            <b>Image is not found</b>
        </div>
    </div>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import { mapCacheActions } from "vuex-cache";

export default {
    props: {
        history_dataset_id: {
            type: String,
            required: true,
        },
        path: {
            type: String,
            default: null,
        },
    },
    created() {
        if (this.path) {
            this.fetchPathDestination({ history_dataset_id: this.history_dataset_id, path: this.path }).then(() => {
                const pathDestination = this.$store.getters.pathDestination(this.history_dataset_id, this.path);
                this.imgUrl = pathDestination.fileLink;
            });
        } else this.imgUrl = `${getAppRoot()}dataset/display?dataset_id=${this.history_dataset_id}`;
    },
    data() {
        return {
            imgUrl: undefined,
        };
    },
    methods: {
        ...mapCacheActions(["fetchPathDestination"]),
    },
};
</script>
