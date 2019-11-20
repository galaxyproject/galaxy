<template>
    <div>
        <span v-if="isError" class="fa fa-times-circle text-danger mr-1" />
        <span v-if="isPaused" class="fa fa-pause text-info mr-1" />
        <b-button
            data-toggle="dropdown"
            id="dataset-name"
            aria-haspopup="true"
            aria-expanded="false"
            v-b-tooltip.hover.bottom
            title="Show dataset"
            class="dataset-add btn-sm btn-primary fa fa-gear"
        />
        <div class="dropdown-menu" aria-labelledby="dataset-name">
            <a class="dropdown-item" href="#" @click="addToHistory">Copy dataset to current history</a>
        </div>
    </div>
</template>
<script>
import { getAppRoot } from "onload";
import { getGalaxyInstance } from "app";
import { Services } from "./services.js";

export default {
    props: {
        item: Object
    },
    data() {
        return {};
    },
    created() {
        this.root = getAppRoot();
        this.services = new Services({ root: this.root });
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
        addToHistory() {
            const Galaxy = getGalaxyInstance();
            const history = Galaxy.currHistoryPanel;
            const dataset_id = this.item.id;
            const history_id = history.model.id;
            this.services
                .copyDataset(dataset_id, history_id)
                .then(response => {
                    history.loadCurrentHistory();
                })
                .catch(error => {
                    this.$emit("error", error);
                });
        }
    }
};
</script>
