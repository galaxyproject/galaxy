<template>
    <li class="dataset-source">
        <a v-if="browserCompatUri" v-b-tooltip.hover title="Dataset Source URL" :href="sourceUri" target="_blank">
            {{ source.source_uri }}
            <FontAwesomeIcon icon="external-link-alt" />
        </a>
        <span v-else>
            {{ source.source_uri }}
        </span>
        <span v-b-tooltip.hover title="Copy URI"
            ><FontAwesomeIcon icon="copy" style="cursor: pointer" @click="copyLink"
        /></span>
        <br />
        <DatasetSourceTransform :transform="source.transform" />
    </li>
</template>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCopy, faExternalLinkAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { copy } from "utils/clipboard";
import _l from "utils/localization";

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
            copy(this.sourceUri, _l("Link copied to your clipboard"));
        },
    },
};
</script>
