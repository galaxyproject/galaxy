<script setup lang="ts">
import { faStar as farStar } from "@fortawesome/free-regular-svg-icons";
import {
    faAngleDown,
    faAngleUp,
    faExclamationTriangle,
    faExternalLinkAlt,
    faInfoCircle,
    faSitemap,
    faStar as fasStar,
    faTag,
    faUser,
    faWrench,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BSkeleton } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import { useFavoriteObjects } from "@/composables/useFavoriteObjects";
import { useToolStore } from "@/stores/toolStore";

import type { CardBadge } from "../Common/GCard.types";
import { useToolsListCardActions } from "./useToolsListCardActions";

import GButton from "../BaseComponents/GButton.vue";
import GCard from "../Common/GCard.vue";
import ToolHelp from "../Tool/ToolHelp.vue";
import GLink from "@/components/BaseComponents/GLink.vue";
import GPopover from "@/components/BaseComponents/GPopover.vue";

type OntologyBadge = {
    id: string;
    name: string;
};

interface Props {
    id: string;
    name: string;
    edamOperations: string[];
    edamTopics: string[];
    toolTags?: string[];
    formStyle?: string;
    description?: string;
    summary?: string;
    help?: string;
    helpFormat?: string;
    version?: string;
    link?: string;
    workflowCompatible?: boolean;
    local?: boolean;
    owner?: string;
    fetching?: boolean;
    gridView?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    formStyle: undefined,
    description: undefined,
    summary: undefined,
    help: undefined,
    helpFormat: "restructuredtext",
    version: undefined,
    link: undefined,
    workflowCompatible: false,
    local: false,
    owner: undefined,
    fetching: false,
    gridView: false,
    toolTags: () => [],
});

const emit = defineEmits<{
    (e: "apply-filter", filter: string, value: string): void;
}>();

const { canFavorite, isFavorite, isSaving, toggleFavorite } = useFavoriteObjects();
const isAnonymous = computed(() => !canFavorite.value);
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

const showHelp = ref(false);

/** We add double quotes to the ontology id filter as well since the backend Whoosh search
 * requires it for exact matches, and the `Filtering` class only does single quotes. */
function quotedOntology(ontology: OntologyBadge) {
    return `"${ontology.id}"`;
}

function favoriteTagTitle(tag: string) {
    if (isAnonymous.value) {
        return "Login or Register to Favorite Tags";
    }
    if (isFavorite("tags", tag)) {
        return "Remove tag from Favorites";
    }
    return "Add tag to Favorites";
}

function favoriteEdamOperationTitle(ontology: OntologyBadge) {
    if (isAnonymous.value) {
        return "Login or Register to Favorite EDAM Operations";
    }
    if (isFavorite("edam_operations", ontology.id)) {
        return `Remove EDAM operation '${ontology.name}' from Favorites`;
    }
    return `Add EDAM operation '${ontology.name}' to Favorites`;
}

function favoriteEdamTopicTitle(ontology: OntologyBadge) {
    if (isAnonymous.value) {
        return "Login or Register to Favorite EDAM Topics";
    }
    if (isFavorite("edam_topics", ontology.id)) {
        return `Remove EDAM topic '${ontology.name}' from Favorites`;
    }
    return `Add EDAM topic '${ontology.name}' to Favorites`;
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
                aria-label="Tool info"
                style="cursor: help">
                <FontAwesomeIcon :icon="faInfoCircle" fixed-width />
            </GButton>
            <GPopover
                v-if="props.version || !props.workflowCompatible"
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
            </GPopover>
        </template>

        <template v-slot:description>
            <div v-if="props.fetching && !props.help">
                <BSkeleton />
            </div>

            <div v-else-if="props.summary && !showHelp" v-sanitize-html="props.summary"></div>

            <div v-if="props.help" class="mt-2">
                <GLink
                    v-if="!showHelp"
                    data-description="tools list toggle tool help"
                    unselectable
                    @click="() => (showHelp = true)">
                    <FontAwesomeIcon :icon="faAngleDown" />
                    Show tool help
                </GLink>
                <GLink
                    v-else
                    data-description="tools list toggle tool help"
                    unselectable
                    @click="() => (showHelp = false)">
                    <FontAwesomeIcon :icon="faAngleUp" />
                    Hide tool help
                </GLink>

                <div v-if="showHelp" data-description="tools list tool help" class="mt-2">
                    <ToolHelp :content="props.help ?? ''" :format="props.helpFormat" />
                </div>
            </div>
        </template>

        <template v-slot:update-time>
            <div class="d-flex flex-gapx-1 flex-gapy-1 flex-wrap py-2">
                <span v-for="ontology in edamOperationsBadges" :key="ontology.id" class="tag toggle operation-tag">
                    <FontAwesomeIcon :icon="faSitemap" />
                    <GLink
                        thin
                        :title="ontology.id"
                        tooltip
                        @click="() => emit('apply-filter', 'ontology', quotedOntology(ontology))">
                        {{ ontology.name }}
                    </GLink>
                    <button
                        class="inline-ontology-button"
                        :class="{ disabled: isAnonymous }"
                        data-description="favorite-edam-operation-button"
                        :title="favoriteEdamOperationTitle(ontology)"
                        :aria-pressed="isFavorite('edam_operations', ontology.id) ? 'true' : 'false'"
                        :aria-disabled="isAnonymous ? 'true' : undefined"
                        :disabled="isSaving('edam_operations', ontology.id)"
                        @click.stop="toggleFavorite('edam_operations', ontology.id, ontology.name)">
                        <FontAwesomeIcon
                            :icon="isFavorite('edam_operations', ontology.id) ? fasStar : farStar"
                            fixed-width />
                    </button>
                </span>

                <span v-for="ontology in edamTopicsBadges" :key="ontology.id" class="tag toggle">
                    <FontAwesomeIcon :icon="faSitemap" />
                    <GLink
                        thin
                        :title="ontology.id"
                        tooltip
                        @click="() => emit('apply-filter', 'ontology', quotedOntology(ontology))">
                        {{ ontology.name }}
                    </GLink>
                    <button
                        class="inline-ontology-button"
                        :class="{ disabled: isAnonymous }"
                        data-description="favorite-edam-topic-button"
                        :title="favoriteEdamTopicTitle(ontology)"
                        :aria-pressed="isFavorite('edam_topics', ontology.id) ? 'true' : 'false'"
                        :aria-disabled="isAnonymous ? 'true' : undefined"
                        :disabled="isSaving('edam_topics', ontology.id)"
                        @click.stop="toggleFavorite('edam_topics', ontology.id, ontology.name)">
                        <FontAwesomeIcon
                            :icon="isFavorite('edam_topics', ontology.id) ? fasStar : farStar"
                            fixed-width />
                    </button>
                </span>

                <span v-for="tag in props.toolTags" :key="tag" class="tag curated-tag">
                    <FontAwesomeIcon :icon="faTag" />
                    <GLink thin :title="`Filter by tag ${tag}`" @click="() => emit('apply-filter', 'tag', tag)">
                        {{ tag }}
                    </GLink>
                    <button
                        class="inline-tag-button"
                        :class="{ disabled: isAnonymous }"
                        :title="favoriteTagTitle(tag)"
                        :aria-pressed="isFavorite('tags', tag) ? 'true' : 'false'"
                        :aria-disabled="isAnonymous ? 'true' : undefined"
                        :disabled="isSaving('tags', tag)"
                        @click.stop="toggleFavorite('tags', tag)">
                        <FontAwesomeIcon :icon="isFavorite('tags', tag) ? fasStar : farStar" fixed-width />
                    </button>
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

    .curated-tag {
        background-color: scale-color($brand-primary, $lightness: +78%);
        border-color: scale-color($brand-primary, $lightness: +58%);
    }

    .inline-tag-button {
        background: transparent;
        border: 0;
        color: inherit;
        cursor: pointer;
        margin-left: 0.125rem;
        padding: 0;

        &.disabled,
        &:disabled {
            cursor: not-allowed;
            opacity: 0.65;
        }
    }

    .inline-ontology-button {
        background: transparent;
        border: 0;
        color: inherit;
        cursor: pointer;
        margin-left: 0.125rem;
        padding: 0;

        &.disabled,
        &:disabled {
            cursor: not-allowed;
            opacity: 0.65;
        }
    }
}
</style>
