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
import * as bibtexParse from "libs/bibtexParse";
import { convertLaTeX } from "latex-to-unicode-converter";
import { stringifyLaTeX } from "latex-parser";

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
                        const citation = {
                            fields: {},
                            entryType: undefined,
                        };
                        let parsed = bibtexParse.toJSON(rawCitation.content);
                        if (parsed) {
                            parsed = _.first(parsed);
                            citation.entryType = parsed.entryType || undefined;
                            Object.keys(parsed.entryTags).forEach((key) => {
                                citation.fields[key.toLowerCase()] = parsed.entryTags[key];
                            });
                        }
                        this.citations.push(citation);
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
        formattedReference(citation) {
            const { entryType, fields } = citation;

            let ref = "";
            const authorsAndYear = `${this.asSentence(
                (fields.author ? fields.author : "") + (fields.year ? ` (${fields.year})` : "")
            )} `;
            const title = fields.title || "";
            const pages = fields.pages ? `pp. ${fields.pages}` : "";
            const { address } = fields;
            if (entryType === "article") {
                const volume =
                    (fields.volume ? fields.volume : "") +
                    (fields.number ? ` (${fields.number})` : "") +
                    (pages ? `, ${pages}` : "");
                ref = `${
                    authorsAndYear +
                    this.asSentence(title) +
                    (fields.journal ? `In <em>${fields.journal}, ` : "") +
                    this.asSentence(volume) +
                    this.asSentence(fields.address)
                }</em>`;
            } else if (entryType === "inproceedings" || entryType === "proceedings") {
                ref = `${
                    authorsAndYear +
                    this.asSentence(title) +
                    (fields.booktitle ? `In <em>${fields.booktitle}, ` : "") +
                    (pages || "") +
                    (address ? `, ${address}` : "")
                }.</em>`;
            } else if (entryType === "mastersthesis" || entryType === "phdthesis") {
                ref =
                    authorsAndYear +
                    this.asSentence(title) +
                    (fields.howpublished ? `${fields.howpublished}. ` : "") +
                    (fields.note ? `${fields.note}.` : "");
            } else if (entryType === "techreport") {
                ref =
                    authorsAndYear +
                    this.asSentence(title) +
                    this.asSentence(fields.institution) +
                    this.asSentence(fields.number) +
                    this.asSentence(fields.type);
            } else if (entryType === "book" || entryType === "inbook" || entryType === "incollection") {
                ref = `${authorsAndYear} ${this.formatBookInfo(fields)}`;
            } else {
                ref = `${authorsAndYear} ${this.asSentence(title)}${this.asSentence(
                    fields.howpublished
                )}${this.asSentence(fields.note)}`;
            }
            if (fields.doi) {
                ref += `[<a href="https://doi.org/${fields.doi}" target="_blank">doi:${fields.doi}</a>]`;
            }
            if (fields.url) {
                ref += `[<a href="${fields.url}" target="_blank">Link</a>]`;
            }
            return convertLaTeX({ onError: (error, latex) => `{${stringifyLaTeX(latex)}}` }, ref);
        },
        formatBookInfo(fields) {
            let info = "";
            if (fields.chapter) {
                info += `${fields.chapter} in `;
            }
            if (fields.title) {
                info += `<em>${fields.title}</em>`;
            }
            if (fields.editor) {
                info += `, Edited by ${fields.editor}, `;
            }
            if (fields.publisher) {
                info += `, ${fields.publisher}`;
            }
            if (fields.pages) {
                info += `, pp. ${fields.pages}`;
            }
            if (fields.series) {
                info += `, <em>${fields.series}</em>`;
            }
            if (fields.volume) {
                info += `, Vol.${fields.volume}`;
            }
            if (fields.issn) {
                info += `, ISBN: ${fields.issn}`;
            }
            return `${info}.`;
        },
        asSentence(str) {
            return str && str.trim() ? `${str}. ` : "";
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
