<template>
    <div>
        <span v-if="isError" class="fa fa-exclamation-triangle text-danger mr-1" />
        <span v-if="isPaused" class="fa fa-pause text-info mr-1" />
        <b-link href="#" @click.stop="click"
            ><b>{{ item.name }}</b></b-link
        >
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
        click() {
            const Galaxy = getGalaxyInstance();
            this.services
                .setHistory(this.item.history_id)
                .then(history => {
                    Galaxy.currHistoryPanel.loadCurrentHistory();
                })
                .catch(error => {
                    //this.error = error;
                });
        }
    }
};
</script>
