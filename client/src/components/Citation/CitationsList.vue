<script setup lang="ts">
import { BButton, BCard, BCollapse, BNav, BNavItem } from "bootstrap-vue";
import { onMounted, onUpdated, ref } from "vue";

import { getCitations } from "@/components/Citation/services";
import { useConfig } from "@/composables/config";

import { type Citation } from ".";

import CitationItem from "@/components/Citation/CitationItem.vue";

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
</script>

<template>
    <div>
        <BCard v-if="!simple" class="citation-card" header-tag="nav">
            <template v-slot:header>
                <BNav card-header tabs>
                    <BNavItem
                        :active="outputFormat === outputFormats.CITATION"
                        @click="outputFormat = outputFormats.CITATION">
                        Citations (APA)
                    </BNavItem>

                    <BNavItem
                        :active="outputFormat === outputFormats.BIBTEX"
                        @click="outputFormat = outputFormats.BIBTEX">
                        BibTeX
                    </BNavItem>
                </BNav>
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
            <BButton v-b-toggle="id" variant="primary">Citations</BButton>

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
.citation-card .card-header .nav-tabs {
    margin-bottom: -0.75rem !important;
}
.formatted-reference {
    margin-bottom: 0.5rem;
}
</style>
