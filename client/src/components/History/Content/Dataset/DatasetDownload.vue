<template>
    <b-dropdown
        v-if="hasMetaFiles"
        v-b-tooltip.top.hover
        dropup
        no-caret
        no-flip
        size="sm"
        variant="link"
        toggle-class="text-decoration-none"
        title="Download"
        class="download-btn"
        data-description="dataset download">
        <template v-slot:button-content>
            <span class="fa fa-save" />
        </template>
        <b-dropdown-item v-localize :href="downloadUrl" @click.prevent.stop="onDownload(downloadUrl)">
            Download Dataset
        </b-dropdown-item>
        <b-dropdown-item
            v-for="(metaFile, index) of metaFiles"
            :key="index"
            :data-description="`download ${metaFile.file_type}`"
            :href="metaDownloadUrl + metaFile.file_type"
            @click.prevent.stop="onDownload(metaDownloadUrl, metaFile.file_type)">
            Download {{ metaFile.file_type }}
        </b-dropdown-item>
    </b-dropdown>
    <b-button
        v-else
        class="download-btn px-1"
        title="Download"
        size="sm"
        variant="link"
        :href="downloadUrl"
        @click.prevent.stop="onDownload(downloadUrl)">
        <span class="fa fa-save" />
    </b-button>
</template>

<script>
import { prependPath } from "utils/redirect";
import { downloadUrlMixin } from "./mixins.js";

export default {
    mixins: [downloadUrlMixin],
    props: {
        item: { type: Object, required: true },
    },
    computed: {
        hasMetaFiles() {
            return this.metaFiles && this.metaFiles.length > 0;
        },
        metaDownloadUrl() {
            return prependPath(`api/datasets/${this.item.id}/metadata_file?metadata_file=`);
        },
        metaFiles() {
            return this.item.meta_files;
        },
    },
    methods: {
        onDownload(resource, extension = "") {
            this.$emit("on-download", `${resource}${extension}`);
        },
    },
};
</script>
