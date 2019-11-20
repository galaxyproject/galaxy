<template>
    <div>
        <b-button
            v-b-tooltip.hover.bottom
            title="Add to current History"
            class="dataset-add btn-sm btn-primary fa fa-plus"
            @click.stop="addToHistory"
        />
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
