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
import { BPopover, BSkeleton } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import { useFormattedToolHelp } from "@/composables/formattedToolHelp";
import { useToolStore } from "@/stores/toolStore";
import { useUserStore } from "@/stores/userStore";
import ariaAlert from "@/utils/ariaAlert";

import type { CardBadge } from "../Common/GCard.types";
import { useToolsListCardActions } from "./useToolsListCardActions";

import GButton from "../BaseComponents/GButton.vue";
import GLink from "@/components/BaseComponents/GLink.vue";
import GCard from "../Common/GCard.vue";
import { useToast } from "@/composables/toast";

type OntologyBadge = {
    id: string;
    name: string;
};

interface Props {
    id: string;
    name: string;
    edamOperations: string[];
    edamTopics: string[];
    toolTags: string[];
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
    toolTags: () => [],
});

const emit = defineEmits<{
    (e: "apply-filter", filter: string, value: string): void;
}>();

const userStore = useUserStore();
const { currentFavorites, isAnonymous } = storeToRefs(userStore);
const Toast = useToast();
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
const showPopover = ref(false);

const formattedToolHelp = computed(() => {
    if (showHelp.value) {
        const { formattedContent } = useFormattedToolHelp(props.help);
        return formattedContent.value;
    } else {
        return "";
    }
});

/** We add double quotes to the ontology id filter as well since the backend Whoosh search
 * requires it for exact matches, and the `Filtering` class only does single quotes. */
function quotedOntology(ontology: OntologyBadge) {
    return `"${ontology.id}"`;
}

const favoriteTagSet = computed(() => new Set(currentFavorites.value.tags || []));
const favoriteEdamOperationSet = computed(() => new Set(currentFavorites.value.edam_operations || []));
const favoriteEdamTopicSet = computed(() => new Set(currentFavorites.value.edam_topics || []));
const togglingTags = ref<string[]>([]);
const togglingEdamOperations = ref<string[]>([]);
const togglingEdamTopics = ref<string[]>([]);

function isFavoriteTag(tag: string) {
    return favoriteTagSet.value.has(tag);
}

function isTogglingTag(tag: string) {
    return togglingTags.value.includes(tag);
}

function isFavoriteEdamOperation(operationId: string) {
    return favoriteEdamOperationSet.value.has(operationId);
}

function isTogglingEdamOperation(operationId: string) {
    return togglingEdamOperations.value.includes(operationId);
}

function isFavoriteEdamTopic(topicId: string) {
    return favoriteEdamTopicSet.value.has(topicId);
}

function isTogglingEdamTopic(topicId: string) {
    return togglingEdamTopics.value.includes(topicId);
}

function favoriteTagTitle(tag: string) {
    if (isAnonymous.value) {
        return "Login or Register to Favorite Tags";
    }
    if (isFavoriteTag(tag)) {
        return "Remove tag from Favorites";
    }
    return "Add tag to Favorites";
}

function favoriteEdamOperationTitle(ontology: OntologyBadge) {
    if (isAnonymous.value) {
        return "Login or Register to Favorite EDAM Operations";
    }
    if (isFavoriteEdamOperation(ontology.id)) {
        return `Remove EDAM operation '${ontology.name}' from Favorites`;
    }
    return `Add EDAM operation '${ontology.name}' to Favorites`;
}

function favoriteEdamTopicTitle(ontology: OntologyBadge) {
    if (isAnonymous.value) {
        return "Login or Register to Favorite EDAM Topics";
    }
    if (isFavoriteEdamTopic(ontology.id)) {
        return `Remove EDAM topic '${ontology.name}' from Favorites`;
    }
    return `Add EDAM topic '${ontology.name}' to Favorites`;
}

async function toggleFavoriteTag(tag: string) {
    if (isAnonymous.value) {
        Toast.error("You must be signed in to manage favorite tags.");
        ariaAlert("sign in to manage favorite tags");
        return;
    }

    if (isTogglingTag(tag)) {
        return;
    }

    togglingTags.value = [...togglingTags.value, tag];

    try {
        if (isFavoriteTag(tag)) {
            await userStore.removeFavoriteTag(tag);
            ariaAlert(`removed tag ${tag} from favorites`);
        } else {
            await userStore.addFavoriteTag(tag);
            ariaAlert(`added tag ${tag} to favorites`);
        }
    } catch {
        Toast.error(`Failed to update favorite tag '${tag}'.`);
        ariaAlert(`failed to update favorite tag ${tag}`);
    } finally {
        togglingTags.value = togglingTags.value.filter((activeTag) => activeTag !== tag);
    }
}

async function toggleFavoriteEdamOperation(ontology: OntologyBadge) {
    if (isAnonymous.value) {
        Toast.error("You must be signed in to manage favorite EDAM operations.");
        ariaAlert("sign in to manage favorite EDAM operations");
        return;
    }

    if (isTogglingEdamOperation(ontology.id)) {
        return;
    }

    togglingEdamOperations.value = [...togglingEdamOperations.value, ontology.id];

    try {
        if (isFavoriteEdamOperation(ontology.id)) {
            await userStore.removeFavoriteEdamOperation(ontology.id);
            ariaAlert(`removed EDAM operation ${ontology.name} from favorites`);
        } else {
            await userStore.addFavoriteEdamOperation(ontology.id);
            ariaAlert(`added EDAM operation ${ontology.name} to favorites`);
        }
    } catch {
        Toast.error(`Failed to update favorite EDAM operation '${ontology.name}'.`);
        ariaAlert(`failed to update favorite EDAM operation ${ontology.name}`);
    } finally {
        togglingEdamOperations.value = togglingEdamOperations.value.filter(
            (activeOperation) => activeOperation !== ontology.id,
        );
    }
}

async function toggleFavoriteEdamTopic(ontology: OntologyBadge) {
    if (isAnonymous.value) {
        Toast.error("You must be signed in to manage favorite EDAM topics.");
        ariaAlert("sign in to manage favorite EDAM topics");
        return;
    }

    if (isTogglingEdamTopic(ontology.id)) {
        return;
    }

    togglingEdamTopics.value = [...togglingEdamTopics.value, ontology.id];

    try {
        if (isFavoriteEdamTopic(ontology.id)) {
            await userStore.removeFavoriteEdamTopic(ontology.id);
            ariaAlert(`removed EDAM topic ${ontology.name} from favorites`);
        } else {
            await userStore.addFavoriteEdamTopic(ontology.id);
            ariaAlert(`added EDAM topic ${ontology.name} to favorites`);
        }
    } catch {
        Toast.error(`Failed to update favorite EDAM topic '${ontology.name}'.`);
        ariaAlert(`failed to update favorite EDAM topic ${ontology.name}`);
    } finally {
        togglingEdamTopics.value = togglingEdamTopics.value.filter((activeTopic) => activeTopic !== ontology.id);
    }
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
                        :aria-pressed="isFavoriteEdamOperation(ontology.id) ? 'true' : 'false'"
                        :aria-disabled="isAnonymous ? 'true' : undefined"
                        :disabled="isTogglingEdamOperation(ontology.id)"
                        @click.stop="toggleFavoriteEdamOperation(ontology)">
                        <FontAwesomeIcon :icon="isFavoriteEdamOperation(ontology.id) ? fasStar : farStar" fixed-width />
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
                        :aria-pressed="isFavoriteEdamTopic(ontology.id) ? 'true' : 'false'"
                        :aria-disabled="isAnonymous ? 'true' : undefined"
                        :disabled="isTogglingEdamTopic(ontology.id)"
                        @click.stop="toggleFavoriteEdamTopic(ontology)">
                        <FontAwesomeIcon :icon="isFavoriteEdamTopic(ontology.id) ? fasStar : farStar" fixed-width />
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
                        :aria-pressed="isFavoriteTag(tag) ? 'true' : 'false'"
                        :aria-disabled="isAnonymous ? 'true' : undefined"
                        :disabled="isTogglingTag(tag)"
                        @click.stop="toggleFavoriteTag(tag)">
                        <FontAwesomeIcon :icon="isFavoriteTag(tag) ? fasStar : farStar" fixed-width />
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
