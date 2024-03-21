<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCopy, faExternalLinkAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import { copy } from "@/utils/clipboard";
import localize from "@/utils/localization";

import DatasetSourceTransform from "@/components/DatasetInformation/DatasetSourceTransform.vue";

library.add(faCopy, faExternalLinkAlt);

interface Props {
    source: {
        source_uri: string;
        transform: {
            action: "to_posix_lines" | "spaces_to_tabs" | "datatype_groom";
            datatype_ext: "bam" | "qname_sorted.bam" | "qname_input_sorted.bam" | "isa-tab" | "isa-json";
        }[];
    };
}

const props = defineProps<Props>();

const sourceUri = computed(() => {
    return props.source.source_uri;
});
const browserCompatUri = computed(() => {
    return sourceUri.value && (sourceUri.value.indexOf("http") == 0 || sourceUri.value.indexOf("ftp") == 0);
});

function copyLink() {
    copy(sourceUri.value, localize("Link copied to your clipboard"));
}
</script>

<template>
    <li class="dataset-source">
        <a v-if="browserCompatUri" v-b-tooltip.hover title="Dataset Source URL" :href="sourceUri" target="_blank">
            {{ source.source_uri }}
            <FontAwesomeIcon :icon="faExternalLinkAlt" />
        </a>
        <span v-else>
            {{ source.source_uri }}
        </span>

        <span v-b-tooltip.hover title="Copy URI">
            <FontAwesomeIcon :icon="faCopy" style="cursor: pointer" @click="copyLink" />
        </span>

        <br />

        <DatasetSourceTransform :transform="source.transform" />
    </li>
</template>
