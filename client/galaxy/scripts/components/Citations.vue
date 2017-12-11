<template>
    <div class="toolForm">
        <div class="toolFormTitle">
            Citations
            <button v-if="viewRender" v-on:click="toggleViewRender" type="button" class="btn btn-xs citations-to-bibtex" title="Show all in BibTeX format.">
                <i class="fa fa-pencil-square-o"></i>
                Show BibTeX
            </button>
            <button v-else type="button" v-on:click="toggleViewRender" class="btn btn-xs citations-to-formatted" title="Return to formatted citation list.">
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
import Cite from "citation-js";

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
            return this.citations.reduce((a, b) => a.concat(`<p class="formatted-reference">${this.formattedReference(b)}</p>`), "");
        }
    },
    created: function() {
        axios
            .get(`${Galaxy.root}api/${this.source}/${this.id}/citations`)
            .then(response => {
                this.content = "";
                for (var rawCitation of response.data) {
                    try {
                        let cite = new Cite(rawCitation.content);
                        this.citations.push(cite);
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
            return citation.get({ format: 'string', type: 'html', style: "citation-apa"});
        },
        toggleViewRender: function() {
            this.viewRender = !this.viewRender;
        }
    }
};
</script>
<style>
.citations-formatted{
    word-wrap: break-word;
}

.citations-bibtex-text{
    width: 100%;
    height: 500px;
}

.citation-padding{
    padding:5px 10px;
}
</style>
