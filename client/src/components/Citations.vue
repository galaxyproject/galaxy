<template>
    <div>
        <b-card class="citation-card" v-if="!simple" header-tag="nav">
            <template v-slot:header>
                <b-nav card-header tabs>
                    <b-nav-item
                        :active="outputFormat === outputFormats.CITATION"
                        @click="outputFormat = outputFormats.CITATION"
                        >Citations (APA)</b-nav-item
                    >
                    <b-nav-item
                        :active="outputFormat === outputFormats.BIBTEX"
                        @click="outputFormat = outputFormats.BIBTEX"
                        >BibTeX</b-nav-item
                    >
                </b-nav>
            </template>
            <div v-if="source === 'histories'" class="infomessage">
                When writing up your analysis, remember to include all references that should be cited in order to
                completely describe your work. Also, please remember to
                <a href="https://galaxyproject.org/citing-galaxy">cite Galaxy</a>.
            </div>
            <div class="citations-formatted">
                <template v-for="citation in formattedCitations">
                    <div :key="citation" class="formatted-reference" v-html="citation"></div>
                </template>
            </div>
        </b-card>
        <div v-else-if="formattedCitations.length">
            <b-btn v-b-toggle="id" variant="primary">Citations</b-btn>
            <b-collapse
                :id="id.replace(/ /g, '_')"
                class="mt-2"
                @show="$emit('show')"
                @shown="$emit('shown')"
                @hide="$emit('hide')"
                @hidden="$emit('hidden')"
            >
                <b-card>
                    <template v-for="citation in formattedCitations">
                        <div :key="citation" class="formatted-reference" v-html="citation"></div>
                    </template>
                </b-card>
            </b-collapse>
        </div>
    </div>
</template>
<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import axios from "axios";
import Cite from "citation-js";
import { getAppRoot } from "onload/loadConfig";

Vue.use(BootstrapVue);

const outputFormats = Object.freeze({
    CITATION: "bibliography",
    BIBTEX: "bibtex",
    RAW: "raw",
});

export default {
    props: {
        source: {
            type: String,
            required: true,
        },
        id: {
            type: String,
            required: true,
        },
        simple: {
            type: Boolean,
            required: false,
            default: false,
        },
    },
    data() {
        return {
            citations: [],
            errors: [],
            showCollapse: false,
            outputFormats,
            outputFormat: outputFormats.CITATION,
        };
    },
    computed: {
        formattedCitations() {
            const processed = [];
            if (this.citations.length !== 0) {
                for (const c of this.citations) {
                    let link = "";
                    if (c.cite.data && c.cite.data[0] && c.cite.data[0].URL) {
                        link = `&nbsp<a href="${c.cite.data[0].URL}" target="_blank">[Link]</a>`;
                    }
                    const formattedCitation = c.cite.format(this.outputFormat, {
                        format: "html",
                        template: "apa",
                        lang: "en-US",
                        append: link,
                    });
                    processed.push(formattedCitation);
                }
            }
            return processed;
        },
    },
    updated() {
        this.$nextTick(() => {
            this.$emit("rendered");
        });
    },
    created() {
        axios
            .get(`${getAppRoot()}api/${this.source}/${this.id}/citations`)
            .then((response) => {
                response.data.forEach((rawCitation) => {
                    try {
                        const cite = new Cite(rawCitation.content);
                        this.citations.push({ raw: rawCitation.content, cite: cite });
                    } catch (err) {
                        console.warn(`Error parsing bibtex: ${err}`);
                    }
                });
            })
            .catch((e) => {
                console.error(e);
            });
    },
};
</script>
<style>
.citation-card .card-header .nav-tabs {
    margin-bottom: -0.75rem !important;
}
.formatted-reference {
    margin-bottom: 0.5rem;
}
</style>
