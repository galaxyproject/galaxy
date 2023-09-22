<template>
    <span class="history-export-component">
        <h1 class="h-lg">Export history archive</h1>
        <span v-if="initializingFileSources">
            <loading-span :message="initializeFileSourcesMessage" />
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

import exportsMixin from "components/Common/exportsMixin";

export default {
    components: {
        ToLink,
        ToRemoteFile,
        BCard,
        BTabs,
        BTab,
    },
    mixins: [exportsMixin],
    props: {
        historyId: {
            type: String,
            required: true,
        },
    },
    async mounted() {
        await this.initializeFilesSources();
    },
};
</script>
