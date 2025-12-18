<script setup lang="ts">
import {
    faAngleDown,
    faAngleUp,
    faExclamationTriangle,
    faExternalLinkAlt,
    faInfoCircle,
    faLayerGroup,
    faSitemap,
    faUser,
    faWrench,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BPopover, BSkeleton } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import { useFormattedToolHelp } from "@/composables/formattedToolHelp";
import { useToolStore } from "@/stores/toolStore";

import type { CardBadge } from "../Common/GCard.types";
import { useToolsListCardActions } from "./useToolsListCardActions";

import GButton from "../BaseComponents/GButton.vue";
import GCard from "../Common/GCard.vue";
import GLink from "@/components/BaseComponents/GLink.vue";

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
    formStyle?: string;
    description?: string;
    summary?: string;
    help?: string;
    version?: string;
    link?: string;
    workflowCompatible: boolean;
    local: boolean;
    owner?: string;
    fetching: boolean;
    gridView?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    id: "",
    name: "",
    section: undefined,
    formStyle: undefined,
    description: undefined,
    summary: undefined,
    help: undefined,
    version: undefined,
    link: undefined,
    workflowCompatible: false,
    local: false,
    owner: undefined,
    fetching: false,
    gridView: false,
});

const emit = defineEmits<{
    (e: "apply-filter", filter: string, value: string): void;
}>();

const { panelSections } = storeToRefs(useToolStore());

function getOntologyBadges(view: "ontology:edam_operations" | "ontology:edam_topics", ids: string[]): OntologyBadge[] {
    if (ids?.length) {
        const sections = panelSections.value(view);
        return ids
            .map((id) => sections.find((section) => section.id === id))
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
const showPopover = ref(false);

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

const routeTo = computed(() =>
    props.id !== "upload1" && props.local && props.formStyle === "regular"
        ? `/?tool_id=${encodeURIComponent(props.id)}${props.version ? `&version=${props.version}` : ""}`
        : undefined,
);

const routeHref = computed(() => (!props.local ? props.link : undefined));

const toolBadges = computed<CardBadge[]>(() => {
    const badges = [];
    if (!props.local) {
        badges.push({
            id: "external-tool",
            label: "External",
            title: "This tool opens in an external site",
            visible: true,
            icon: faExternalLinkAlt,
        });
    }
    if (props.owner) {
        badges.push({
            id: "tool-owner",
            label: props.owner,
            title: "The Toolshed Repository Owner",
            visible: true,
            icon: faUser,
        });
    }
    return badges;
});

const {
    favoriteToolAction: bookmark,
    toolsListCardPrimaryActions,
    toolsListCardSecondaryActions,
    openUploadIfNeeded,
} = useToolsListCardActions(
    props.id,
    props.local,
    props.name,
    props.formStyle,
    props.version,
    routeTo.value,
    routeHref.value,
);
</script>

<template>
    <GCard
        :id="props.id"
        class="tool-list-item"
        :badges="toolBadges"
        :grid-view="props.gridView"
        :bookmarked="bookmark.label === 'Unfavorite'"
        :show-bookmark="!bookmark.title.includes('Login')"
        :primary-actions="toolsListCardPrimaryActions"
        :secondary-actions="toolsListCardSecondaryActions"
        @bookmark="bookmark.handler">
        <template v-slot:title>
            <h4 class="py-1 d-flex flex-wrap text-wrap flex-gapx-1">
                <span>
                    <FontAwesomeIcon v-if="props.local" :icon="faWrench" fixed-width />
                    <FontAwesomeIcon v-else :icon="faExternalLinkAlt" fixed-width />

                    <GLink v-if="routeTo || routeHref" dark :to="routeTo" :href="routeHref" @click="openUploadIfNeeded">
                        <b>{{ props.name }}</b>
                    </GLink>
                    <span v-else
                        ><b>{{ props.name }}</b></span
                    >
                </span>
                <span itemprop="description">{{ props.description }}</span>
            </h4>
        </template>

        <template v-slot:indicators>
            <GButton
                v-if="props.version || !props.workflowCompatible"
                :id="`tools-list-${props.id}`"
                icon-only
                transparent
                inline
                style="cursor: help"
                @click="showPopover = !showPopover">
                <FontAwesomeIcon :icon="faInfoCircle" fixed-width />
            </GButton>
            <BPopover
                v-if="props.version || !props.workflowCompatible"
                :show.sync="showPopover"
                custom-class="tool-info-popover"
                boundary="window"
                placement="topleft"
                :target="`tools-list-${props.id}`"
                triggers="hover">
                <div class="d-flex flex-column flex-gapy-1 text-center">
                    <div>Galaxy Version {{ props.version }}</div>

                    <div v-if="!props.workflowCompatible" class="tag warn">
                        <FontAwesomeIcon :icon="faExclamationTriangle" />
                        Not Workflow compatible
                    </div>
                </div>
            </BPopover>
        </template>

        <template v-slot:description>
            <div v-if="props.fetching && !props.help">
                <BSkeleton />
            </div>

            <!-- eslint-disable-next-line vue/no-v-html -->
            <div v-else-if="props.summary && !showHelp" v-html="props.summary"></div>

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
                <div
                    v-if="showHelp"
                    data-description="tools list tool help"
                    class="mt-2"
                    v-html="formattedToolHelp"></div>
            </div>
        </template>

        <template v-slot:update-time>
            <div class="d-flex flex-gapx-1 flex-gapy-1 flex-wrap py-2">
                <span v-if="props.section" class="tag info">
                    <FontAwesomeIcon :icon="faLayerGroup" />
                    <GLink thin @click="() => emit('apply-filter', 'section', quotedSection)">{{ section }}</GLink>
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
        </template>
    </GCard>
</template>

<style lang="scss" scoped>
@import "@/style/scss/theme/blue.scss";

// Styling for the section and ontology tags
.tool-info-popover,
.tool-list-item {
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
}
</style>
