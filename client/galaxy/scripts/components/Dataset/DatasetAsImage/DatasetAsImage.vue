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
import { getPathDestination } from "components/Dataset/compositeDatasetUtils";

export default {
    props: {
        history_dataset_id: {
            type: String,
            required: true,
        },
        path: {
            type: String,
        },
    },
    created() {
        if (this.path) {
            getPathDestination(this.history_dataset_id, this.path).then((pathDestination) => {
                this.imgUrl = pathDestination.fileLink;
            });
        } else this.imgUrl = `${getAppRoot()}dataset/display?dataset_id=${this.history_dataset_id}`;
    },
    data() {
        return {
            imgUrl: undefined,
        };
    },
};
</script>
