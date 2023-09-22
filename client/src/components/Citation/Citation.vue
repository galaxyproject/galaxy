<template>
    <div>
        {{ prefix }}
        <span v-html="citationHtml" />
        <a v-if="link" :href="link" target="_blank">Visit Citation <font-awesome-icon icon="external-link-alt" /> </a>
    </div>
</template>

<script>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faExternalLinkAlt } from "@fortawesome/free-solid-svg-icons";

library.add(faExternalLinkAlt);

export default {
    components: {
        FontAwesomeIcon,
    },
    props: {
        citation: {
            type: Object,
            required: true,
        },
        outputFormat: {
            type: String,
            default: "bibliography",
        },
        prefix: {
            type: String,
            default: "",
        },
    },
    computed: {
        link() {
            const citeUrl = this.citation.cite?.data?.[0]?.URL;
            return citeUrl ? decodeURIComponent(citeUrl) : null;
        },
        citationHtml() {
            const citation = this.citation;
            const cite = citation.cite;
            const formattedCitation = cite.format(this.outputFormat, {
                format: "html",
                template: "apa",
                lang: "en-US",
            });
            return formattedCitation;
        },
    },
};
</script>

<style>
.csl-bib-body {
    display: inline;
}
.csl-entry {
    display: inline;
}
</style>
