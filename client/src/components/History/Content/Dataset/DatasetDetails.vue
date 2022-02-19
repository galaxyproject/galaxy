<template>
    <UrlDataProvider :url="dataUrl" v-slot="{ loading, result }">
        <div v-if="!loading" class="dataset">
            <div class="p-2 details">
                <div class="summary">
                    <div v-if="result.misc_blurb" class="blurb">
                        <span class="value">{{ result.misc_blurb }}</span>
                    </div>
                    <span v-if="result.file_ext" class="datatype">
                        <label class="prompt" v-localize>format</label>
                        <span class="value">{{ result.file_ext }}</span>
                    </span>
                    <span v-if="result.genome_build" class="dbkey">
                        <label class="prompt" v-localize>database</label>
                        <b-link class="value" @click.stop="$emit('edit', dataset)">{{ result.genome_build }}</b-link>
                    </span>
                    <div v-if="result.misc_info" class="info">
                        <span class="value">{{ result.misc_info }}</span>
                    </div>
                </div>
                <DatasetActions :item="result" />
                <pre v-if="result.peek" class="dataset-peek p-1" v-html="result.peek" />
            </div>
        </div>
    </UrlDataProvider>
</template>

<script>
import { UrlDataProvider } from "components/providers/UrlDataProvider";
import DatasetActions from "./DatasetActions";

export default {
    components: {
        DatasetActions,
        UrlDataProvider,
    },
    props: {
        item: { type: Object, required: true },
    },
    computed: {
        dataset() {
            return this.item.object || this.item;
        },
        dataUrl() {
            const datasetId = this.dataset.id;
            return `api/datasets/${datasetId}`;
        },
    },
    created() {
        console.log(this.item);
    },
};
</script>
