<template>
    <b-dropdown
        v-if="hasMetaFiles"
        dropup
        no-caret
        no-flip
        v-b-tooltip.top.hover
        size="sm"
        variant="link"
        toggle-class="text-decoration-none"
        title="Download"
        data-description="dataset download">
        <template v-slot:button-content>
            <span class="fa fa-save" />
        </template>
        <b-dropdown-item v-localize @click.stop="onDownload(downloadUrl)"> Download Dataset </b-dropdown-item>
        <b-dropdown-item
            v-for="(metaFile, index) of metaFiles"
            :key="index"
            @click.stop="onDownload(metaDownloadUrl, metaFile.file_type)">
            Download {{ metaFile.file_type }}
        </b-dropdown-item>
    </b-dropdown>
    <b-button
        v-else
        class="download-btn px-1"
        title="Download"
        size="sm"
        variant="link"
        @click.stop="onDownload(downloadUrl)">
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
        hasMetaFiles() {
            return this.metaFiles && this.metaFiles.length > 0;
        },
        metaDownloadUrl() {
            return prependPath(`dataset/get_metadata_file?hda_id=${this.item.id}&metadata_name=`);
        },
        metaFiles() {
            return this.item.meta_files;
        },
    },
    methods: {
        onDownload(resource, extension = "") {
            window.location.href = `${resource}${extension}`;
        },
    },
};
</script>
