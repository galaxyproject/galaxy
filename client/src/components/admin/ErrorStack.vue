<template>
    <div>
        <GAlert :show="messageVisible" variant="danger"> {{ messageText }} </GAlert>
        <GAlert :show="infoVisible" variant="info"> No errors available. </GAlert>
        <b-table v-if="errorStackVisible" striped :fields="errorStackAttributes" :items="errorStack" />
    </div>
</template>
<script>
import { getErrorStack } from "./AdminServices";

import GAlert from "@/component-library/GAlert.vue";

export default {
    components: {
        GAlert,
    },
    data() {
        return {
            errorStack: [],
            errorStackLoaded: false,
            errorStackAttributes: [
                { key: "time", sortable: true },
                { key: "phase", sortable: true },
                { key: "file", sortable: true },
                { key: "error" },
            ],
            messageText: null,
        };
    },
    computed: {
        errorStackVisible: function () {
            return this.errorStack.length > 0;
        },
        messageVisible: function () {
            return this.messageText != null;
        },
        infoVisible: function () {
            return !this.errorStackVisible && this.errorStackLoaded;
        },
    },
    created() {
        getErrorStack()
            .then((response) => {
                this.errorStack = response.data;
                this.errorStackLoaded = true;
            })
            .catch((e) => {
                const message = e && e.response && e.response.data && e.response.data.err_msg;
                this.messageText = message || "Request failed for an unknown reason.";
            });
    },
};
</script>
