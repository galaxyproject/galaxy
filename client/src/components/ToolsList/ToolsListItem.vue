<script setup lang="ts">
import {
    faAngleDown,
    faAngleUp,
    faExclamationTriangle,
    faExternalLinkAlt,
    faLayerGroup,
    faSitemap,
    faUser,
    faWrench,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BSkeleton } from "bootstrap-vue";
import { computed, ref } from "vue";

import { useFormattedToolHelp } from "@/composables/formattedToolHelp";
import { useToolStore } from "@/stores/toolStore";

import GButton from "../BaseComponents/GButton.vue";
import GLink from "@/components/BaseComponents/GLink.vue";
import ToolFavoriteButton from "@/components/Tool/Buttons/ToolFavoriteButton.vue";

type OntologyBadge = {
    id: string;
    name: string;
};

interface Props {
    id: string;
    name: string;
    section?: string;
    edamOperations: string[];
    edamTopics: string[];
    description?: string;
    summary?: string;
    help?: string;
    version?: string;
    link?: string;
    workflowCompatible: boolean;
    local: boolean;
    owner?: string;
    fetching: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    id: "",
    name: "",
    section: undefined,
    ontologies: undefined,
    description: undefined,
    summary: undefined,
    help: undefined,
    version: undefined,
    link: undefined,
    workflowCompatible: false,
    local: false,
    owner: undefined,
    fetching: false,
});

// TODO: For tool open emit, consider adding event as param to allow for opening tool in new tab
const emit = defineEmits<{
    (e: "open"): void;
    (e: "apply-filter", filter: string, value: string): void;
}>();

const toolStore = useToolStore();

function getOntologyBadges(view: "ontology:edam_operations" | "ontology:edam_topics", ids: string[]): OntologyBadge[] {
    if (ids?.length) {
        const sections = toolStore.getToolSections(view);
        return ids
            .map((id) => sections[id])
            .filter((section) => section !== undefined)
            .map((section) => ({
                id: section.id,
                name: section.name,
            }));
    }
    return [];
}

const edamOperationsBadges = computed(() => getOntologyBadges("ontology:edam_operations", props.edamOperations));

const edamTopicsBadges = computed(() => getOntologyBadges("ontology:edam_topics", props.edamTopics));

const ontologies = computed(() => {
    return edamOperationsBadges.value.concat(edamTopicsBadges.value);
});

const showHelp = ref(false);

const formattedToolHelp = computed(() => {
    if (showHelp.value) {
        const { formattedContent } = useFormattedToolHelp(props.help);
        return formattedContent.value;
    } else {
        return "";
    }
});

/** We add double quotes to the section filter since the backend Whoosh search
 * requires it for exact matches, and the `Filtering` class only does single quotes. */
const quotedSection = computed(() => (props.section ? `"${props.section}"` : ""));

/** We add double quotes to the ontology id filter as well since the backend Whoosh search
 * requires it for exact matches, and the `Filtering` class only does single quotes. */
function quotedOntology(ontology: OntologyBadge) {
    return `"${ontology.id}"`;
}
</script>

<template>
    <div class="tool-list-item">
        <div class="top-bar bg-secondary px-2 py-1 rounded-right">
            <div class="py-1 d-flex flex-wrap flex-gapx-1">
                <span>
                    <FontAwesomeIcon v-if="props.local" :icon="faWrench" fixed-width />
                    <FontAwesomeIcon v-else :icon="faExternalLinkAlt" fixed-width />

                    <GLink v-if="props.local" dark @click="() => emit('open')">
                        <b>{{ props.name }}</b>
                    </GLink>
                    <GLink v-else dark :href="props.link">
                        <b>{{ props.name }}</b>
                    </GLink>
                </span>
                <span itemprop="description">{{ props.description }}</span>
                <span>(Galaxy Version {{ props.version }})</span>
            </div>
            <div class="d-flex align-items-start">
                <div class="d-flex align-items-center flex-gapx-1">
                    <ToolFavoriteButton :id="props.id" color="grey" />

                    <GButton
                        v-if="props.local"
                        class="text-nowrap"
                        color="blue"
                        size="small"
                        @click="() => emit('open')">
                        <FontAwesomeIcon :icon="faWrench" fixed-width />
                        Open
                    </GButton>
                    <GButton v-else class="text-nowrap" color="blue" size="small" :href="props.link">
                        <FontAwesomeIcon :icon="faExternalLinkAlt" fixed-width />
                        Open
                    </GButton>
                </div>
            </div>
        </div>

        <div class="tool-list-item-content">
            <div class="d-flex flex-gapx-1 flex-gapy-1 flex-wrap py-2">
                <span v-if="props.section" class="tag info">
                    <FontAwesomeIcon :icon="faLayerGroup" />
                    <GLink thin @click="() => emit('apply-filter', 'section', quotedSection)">{{ section }}</GLink>
                </span>

                <span v-if="!props.local" class="tag info">
                    <FontAwesomeIcon :icon="faExternalLinkAlt" fixed-width />
                    External
                </span>

                <span v-if="!props.workflowCompatible" class="tag warn">
                    <FontAwesomeIcon :icon="faExclamationTriangle" />
                    Not Workflow compatible
                </span>

                <span v-if="props.owner" class="tag success">
                    <FontAwesomeIcon :icon="faUser" />
                    <b>Owner:</b>
                    <GLink thin @click="emit('apply-filter', 'owner', props.owner)">{{ props.owner }}</GLink>
                </span>

                <span v-for="ontology in ontologies" :key="ontology.id" class="tag toggle">
                    <FontAwesomeIcon :icon="faSitemap" />
                    <GLink
                        thin
                        :title="ontology.id"
                        tooltip
                        @click="() => emit('apply-filter', 'ontology', quotedOntology(ontology))">
                        {{ ontology.name }}
                    </GLink>
                </span>
            </div>

            <div v-if="props.fetching">
                <BSkeleton />
            </div>

            <!-- eslint-disable-next-line vue/no-v-html -->
            <div v-if="props.summary && !showHelp" v-html="props.summary"></div>

            <div v-if="props.help" class="mt-2">
                <GLink v-if="!showHelp" unselectable @click="() => (showHelp = true)">
                    <FontAwesomeIcon :icon="faAngleDown" />
                    Show tool help
                </GLink>
                <GLink v-else unselectable @click="() => (showHelp = false)">
                    <FontAwesomeIcon :icon="faAngleUp" />
                    Hide tool help
                </GLink>

                <!-- eslint-disable-next-line vue/no-v-html -->
                <div v-if="showHelp" class="mt-2" v-html="formattedToolHelp"></div>
            </div>
        </div>
    </div>
</template>

<style lang="scss" scoped>
@import "theme/blue.scss";

.tool-list-item {
    border-left: solid 3px $brand-secondary;
    border-radius: 0.25rem;

    .tool-list-item-content {
        padding-left: 0.5rem;
    }

    .tag {
        border-style: solid;
        border-width: 0 2px 1px 0;
        border-radius: 4px;
        padding: 0 0.5rem;
    }

    .info {
        background-color: scale-color($brand-info, $lightness: +75%);
        border-color: scale-color($brand-info, $lightness: +55%);
    }

    .success {
        background-color: scale-color($brand-success, $lightness: +75%);
        border-color: scale-color($brand-success, $lightness: +55%);
    }

    .warn {
        background-color: scale-color($brand-warning, $lightness: +75%);
        border-color: scale-color($brand-warning, $lightness: +55%);
    }

    .toggle {
        background-color: scale-color($brand-toggle, $lightness: +75%);
        border-color: scale-color($brand-toggle, $lightness: +55%);
    }

    .top-bar {
        display: flex;
        justify-content: space-between;
    }
}
</style>
