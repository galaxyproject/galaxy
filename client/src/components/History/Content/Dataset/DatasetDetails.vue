<template>
    <DatasetProvider :id="dataset.id" auto-refresh v-slot="{ loading, result }">
        <div v-if="!loading" class="dataset">
            <div class="p-2 details">
                <div class="summary">
                    <div v-if="stateText" class="mb-1">{{ stateText }}</div>
                    <div v-else-if="result.misc_blurb" class="blurb">
                        <span class="value">{{ result.misc_blurb }}</span>
                    </div>
                    <span v-if="result.file_ext" class="datatype">
                        <label class="prompt" v-localize>format</label>
                        <span class="value">{{ result.file_ext }}</span>
                    </span>
                    <span v-if="result.genome_build" class="dbkey">
                        <label class="prompt" v-localize>database</label>
                        <b-link class="value" @click.stop="$emit('edit', dataset)" data-label="Database/Build">{{
                            result.genome_build
                        }}</b-link>
                    </span>
                    <div v-if="result.misc_info" class="info">
                        <span class="value">{{ result.misc_info }}</span>
                    </div>
                </div>
                <DatasetActions :item="result" />
                <pre v-if="result.peek" class="dataset-peek p-1" v-html="result.peek" />
            </div>
        </div>
    </DatasetProvider>
</template>

<script>
import STATES from "components/History/Content/contentStates";
import { DatasetProvider } from "components/providers/storeProviders";
import DatasetActions from "./DatasetActions";

export default {
    components: {
        DatasetActions,
        DatasetProvider,
    },
    props: {
        dataset: { type: Object, required: true },
    },
    computed: {
        stateText() {
            return STATES[this.dataset.state] && STATES[this.dataset.state].text;
        },
    },
};
</script>
