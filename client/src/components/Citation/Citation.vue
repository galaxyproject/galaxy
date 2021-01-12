<template>
    <div>
        {{ prefix }}
        <span v-html="citationHtml" />
        <a v-if="link" :href="link" target="_blank">
            <font-awesome-icon v-b-tooltip.hover title="View Citation" icon="external-link-alt" />
        </a>
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
        },
        outputFormat: {
            type: String,
        },
        prefix: {
            type: String,
        },
    },
    computed: {
        link() {
            const cite = this.citation.cite;
            return cite.data && cite.data[0] && cite.data[0].URL;
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
