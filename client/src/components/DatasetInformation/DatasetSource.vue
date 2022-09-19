<template>
    <li class="dataset-source">
        <a v-if="browserCompatUri" :href="sourceUri" target="_blank">
            {{ source.source_uri }}
            <font-awesome-icon v-b-tooltip.hover title="Dataset Source URL" icon="external-link-alt" />
        </a>
        <span v-else>
            {{ source.source_uri }}
        </span>
        <font-awesome-icon v-b-tooltip.hover title="Copy URI" icon="copy" style="cursor: pointer" @click="copyLink" />
        <br />
        <DatasetSourceTransform :transform="source.transform" />
    </li>
</template>

<script>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCopy, faExternalLinkAlt } from "@fortawesome/free-solid-svg-icons";
import { copy } from "utils/clipboard";
import DatasetSourceTransform from "./DatasetSourceTransform";

library.add(faCopy, faExternalLinkAlt);

export default {
    components: {
        DatasetSourceTransform,
        FontAwesomeIcon,
    },
    props: {
        source: {
            type: Object,
            required: true,
        },
    },
    computed: {
        browserCompatUri() {
            const sourceUri = this.sourceUri;
            return sourceUri && (sourceUri.indexOf("http") == 0 || sourceUri.indexOf("ftp") == 0);
        },
        sourceUri() {
            return this.source.source_uri;
        },
    },
    methods: {
        copyLink() {
            copy(this.sourceUri, "Link copied to the clipboard.");
        },
    },
};
</script>
