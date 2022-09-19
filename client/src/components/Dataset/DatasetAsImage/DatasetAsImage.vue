<template>
    <div>
        <div v-if="imageUrl" class="w-100 p-2">
            <b-card nobody body-class="p-1">
                <b-img :src="imageUrl" fluid />
            </b-card>
        </div>
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
    data() {
        return {
            imageUrl: undefined,
        };
    },
    created() {
        if (this.path) {
            this.fetchPathDestination({ history_dataset_id: this.history_dataset_id, path: this.path }).then(() => {
                const pathDestination = this.$store.getters.pathDestination(this.history_dataset_id, this.path);
                this.imageUrl = pathDestination.fileLink;
            });
        } else {
            this.imageUrl = `${getAppRoot()}dataset/display?dataset_id=${this.history_dataset_id}`;
        }
    },
    methods: {
        ...mapCacheActions(["fetchPathDestination"]),
    },
};
</script>
