<template>
    <div>
        <BAlert :show="messageVisible" variant="danger"> {{ messageText }} </BAlert>

        <BAlert :show="infoVisible" variant="info"> No errors available. </BAlert>

        <GTable v-if="errorStackVisible" striped :fields="errorStackAttributes" :items="errorStack" />
    </div>
</template>

<script>
import { BAlert } from "bootstrap-vue";

import { getErrorStack } from "./AdminServices";

import GTable from "@/components/Common/GTable.vue";

export default {
    components: {
        BAlert,
        GTable,
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
