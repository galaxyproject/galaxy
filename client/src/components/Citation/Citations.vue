<template>
    <div>
        <GCard v-if="!simple" class="citation-card" header-tag="nav">
            <template v-slot:header>
                <GNav card-header tabs>
                    <GNavItem
                        :active="outputFormat === outputFormats.CITATION"
                        @click="outputFormat = outputFormats.CITATION">
                        Citations (APA)
                    </GNavItem>
                    <GNavItem
                        :active="outputFormat === outputFormats.BIBTEX"
                        @click="outputFormat = outputFormats.BIBTEX">
                        BibTeX
                    </GNavItem>
                </GNav>
            </template>
            <div v-if="source === 'histories'" class="infomessage">
                <div v-html="config.citations_export_message_html"></div>
            </div>
            <div class="citations-formatted">
                <Citation
                    v-for="(citation, index) in citations"
                    :key="index"
                    class="formatted-reference"
                    :citation="citation"
                    :output-format="outputFormat" />
            </div>
        </GCard>
        <div v-else-if="citations.length">
            <GButton v-b-toggle="id" variant="primary">Citations</GButton>
            <GCollapse
                :id="id.replace(/ /g, '_')"
                class="mt-2"
                @show="$emit('show')"
                @shown="$emit('shown')"
                @hide="$emit('hide')"
                @hidden="$emit('hidden')">
                <GCard>
                    <Citation
                        v-for="(citation, index) in citations"
                        :key="index"
                        class="formatted-reference"
                        :citation="citation"
                        :output-format="outputFormat" />
                </GCard>
            </GCollapse>
        </div>
    </div>
</template>
<script>
import { GButton, GCard, GCollapse, GNav, GNavItem } from "@/component-library";
import { useConfig } from "@/composables/config";

import Citation from "./Citation";
import { getCitations } from "./services";

const outputFormats = Object.freeze({
    CITATION: "bibliography",
    BIBTEX: "bibtex",
    RAW: "raw",
});

export default {
    components: {
        GButton,
        GCard,
        GCollapse,
        GNav,
        GNavItem,
        Citation,
    },
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
    setup() {
        const { config } = useConfig(true);
        return { config };
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
    updated() {
        this.$nextTick(() => {
            this.$emit("rendered");
        });
    },
    created() {
        getCitations(this.source, this.id)
            .then((citations) => {
                this.citations = citations;
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
