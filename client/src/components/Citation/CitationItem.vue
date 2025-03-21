<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faExternalLinkAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import { type Citation } from ".";

library.add(faExternalLinkAlt);

interface Props {
    citation: Citation;
    outputFormat?: string;
    prefix?: string;
}

const props = withDefaults(defineProps<Props>(), {
    outputFormat: "bibliography",
    prefix: "",
});

const link = computed(() => {
    const citeUrl = props.citation.cite?.data?.[0]?.URL;
    return citeUrl ? decodeURIComponent(citeUrl) : null;
});
const citationHtml = computed(() => {
    const citation = props.citation;
    const cite = citation.cite;
    const formattedCitation = cite.format(props.outputFormat, {
        format: "html",
        template: "apa",
        lang: "en-US",
    });
    return formattedCitation;
});
</script>

<template>
    <div>
        {{ prefix }}
        <span v-html="citationHtml" />

        <a v-if="link" :href="link" target="_blank">
            访问引用
            <FontAwesomeIcon :icon="faExternalLinkAlt" />
        </a>
    </div>
</template>

<style>
.csl-bib-body {
    display: inline;
}
.csl-entry {
    display: inline;
}
</style>
