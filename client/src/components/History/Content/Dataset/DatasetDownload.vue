<template>
    <GDropdown
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
        <GDropdownItem v-localize :href="downloadUrl" @click.prevent.stop="onDownload(downloadUrl)">
            Download Dataset
        </GDropdownItem>
        <GDropdownItem
            v-for="(metaFile, index) of metaFiles"
            :key="index"
            :data-description="`download ${metaFile.file_type}`"
            :href="metaDownloadUrl + metaFile.file_type"
            @click.prevent.stop="onDownload(metaDownloadUrl, metaFile.file_type)">
            Download {{ metaFile.file_type }}
        </GDropdownItem>
    </GDropdown>
    <GButton
        v-else
        class="download-btn px-1"
        title="Download"
        size="sm"
        variant="link"
        :href="downloadUrl"
        @click.prevent.stop="onDownload(downloadUrl)">
        <span class="fa fa-save" />
    </GButton>
</template>

<script>
import GButton from "component-library/GButton";
import { prependPath } from "utils/redirect";

import { downloadUrlMixin } from "./mixins.js";

import GDropdown from "@/component-library/GDropdown.vue";
import GDropdownItem from "@/component-library/GDropdownItem.vue";

export default {
    components: {
        GButton,
        GDropdown,
        GDropdownItem,
    },
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
