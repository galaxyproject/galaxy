<template>
    <UrlDataProvider :url="dataUrl" v-slot="{ loading, result: dataset }">
        <div class="p-2 details">
            <div class="summary">
                <div v-if="dataset.misc_blurb" class="blurb">
                    <span class="value">{{ dataset.misc_blurb }}</span>
                </div>
                <div v-if="dataset.file_ext" class="datatype">
                    <label class="prompt" v-localize>format</label>
                    <span class="value">{{ dataset.file_ext }}</span>
                </div>
                <div v-if="dataset.genome_build" class="dbkey">
                    <label class="prompt" v-localize>database</label>
                    <b-link class="value" @click.stop="listeners['edit']()">{{ dataset.genome_build }}</b-link>
                </div>
                <div v-if="dataset.misc_info" class="info">
                    <span class="value">{{ dataset.misc_info }}</span>
                </div>
            </div>
            <pre v-if="dataset.peek" class="dataset-peek p-1" v-html="dataset.peek" />
        </div>
    </UrlDataProvider>
</template>

<script>
import { UrlDataProvider } from "components/providers/UrlDataProvider";

export default {
    components: {
        UrlDataProvider,
    },
    props: {
        item: { type: Object, required: true },
    },
    computed: {
        dataUrl() {
            //object.id and item.element_type == "hda"
            const datasetId = this.item.id;
            return `api/datasets/${datasetId}`;
        },
    },
    created() {
        console.log(this.item);
    },
};
</script>
