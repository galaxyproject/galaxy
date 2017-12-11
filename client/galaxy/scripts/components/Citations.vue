<template>
    <div>
        <b-card v-if="!simple">
            <template v-slot:header>
                <h4 class="mb-0">
                    Citations
                    <b-button
                        v-if="viewRender"
                        title="Show all in BibTeX format."
                        class="citations-to-bibtex"
                        @click="toggleViewRender"
                    >
                        <i class="fa fa-pencil-square-o"></i> Show BibTeX
                    </b-button>
                    <b-button v-else title="Return to formatted citation list." @click="toggleViewRender">
                        <i class="fa fa-times"></i> Hide BibTeX
                    </b-button>
                </h4>
            </template>
            <div v-if="source === 'histories'" class="infomessage">
                When writing up your analysis, remember to include all references that should be cited in order to
                completely describe your work. Also, please remember to
                <a href="https://galaxyproject.org/citing-galaxy">cite Galaxy</a>.
            </div>
            <span v-if="viewRender" class="citations-formatted">
                <p v-html="formattedReferences"></p>
            </span>
            <pre v-else>
            <code class="citations-bibtex">
                {{ content }}
            </code>
        </pre>
        </b-card>
        <div v-else-if="citations.length">
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
                    <p v-html="formattedReferences"></p>
                </b-card>
            </b-collapse>
        </div>
    </div>
</template>
<script>
import _ from "underscore";
import axios from "axios";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { getAppRoot } from "onload/loadConfig";
import Cite from "citation-js";

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
        viewRender: {
            type: Boolean,
            requried: false,
            default: true,
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
            content: "",
            errors: [],
            showCollapse: false,
        };
    },
    computed: {
        formattedReferences() {
            return this.citations.reduce(
                (a, b) => a.concat(`<p class="formatted-reference">${this.formattedReference(b)}</p>`),
                ""
            );
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
                this.content = "";
                response.data.forEach((rawCitation) => {
                    try {
                        let cite = new Cite(rawCitation.content);
                        this.citations.push(cite);
                        this.content += rawCitation.content;
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
        formattedReference: function (citation) {
            return citation.get({ format: "string", type: "html", style: "citation-apa" });
        },
        toggleViewRender() {
            this.viewRender = !this.viewRender;
        },
    },
};
</script>
<style>
pre code {
    white-space: pre-wrap;
}
</style>
