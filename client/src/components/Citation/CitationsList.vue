<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCopy } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BCard, BCollapse, BNav, BNavItem } from "bootstrap-vue";
import { onMounted, onUpdated, ref } from "vue";

import { getCitations } from "@/components/Citation/services";
import { useConfig } from "@/composables/config";
import { copy } from "@/utils/clipboard";

import type { Citation } from ".";

import CitationItem from "@/components/Citation/CitationItem.vue";

library.add(faCopy);

const outputFormats = Object.freeze({
    CITATION: "bibliography",
    BIBTEX: "bibtex",
    RAW: "raw",
});

interface Props {
    id: string;
    source: string;
    simple?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    simple: false,
});

const { config } = useConfig(true);

const emit = defineEmits(["rendered", "show", "shown", "hide", "hidden"]);

const outputFormat = ref<string>(outputFormats.CITATION);
const citations = ref<Citation[]>([]);

onUpdated(() => {
    emit("rendered");
});

onMounted(async () => {
    try {
        citations.value = await getCitations(props.source, props.id);
    } catch (e) {
        console.error(e);
    }
});

function copyBibtex() {
    let text = "";
    citations.value.forEach((citation) => {
        const cite = citation.cite;
        const bibtex = cite.format("bibtex", {
            format: "text",
            template: "bibtex",
            lang: "en-US",
        });
        text += bibtex;
    });
    copy(text, "References copied to your clipboard as BibTeX");
}
</script>

<template>
    <div>
        <BCard v-if="!simple" class="citation-card" header-tag="nav">
            <template v-slot:header>
                <BNav card-header tabs>
                    <BNavItem
                        :active="outputFormat === outputFormats.CITATION"
                        @click="outputFormat = outputFormats.CITATION">
                        References (APA)
                    </BNavItem>

                    <BNavItem
                        :active="outputFormat === outputFormats.BIBTEX"
                        @click="outputFormat = outputFormats.BIBTEX">
                        BibTeX
                    </BNavItem>
                </BNav>
                <BButton
                    v-if="outputFormat === outputFormats.BIBTEX"
                    v-b-tooltip.hover
                    title="Copy all references as BibTeX"
                    variant="link"
                    size="sm"
                    class="copy-bibtex-btn"
                    @click="copyBibtex">
                    <FontAwesomeIcon icon="copy" />
                </BButton>
            </template>

            <div v-if="source === 'histories'" class="infomessage">
                <div v-html="config?.citations_export_message_html"></div>
            </div>

            <div class="citations-formatted">
                <CitationItem
                    v-for="(citation, index) in citations"
                    :key="index"
                    class="formatted-reference"
                    :citation="citation"
                    :output-format="outputFormat" />
            </div>
        </BCard>
        <div v-else-if="citations.length">
            <BButton v-b-toggle="id" variant="primary">References</BButton>

            <BCollapse
                :id="id.replace(/ /g, '_')"
                class="mt-2"
                @show="$emit('show')"
                @shown="$emit('shown')"
                @hide="$emit('hide')"
                @hidden="$emit('hidden')">
                <BCard>
                    <CitationItem
                        v-for="(citation, index) in citations"
                        :key="index"
                        class="formatted-reference"
                        :citation="citation"
                        :output-format="outputFormat" />
                </BCard>
            </BCollapse>
        </div>
    </div>
</template>

<style scoped lang="scss">
.citation-card .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.citation-card .card-header .nav-tabs {
    margin-bottom: -0.75rem !important;
}
.formatted-reference {
    margin-bottom: 0.5rem;
}
.copy-bibtex-btn {
    margin-left: auto;
    padding: 0.25rem 0.5rem;
}
</style>
