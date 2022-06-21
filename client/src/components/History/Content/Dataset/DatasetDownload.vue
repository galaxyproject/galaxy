<template>
    <b-dropdown
        v-if="metaFiles"
        no-caret
        v-b-tooltip.top.hover
        size="sm"
        variant="link"
        toggle-class="text-decoration-none"
        title="Download"
        data-description="dataset download">
        <template v-slot:button-content>
            <span class="fa fa-save" />
        </template>
        <b-dropdown-item v-localize @click.stop="onDownload">Download Dataset</b-dropdown-item>
    </b-dropdown>
    <b-button v-else class="download-btn px-1" title="Download" size="sm" variant="link" @click.stop="onDownload">
        <span class="fa fa-save" />
    </b-button>
</template>

<script>
import { prependPath } from "utils/redirect";

export default {
    props: {
        item: { type: Object, required: true },
    },
    computed: {
        downloadUrl() {
            return prependPath(`api/datasets/${this.item.id}/display?to_ext=${this.item.extension}`);
        },
        metaDownloadUrl() {
            return prependPath(`dataset/get_metadata_file?hda_id=${this.item.id}&metadata_name=`);
        },
        metaFiles() {
            console.log(this.item);
            return this.item.meta_files;
        },
    },
    methods: {
        onDownload() {
            window.location.href = this.downloadUrl;
        },
    },
};
</script>
