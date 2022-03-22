<template>
    <span class="history-export-component">
        <h2>Export history archive</h2>
        <span v-if="initializing">
            <loading-span message="Loading server configuration." />
        </span>
        <span v-else-if="hasWritableFileSources">
            <b-card no-body>
                <b-tabs pills card vertical>
                    <b-tab title="to a link" title-link-class="tab-export-to-link" active>
                        <b-card-text>
                            <ToLink :history-id="historyId" />
                        </b-card-text>
                    </b-tab>
                    <b-tab title="to a remote file" title-link-class="tab-export-to-file">
                        <b-card-text>
                            <ToRemoteFile :history-id="historyId" />
                        </b-card-text>
                    </b-tab>
                </b-tabs>
            </b-card>
        </span>
        <span v-else>
            <ToLink :history-id="historyId" />
        </span>
    </span>
</template>

<script>
import { BCard, BTabs, BTab } from "bootstrap-vue";
import ToLink from "./ToLink.vue";
import ToRemoteFile from "./ToRemoteFile.vue";
import { Services } from "components/FilesDialog/services";
import LoadingSpan from "components/LoadingSpan";

export default {
    components: {
        LoadingSpan,
        ToLink,
        ToRemoteFile,
        BCard,
        BTabs,
        BTab,
    },
    props: {
        historyId: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            initializing: true,
            hasWritableFileSources: false,
        };
    },
    async mounted() {
        await this.initialize();
    },
    methods: {
        async initialize() {
            const fileSources = await new Services().getFileSources();
            this.hasWritableFileSources = fileSources.some((fs) => fs.writable);
            this.initializing = false;
        },
    },
};
</script>
