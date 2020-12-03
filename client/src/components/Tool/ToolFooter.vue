<template>
    <div class="tool-footer">
        <!-- <b-button v-b-toggle.collapse-about>About this tool</b-button> -->
        <b-link
            :aria-expanded="expanded"
            aria-controls="collapse-about"
            class="collapse-about"
            @click="expanded = !expanded"
            >About this tool
            <font-awesome-icon :icon="expanded ? 'angle-double-up' : 'angle-double-down'" />
        </b-link>
        <b-collapse id="collapse-about" class="mt-2" v-model="expanded">
            <b-card>
                <div v-if="hasCitations" class="metadata-section">
                    <span class="metadata-key">Citations:</span>
                    <font-awesome-icon
                        v-b-tooltip.hover
                        title="Copy all citations as BibTeX"
                        icon="copy"
                        style="cursor: pointer;"
                        @click="copyBibtex"
                    />
                    <Citation
                        class="formatted-reference"
                        v-for="(citation, index) in citations"
                        :key="index"
                        :citation="citation"
                        output-format="bibliography"
                        prefix="-"
                    />
                </div>
                <div v-if="hasRequirements" class="metadata-section">
                    <span class="metadata-key"
                        >Requirements:
                        <a href="https://galaxyproject.org/tools/requirements/" target="_blank">
                            <font-awesome-icon
                                v-b-tooltip.hover
                                title="Learn more about Galaxy Requirements"
                                icon="question"
                            />
                        </a>
                    </span>
                    <div v-for="(requirement, index) in requirements" :key="index">
                        - {{ requirement.name }}
                        <span v-if="requirement.version"> (Version {{ requirement.version }}) </span>
                    </div>
                </div>
                <div class="metadata-section" v-if="license">
                    <span class="metadata-key">License:</span>
                    <License :licenseId="license" />
                </div>
                <div v-if="hasReferences" class="metadata-section">
                    <span class="metadata-key">References:</span>
                    <div v-for="(xref, index) in xrefs" :key="index">
                        - {{ xref.reftype }}:
                        <template v-if="xref.reftype == 'bio.tools'">
                            {{ xref.value }}
                            (<a :href="`https://bio.tools/${xref.value}`" target="_blank"
                                >bio.tools
                                <font-awesome-icon
                                    v-b-tooltip.hover
                                    title="Visit bio.tools reference"
                                    icon="external-link-alt"
                                /> </a
                            >) (<a :href="`https://openebench.bsc.es/tool/${xref.value}`" target="_blank"
                                >OpenEBench
                                <font-awesome-icon
                                    v-b-tooltip.hover
                                    title="Visit OpenEBench reference"
                                    icon="external-link-alt"
                                /> </a
                            >)
                        </template>
                        <template v-else>
                            {{ xref.value }}
                        </template>
                    </div>
                </div>
                <div v-if="creators && creators.length > 0" class="metadata-section">
                    <span class="metadata-key">Creators:</span>
                    <Creators :creators="creators" />
                </div>
            </b-card>
        </b-collapse>
    </div>
</template>

<script>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faQuestion, faCopy, faAngleDoubleDown, faAngleDoubleUp } from "@fortawesome/free-solid-svg-icons";

library.add(faQuestion, faCopy, faAngleDoubleDown, faAngleDoubleUp);

import { getCitations } from "components/Citation/services";
import Citation from "components/Citation/Citation.vue";
import License from "components/License/License.vue";
import Creators from "components/SchemaOrg/Creators.vue";
import { copy } from "utils/clipboard";

export default {
    components: {
        Citation,
        License,
        Creators,
        FontAwesomeIcon,
    },
    props: {
        id: {
            type: String,
        },
        hasCitations: {
            type: Boolean,
            default: true,
        },
        xrefs: {
            type: Array,
        },
        license: {
            type: String,
        },
        creators: {
            type: Array,
        },
        requirements: {
            type: Array,
        },
    },
    computed: {
        hasRequirements() {
            return this.requirements && this.requirements.length > 0;
        },
        hasRequirements() {
            return this.xrefs && this.xrefs.length > 0
        },
    }
    data() {
        return {
            citations: [],
            expanded: false,
        };
    },
    created() {
        if (this.hasCitations) {
            getCitations("tools", this.id)
                .then((citations) => {
                    this.citations = citations;
                })
                .catch((e) => {
                    console.error(e);
                });
        }
    },
    methods: {
        copyBibtex() {
            var text = "";
            this.citations.forEach((citation) => {
                const cite = citation.cite;
                const bibtex = cite.format("bibtex", {});
                text += bibtex;
            });
            copy(text, "Citations copied to your clipboard as BibTeX");
        },
    },
};
</script>

<style scoped>
.metadata-key {
    font-weight: bold;
}
.metadata-section {
    margin-bottom: 5px;
}
</style>
