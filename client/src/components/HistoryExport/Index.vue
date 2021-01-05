<template>
    <span>
        <h2>Export history archive</h2>
        <b-card no-body>
            <b-tabs pills card vertical>
                <b-tab title="to a link" active>
                    <b-card-text>
                        <ToLink :history-id="historyId" />
                    </b-card-text>
                </b-tab>
                <b-tab title="to a remote file">
                    <ToRemoteFile :history-id="historyId" />
                </b-tab>
            </b-tabs>
        </b-card>
    </span>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import ToLink from "./ToLink.vue";
import ToRemoteFile from "./ToRemoteFile.vue";

Vue.use(BootstrapVue);

export default {
    components: {
        ToLink,
        ToRemoteFile,
    },
    props: {
        historyId: {
            type: String,
            required: true,
        },
    },
};
</script>
