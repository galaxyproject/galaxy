<template>
    <DatasetProvider :id="dataset.id" v-slot="{ loading, result }" auto-refresh>
        <div v-if="!loading" class="dataset">
            <div class="p-2 details">
                <div class="summary">
                    <div v-if="stateText" class="mb-1">{{ stateText }}</div>
                    <div v-else-if="result.misc_blurb" class="blurb">
                        <span class="value">{{ result.misc_blurb }}</span>
                    </div>
                    <span v-if="result.file_ext" class="datatype">
                        <label v-localize class="prompt">format</label>
                        <span class="value">{{ result.file_ext }}</span>
                    </span>
                    <span v-if="result.genome_build" class="dbkey">
                        <label v-localize class="prompt">database</label>
                        <b-link class="value" data-label="Database/Build" @click.stop="$emit('edit')">{{
                            result.genome_build
                        }}</b-link>
                    </span>
                    <div v-if="result.misc_info" class="info">
                        <span class="value">{{ result.misc_info }}</span>
                    </div>
                </div>
                <DatasetActions :item="result" :show-highlight="showHighlight" @toggleHighlights="toggleHighlights" />
                <pre v-if="result.peek" class="dataset-peek p-1" v-html="result.peek" />
            </div>
        </div>
        <div v-else class="dataset">
            <!--
                placeholder skeleton for loading smoothly without a spinner
                (which you don't even see since this happens pretty fast)
            -->
            <div class="p-2 details">
                <div class="summary">
                    <div class="mb-1">
                        <b-skeleton width="85%"></b-skeleton>
                    </div>
                    <span class="datatype">
                        <b-skeleton width="55%"></b-skeleton>
                    </span>
                    <div class="info">
                        <span class="value">Dataset Information Loading.</span>
                    </div>
                </div>
                <pre class="dataset-peek p-1">
                    <table cellspacing="0" cellpadding="3">
                        <tbody>
                            <tr><td>Loading...</td></tr>
                        </tbody>
                    </table>
                </pre>
            </div>
        </div>
    </DatasetProvider>
</template>

<script>
import { STATES } from "components/History/Content/model/states";
import { DatasetProvider } from "components/providers/storeProviders";
import DatasetActions from "./DatasetActions";

export default {
    components: {
        DatasetActions,
        DatasetProvider,
    },
    props: {
        dataset: { type: Object, required: true },
        showHighlight: { type: Boolean, default: false },
    },
    computed: {
        stateText() {
            return STATES[this.dataset.state] && STATES[this.dataset.state].text;
        },
    },
    methods: {
        toggleHighlights() {
            this.$emit("toggleHighlights");
        },
    },
};
</script>
<style scoped>
.details .summary div.info {
    max-height: 4rem;
    overflow-y: auto;
}
</style>
