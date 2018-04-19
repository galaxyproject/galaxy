<template>
    <div class="toolForm">
        <div class="toolFormTitle">
            Citations
            <button v-if="viewRender" v-on:click="toggleViewRender" type="button" class="btn btn-sm btn-secondary citations-to-bibtex" title="Show all in BibTeX format.">
                <i class="fa fa-pencil-square-o"></i>
                Show BibTeX
            </button>
            <button v-else type="button" v-on:click="toggleViewRender" class="btn btn-sm btn-secondary citations-to-formatted" title="Return to formatted citation list.">
                <i class="fa fa-times"></i>
                Hide BibTeX
            </button>
        </div>
        <div class="citations-bibtex toolFormBody citation-padding">
            <div v-if="source === 'histories'" class="infomessage">
                When writing up your analysis, remember to include all references that should be cited in order
                to completely describe your work. Also, please remember to <a href="https://galaxyproject.org/citing-galaxy">cite Galaxy</a>.
            </div>
            <span v-if="viewRender" class="citations-formatted">
                <p v-html="formattedReferences">
                </p>
            </span>
            <textarea v-else class="citations-bibtex-text">
                {{ content }}
            </textarea>
        </div>
    </div>
</template>
<script>
import axios from "axios";
import * as bibtexParse from "libs/bibtexParse";
import { convertLaTeX } from "latex-to-unicode-converter";
import { stringifyLaTeX } from "latex-parser";

export default {
    props: {
        source: {
            type: String,
            required: true
        },
        id: {
            type: String,
            required: true
        },
        viewRender: {
            type: Boolean,
            requried: false,
            default: true
        }
    },
    data() {
        return {
            citations: [],
            content: "",
            errors: []
        };
    },
    computed: {
        formattedReferences: function() {
            return this.citations.reduce(
                (a, b) => a.concat(`<p class="formatted-reference">${this.formattedReference(b)}</p>`),
                ""
            );
        }
    },
    created: function() {
        axios
            .get(`${Galaxy.root}api/${this.source}/${this.id}/citations`)
            .then(response => {
                this.content = "";
                for (var rawCitation of response.data) {
                    try {
                        var citation = {
                            fields: {},
                            entryType: undefined
                        };
                        var parsed = bibtexParse.toJSON(rawCitation.content);
                        if (parsed) {
                            parsed = _.first(parsed);
                            citation.entryType = parsed.entryType || undefined;
                            for (var key in parsed.entryTags) {
                                citation.fields[key.toLowerCase()] = parsed.entryTags[key];
                            }
                        }
                        this.citations.push(citation);
                        this.content += rawCitation.content;
                    } catch (err) {
                        console.warn("Error parsing bibtex: " + err);
                    }
                }
            })
            .catch(e => {
                console.error(e);
            });
    },
    methods: {
        formattedReference: function(citation) {
            var entryType = citation.entryType;
            var fields = citation.fields;

            var ref = "";
            var authorsAndYear = `${this._asSentence(
                (fields.author ? fields.author : "") + (fields.year ? ` (${fields.year})` : "")
            )} `;
            var title = fields.title || "";
            var pages = fields.pages ? `pp. ${fields.pages}` : "";
            var address = fields.address;
            if (entryType == "article") {
                var volume =
                    (fields.volume ? fields.volume : "") +
                    (fields.number ? ` (${fields.number})` : "") +
                    (pages ? `, ${pages}` : "");
                ref = `${authorsAndYear +
                    this._asSentence(title) +
                    (fields.journal ? `In <em>${fields.journal}, ` : "") +
                    this._asSentence(volume) +
                    this._asSentence(fields.address)}</em>`;
            } else if (entryType == "inproceedings" || entryType == "proceedings") {
                ref = `${authorsAndYear +
                    this._asSentence(title) +
                    (fields.booktitle ? `In <em>${fields.booktitle}, ` : "") +
                    (pages ? pages : "") +
                    (address ? `, ${address}` : "")}.</em>`;
            } else if (entryType == "mastersthesis" || entryType == "phdthesis") {
                ref =
                    authorsAndYear +
                    this._asSentence(title) +
                    (fields.howpublished ? `${fields.howpublished}. ` : "") +
                    (fields.note ? `${fields.note}.` : "");
            } else if (entryType == "techreport") {
                ref =
                    authorsAndYear +
                    this._asSentence(title) +
                    this._asSentence(fields.institution) +
                    this._asSentence(fields.number) +
                    this._asSentence(fields.type);
            } else if (entryType == "book" || entryType == "inbook" || entryType == "incollection") {
                ref = `${authorsAndYear} ${this._formatBookInfo(fields)}`;
            } else {
                ref = `${authorsAndYear} ${this._asSentence(title)}${this._asSentence(
                    fields.howpublished
                )}${this._asSentence(fields.note)}`;
            }
            var doiUrl = "";
            if (fields.doi) {
                doiUrl = `http://dx.doi.org/${fields.doi}`;
                ref += `[<a href="${doiUrl}" target="_blank">doi:${fields.doi}</a>]`;
            }
            var url = fields.url || doiUrl;
            if (url) {
                ref += `[<a href="${url}" target="_blank">Link</a>]`;
            }
            return convertLaTeX({ onError: (error, latex) => `{${stringifyLaTeX(latex)}}` }, ref);
        },
        _formatBookInfo: function(fields) {
            var info = "";
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
        _asSentence: function(str) {
            return str && str.trim() ? `${str}. ` : "";
        },
        toggleViewRender: function() {
            this.viewRender = !this.viewRender;
        }
    }
};
</script>
<style>
.citations-formatted {
    word-wrap: break-word;
}

.citations-bibtex-text {
    width: 100%;
    height: 500px;
}

.citation-padding {
    padding: 5px 10px;
}
</style>
