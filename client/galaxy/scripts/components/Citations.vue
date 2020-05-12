<template>
    <div>
        <b-card class="citation-card" v-if="!simple" header-tag="nav">
            <template v-slot:header>
                <b-nav card-header tabs>
                    <b-nav-item :active="!outputBibtex" @click="toggleOutput">Citations</b-nav-item>
                    <b-nav-item :active="outputBibtex" @click="toggleOutput">BibTeX</b-nav-item>
                </b-nav>
            </template>
            <div v-if="source === 'histories'" class="infomessage">
                When writing up your analysis, remember to include all references that should be cited in order to
                completely describe your work. Also, please remember to
                <a href="https://galaxyproject.org/citing-galaxy">cite Galaxy</a>.
            </div>
            <div class="citations-formatted">
                <template v-for="citation in formattedCitations">
                    <div class="formatted-reference" v-html="citation"></div>
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
                        <div class="formatted-reference" v-html="citation"></div>
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
            outputBibtex: false,
        };
    },
    computed: {
        outputStyle() {
            return this.outputBibtex ? "bibtex" : "citation-apa";
        },
        formattedCitations() {
            return this.citations.length === 0
                ? []
                : this.citations.map((c) => {
                      return c.get({ format: "string", type: "html", style: this.outputStyle });
                  });
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
                        this.citations.push(cite);
                    } catch (err) {
                        console.warn(`Error parsing bibtex: ${err}`);
                    }
                });
            })
            .catch((e) => {
                console.error(e);
            });
    },
    methods: {
        toggleOutput() {
            this.outputBibtex = !this.outputBibtex;
        },
    },
};
</script>
<style>
.citation-card .card-header .nav-tabs {
    margin-bottom: -0.75rem !important;
}
</style>
