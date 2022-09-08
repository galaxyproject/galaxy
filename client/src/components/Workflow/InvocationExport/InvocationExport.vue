<template>
    <span class="workflow-invocation-export-component">
        <h2>Export worklfow invocation</h2>
        <span v-if="initializingFileSources">
            <loading-span :message="initializeFileSourcesMessage" />
        </span>
        <span v-else-if="hasWritableFileSources">
            <b-card no-body>
                <b-tabs pills card vertical>
                    <b-tab title="to a direct download" title-link-class="tab-export-to-link" active>
                        <b-card-text>
                            <StsExport :invocation-id="invocationId" />
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
            <StsExport :invocation-id="invocationId" />
        </span>
    </span>
</template>

<script>
import { BCard, BTabs, BTab } from "bootstrap-vue";
import StsExport from "./StsExport.vue";
import ToRemoteFile from "./ToRemoteFile.vue";

import exportsMixin from "components/Common/exportsMixin";

export default {
    components: {
        StsExport,
        ToRemoteFile,
        BCard,
        BTabs,
        BTab,
    },
    mixins: [exportsMixin],
    props: {
        invocationId: {
            type: String,
            required: true,
        },
    },
    async mounted() {
        await this.initializeFilesSources();
    },
};
</script>
