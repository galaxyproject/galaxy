<template>
    <div v-html="citationHtml"></div>
</template>

<script>
export default {
    props: {
        citation: {
            type: Object,
        },
        outputFormat: {
            type: String,
        },
    },
    computed: {
        citationHtml() {
            const citation = this.citation;
            const cite = citation.cite;
            let link = "";
            if (cite.data && cite.data[0] && cite.data[0].URL) {
                link = `&nbsp<a href="${cite.data[0].URL}" target="_blank">[Link]</a>`;
            }
            const formattedCitation = cite.format(this.outputFormat, {
                format: "html",
                template: "apa",
                lang: "en-US",
                append: link,
            });
            return formattedCitation;
        },
    },
};
</script>
