<script setup lang="ts">
import { faStar as farStar } from "@fortawesome/free-regular-svg-icons";
import { faCaretDown, faEdit, faPen, faSpinner, faStar, type IconDefinition } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBadge, BButton, BButtonGroup, BDropdown, BDropdownItem, BFormCheckbox, BLink } from "bootstrap-vue";
import { ref } from "vue";

import { useMarkdown } from "@/composables/markdown";
import { useUid } from "@/composables/utils/uid";
import localize from "@/utils/localization";

import { type CardAttributes, type CardBadge, type Title, type TitleIcon } from "./GCard.types";

import Heading from "@/components/Common/Heading.vue";
import TextSummary from "@/components/Common/TextSummary.vue";
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";
import UtcDate from "@/components/UtcDate.vue";

interface Props {
    /** Unique identifier for the card */
    id?: string;
    /** Array of badges to display on the card */
    badges?: CardBadge[];
    /** Indicates if the card is bookmarked */
    bookmarked?: boolean;
    /** Indicates if the card is clickable */
    clickable?: boolean;
    /** Additional CSS classes for the card container */
    containerClass?: string | string[];
    /** Additional CSS classes for the card content */
    contentClass?: string | string[];
    /** Indicates if the card is marked as current */
    current?: boolean;
    /** Description text for the card */
    description?: string;
    /** Array of extra actions available for the card */
    extraActions?: CardAttributes[];
    /** Indicates if the card is expanded to show full description */
    fullDescription?: boolean;
    /** Indicates if the card is displayed in grid view mode */
    gridView?: boolean;
    /** Array of indicators to display on the card */
    indicators?: CardAttributes[];
    /** Maximum number of visible tags */
    maxVisibleTags?: number;
    /** Array of primary actions available for the card */
    primaryActions?: CardAttributes[];
    /** Indicates if the card is published */
    published?: boolean;
    /** Title for the rename action */
    renameTitle?: string;
    /** Indicates if the card title is editable */
    canRenameTitle?: boolean;
    /** Array of secondary actions available for the card */
    secondaryActions?: CardAttributes[];
    /** Indicates if the card is selectable */
    selectable?: boolean;
    /** Indicates if the card is selected */
    selected?: boolean;
    /** Title for the card select checkbox */
    selectTitle?: string;
    /** Indicates if the bookmark button is displayed */
    showBookmark?: boolean;
    /** Array of tags associated with the card */
    tags?: string[];
    /** Indicates if the card tags are editable */
    tagsEditable?: boolean;
    /** Title of the card, can be a string or an object with label, title, and handler */
    title?: Title;
    /** Array of badges to display next to the card title */
    titleBadges?: CardBadge[];
    /** Icon to display before the card title */
    titleIcon?: TitleIcon;
    /** Size of the card title */
    titleSize?: "xl" | "lg" | "md" | "sm" | "text";
    /** Icon to display before the update time */
    updateTimeIcon?: IconDefinition;
    /** Timestamp of the last update to the card */
    updateTime?: string;
    /** Tooltip title for the update time */
    updateTimeTitle?: string;
}

const props = withDefaults(defineProps<Props>(), {
    id: () => useUid("g-card-").value,
    badges: () => [],
    containerClass: "",
    contentClass: "",
    current: false,
    description: "",
    extraActions: () => [],
    gridView: false,
    indicators: () => [],
    maxVisibleTags: 3,
    primaryActions: () => [],
    published: false,
    renameTitle: "Rename",
    canRenameTitle: false,
    secondaryActions: () => [],
    selectable: false,
    selected: false,
    selectTitle: "",
    tags: () => [],
    tagsEditable: false,
    title: "",
    titleBadges: () => [],
    titleIcon: undefined,
    titleSize: "sm",
    updateTime: "",
    updateTimeIcon: () => faEdit,
    updateTimeTitle: "Last updated",
});

const emit = defineEmits<{
    (e: "click"): void;
    (e: "bookmark"): void;
    (e: "dropdown", open: boolean): void;
    (e: "rename"): void;
    (e: "select"): void;
    (e: "titleClick"): void;
    (e: "tagClick", tag: string): void;
    (e: "tagsUpdate", tags: string[]): void;
}>();

const bookmarkLoading = ref(false);

async function toggleBookmark() {
    bookmarkLoading.value = true;
    await emit("bookmark");
    bookmarkLoading.value = false;
}

const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true });

const getElementId = (cardId: string, element: string) => `g-card-${element}-${cardId}`;
const getIndicatorId = (cardId: string, indicatorId: string) => `g-card-indicator-${indicatorId}-${cardId}`;
const getBadgeId = (cardId: string, badgeId: string) => `g-card-badge-${badgeId}-${cardId}`;
const getActionId = (cardId: string, actionId: string) => `g-card-action-${actionId}-${cardId}`;
</script>

<template>
    <component
        :is="'div'"
        :id="`g-card-${props.id}`"
        :role="props.clickable ? 'button' : undefined"
        class="g-card pt-0 px-1 pb-2"
        :class="[
            { 'g-card-grid-view': gridView },
            { 'g-card-selected': selected },
            { 'g-card-current': current },
            { 'g-card-published': published },
            containerClass,
        ]"
        :tabindex="props.clickable ? 0 : undefined"
        @click="props.clickable ? emit('click') : undefined"
        @keydown.enter="props.clickable ? emit('click') : undefined">
        <div
            :id="`g-card-content-${props.id}`"
            class="g-card-content d-flex flex-column justify-content-between h-100 p-2"
            :class="contentClass">
            <slot>
                <div class="d-flex flex-column flex-gapy-1">
                    <div
                        :id="`g-card-${props.id}-header`"
                        class="d-flex flex-gapy-1 flex-gapx-1 justify-content-between">
                        <div class="d-flex flex-column">
                            <div class="d-flex">
                                <div v-if="selectable">
                                    <slot name="select">
                                        <BFormCheckbox
                                            :id="getElementId(props.id, 'select')"
                                            v-b-tooltip.hover
                                            :checked="selected"
                                            :title="props.selectTitle || localize('Select for bulk actions')"
                                            @change="emit('select')" />
                                    </slot>
                                </div>

                                <div :id="`g-card-${props.id}-header-title`">
                                    <slot name="title">
                                        <Heading
                                            :id="getElementId(props.id, 'title')"
                                            bold
                                            inline
                                            class="d-inline"
                                            :size="props.titleSize">
                                            <FontAwesomeIcon
                                                v-if="props.titleIcon?.icon"
                                                :icon="props.titleIcon.icon"
                                                :class="props.titleIcon.class"
                                                :title="props.titleIcon.title"
                                                :size="props.titleIcon.size"
                                                fixed-width />

                                            <BLink
                                                v-if="typeof title === 'object'"
                                                :id="getElementId(props.id, 'title-link')"
                                                v-b-tooltip.hover
                                                :title="localize(title.title)"
                                                @click.stop.prevent="title.handler">
                                                {{ title.label }}
                                            </BLink>
                                            <template v-else>
                                                <span :id="getElementId(props.id, 'title-text')">{{ title }}</span>
                                            </template>

                                            <slot name="titleActions">
                                                <BButton
                                                    v-if="props.canRenameTitle"
                                                    :id="getElementId(props.id, 'rename')"
                                                    v-b-tooltip.hover.noninteractive
                                                    class="inline-icon-button g-card-rename"
                                                    variant="link"
                                                    :title="localize(props.renameTitle)"
                                                    @click="emit('rename')">
                                                    <FontAwesomeIcon :icon="faPen" fixed-width />
                                                </BButton>
                                            </slot>
                                        </Heading>
                                    </slot>
                                </div>
                            </div>

                            <div class="align-items-center d-flex flex-gapx-1">
                                <slot name="titleBadges">
                                    <template v-for="badge in props.titleBadges">
                                        <BBadge
                                            v-if="badge.visible"
                                            :id="getBadgeId(props.id, badge.id)"
                                            :key="badge.id"
                                            v-b-tooltip.hover
                                            :pill="badge.type !== 'badge'"
                                            class="mt-1"
                                            :class="{
                                                'outline-badge': badge.variant?.includes('outline'),
                                                'cursor-pointer': badge.handler,
                                                [String(badge.class)]: badge.class,
                                            }"
                                            :title="localize(badge.title)"
                                            :variant="badge.variant || 'secondary'"
                                            :to="badge.to"
                                            @click.stop="badge.handler">
                                            <FontAwesomeIcon v-if="badge.icon" :icon="badge.icon" fixed-width />
                                            {{ localize(badge.label) }}
                                        </BBadge>
                                    </template>
                                </slot>
                            </div>
                        </div>

                        <div class="align-items-start d-flex flex-row-reverse flex-wrap gap-1">
                            <div>
                                <slot v-if="props.showBookmark" name="bookmark">
                                    <BButton
                                        v-if="!bookmarkLoading"
                                        :id="
                                            getElementId(
                                                props.id,
                                                props.bookmarked ? 'bookmark-remove' : 'bookmark-add'
                                            )
                                        "
                                        v-b-tooltip.hover
                                        class="inline-icon-button"
                                        variant="link"
                                        :title="props.bookmarked ? 'Remove bookmark' : 'Add to bookmarks'"
                                        @click="toggleBookmark">
                                        <FontAwesomeIcon :icon="props.bookmarked ? faStar : farStar" fixed-width />
                                    </BButton>
                                    <BButton
                                        v-else
                                        :id="getElementId(props.id, 'bookmark-loading')"
                                        v-b-tooltip.hover
                                        class="inline-icon-button"
                                        variant="link"
                                        :title="localize('Bookmarking...')"
                                        disabled>
                                        <FontAwesomeIcon :icon="faSpinner" spin fixed-width />
                                    </BButton>
                                </slot>

                                <slot name="extra-actions">
                                    <BDropdown
                                        v-if="props.extraActions?.length && props.extraActions.some((ea) => ea.visible)"
                                        :id="getElementId(props.id, 'extra-actions')"
                                        v-b-tooltip.hover.noninteractive
                                        right
                                        no-caret
                                        title="More options"
                                        toggle-class="inline-icon-button"
                                        variant="link"
                                        @show="() => emit('dropdown', true)"
                                        @hide="() => emit('dropdown', false)">
                                        <template v-slot:button-content>
                                            <FontAwesomeIcon :icon="faCaretDown" fixed-width />
                                        </template>

                                        <template v-for="ea in props.extraActions">
                                            <BDropdownItem
                                                v-if="ea.visible"
                                                :id="getActionId(props.id, ea.id)"
                                                :key="ea.id"
                                                :disabled="ea.disabled"
                                                :variant="ea.variant || 'link'"
                                                :to="ea.to"
                                                :href="ea.href"
                                                :title="ea.title"
                                                :size="ea.size || 'sm'"
                                                :target="ea.externalLink ? '_blank' : undefined"
                                                @click="ea.handler && ea.handler()">
                                                <FontAwesomeIcon v-if="ea.icon" :icon="ea.icon" fixed-width />
                                                {{ localize(ea.label) }}
                                            </BDropdownItem>
                                        </template>
                                    </BDropdown>
                                </slot>
                            </div>

                            <div class="d-flex flex-gapx-1" style="margin-top: 1px">
                                <div
                                    :id="getElementId(props.id, 'badges')"
                                    class="align-items-center align-self-baseline d-flex flex-gapx-1">
                                    <slot name="badges">
                                        <template v-for="badge in props.badges">
                                            <BBadge
                                                v-if="badge.visible"
                                                :id="getBadgeId(props.id, badge.id)"
                                                :key="badge.id"
                                                v-b-tooltip.hover.top.noninteractive
                                                :pill="badge.type !== 'badge'"
                                                :class="{
                                                    'outline-badge': badge.variant?.includes('outline'),
                                                    'cursor-pointer': badge.handler,
                                                    [String(badge.class)]: badge.class,
                                                }"
                                                :title="localize(badge.title)"
                                                :variant="badge.variant || 'secondary'"
                                                :to="badge.to"
                                                @click.stop="badge.handler">
                                                <FontAwesomeIcon v-if="badge.icon" :icon="badge.icon" fixed-width />
                                                {{ localize(badge.label) }}
                                            </BBadge>
                                        </template>
                                    </slot>
                                </div>

                                <div :id="getElementId(props.id, 'indicators')">
                                    <slot name="indicators">
                                        <template v-for="indicator in props.indicators">
                                            <BButton
                                                v-if="indicator.visible && !indicator.disabled"
                                                :id="getIndicatorId(props.id, indicator.id)"
                                                :key="indicator.id"
                                                v-b-tooltip.hover
                                                class="inline-icon-button"
                                                :title="localize(indicator.title)"
                                                :variant="indicator.variant || 'outline-secondary'"
                                                :size="indicator.size || 'sm'"
                                                :to="indicator.to"
                                                :href="indicator.href"
                                                :disabled="indicator.disabled"
                                                :target="indicator.externalLink ? '_blank' : undefined"
                                                @click.stop="indicator.handler">
                                                <FontAwesomeIcon
                                                    v-if="indicator.icon"
                                                    :icon="indicator.icon"
                                                    fixed-width />
                                                {{ localize(indicator.label) }}
                                            </BButton>
                                            <FontAwesomeIcon
                                                v-else-if="indicator.visible && indicator.disabled"
                                                :id="getIndicatorId(props.id, indicator.id)"
                                                :key="indicator.id"
                                                v-b-tooltip.hover
                                                :title="localize(indicator.title)"
                                                :icon="indicator.icon"
                                                :size="indicator.size || 'sm'"
                                                fixed-width />
                                        </template>
                                    </slot>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div :id="getElementId(props.id, 'description')">
                        <slot name="description">
                            <TextSummary
                                v-if="props.description && !props.fullDescription"
                                :id="getElementId(props.id, 'text-summary')"
                                :description="props.description" />
                            <div
                                v-else-if="props.description && props.fullDescription"
                                class="mb-2"
                                v-html="renderMarkdown(props.description)" />
                        </slot>
                    </div>
                </div>

                <div
                    :id="getElementId(props.id, 'footer')"
                    class="align-items-end align-items-sm-stretch d-flex flex-sm-column justify-content-between">
                    <slot name="tags">
                        <StatelessTags
                            :id="getElementId(props.id, 'tags')"
                            inline
                            :clickable="props.tagsEditable"
                            :value="props.tags"
                            :disabled="!props.tagsEditable"
                            :max-visible-tags="props.maxVisibleTags"
                            @input="emit('tagsUpdate', $event)"
                            @tag-click="emit('tagClick', $event)" />
                    </slot>

                    <div
                        :id="getElementId(props.id, 'footer-update-time-actions')"
                        class="align-items-center d-flex flex-gapy-1 flex-sm-wrap justify-content-between">
                        <slot name="update-time">
                            <div
                                v-if="props.updateTime"
                                :id="`g-card-${props.id}-update-time`"
                                class="align-self-end mt-1">
                                <BBadge
                                    v-b-tooltip.hover.noninteractive
                                    pill
                                    variant="secondary"
                                    :title="localize(props.updateTimeTitle)">
                                    <FontAwesomeIcon :icon="props.updateTimeIcon" fixed-width />

                                    <UtcDate :date="props.updateTime" mode="elapsed" />
                                </BBadge>
                            </div>
                        </slot>

                        <div class="align-items-center d-flex flex-gapx-1 justify-content-end ml-auto mt-1">
                            <slot name="secondary-actions">
                                <BButtonGroup :id="getElementId(props.id, 'secondary-actions')" size="sm">
                                    <template v-for="sa in props.secondaryActions">
                                        <BButton
                                            v-if="sa.visible"
                                            :id="getActionId(props.id, sa.id)"
                                            :key="sa.id"
                                            v-b-tooltip.hover
                                            :disabled="sa.disabled"
                                            :title="localize(sa.title)"
                                            :variant="sa.variant || 'outline-primary'"
                                            :size="sa.size || 'sm'"
                                            :to="sa.to"
                                            :href="sa.href"
                                            :target="sa.externalLink ? '_blank' : undefined"
                                            @click.stop="sa.handler">
                                            <FontAwesomeIcon
                                                v-if="sa.icon"
                                                :icon="sa.icon"
                                                fixed-width
                                                :size="sa.size || undefined" />
                                            <span class="g-card-secondary-action-label">
                                                {{ localize(sa.label) }}
                                            </span>
                                        </BButton>
                                    </template>
                                </BButtonGroup>
                            </slot>

                            <div :id="getElementId(props.id, 'primary-actions')" class="d-flex flex-gapx-1">
                                <slot name="primary-actions">
                                    <template v-for="pa in props.primaryActions">
                                        <BButton
                                            v-if="pa.visible"
                                            :id="getActionId(props.id, pa.id)"
                                            :key="pa.id"
                                            v-b-tooltip.hover
                                            :disabled="pa.disabled"
                                            :title="localize(pa.title)"
                                            :variant="pa.variant || 'primary'"
                                            :size="pa.size || 'sm'"
                                            :to="pa.to"
                                            :href="pa.href"
                                            :class="{
                                                'inline-icon-button': pa.inline,
                                            }"
                                            @click.stop="pa.handler">
                                            <FontAwesomeIcon
                                                v-if="pa.icon"
                                                :icon="pa.icon"
                                                :size="pa.size || undefined"
                                                fixed-width />
                                            {{ localize(pa.label) }}
                                        </BButton>
                                    </template>
                                </slot>
                            </div>
                        </div>
                    </div>
                </div>
            </slot>
        </div>
    </component>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";
@import "_breakpoints.scss";

.g-card {
    container: g-card / inline-size;
    width: 100%;

    &.g-card-grid-view {
        width: calc(100% / 3);

        @container cards-list (max-width: #{$breakpoint-xl}) {
            width: calc(100% / 2);
        }

        @container cards-list (max-width: #{$breakpoint-sm}) {
            width: 100%;
        }
    }

    &.g-card-selected .g-card-content {
        background-color: $brand-light;
        border-color: $brand-primary;
    }

    &.g-card-current .g-card-content {
        background-color: $brand-light;
        border-width: 2px;
        border-color: $brand-primary;
        border-left: 0.25rem solid $brand-primary;
    }

    &.g-card-published .g-card-content {
        border-left: 0.25rem solid $brand-primary;
    }

    .g-card-rename {
        visibility: hidden;
    }

    &:hover,
    &:focus-within {
        .g-card-rename {
            visibility: visible;
        }
    }

    .g-card-content {
        background-color: $body-bg;
        border: 1px solid $brand-secondary;
        border-radius: 0.5rem;

        .g-card-secondary-action-label {
            @container g-card (max-width: #{$breakpoint-sm}) {
                display: none;
            }
        }
    }

    &:focus {
        outline: none;

        .g-card-content {
            border-color: $brand-primary;
            box-shadow: 0 0 0 0.5px;
            background-color: lighten($brand-light, 0.5);
        }
    }
}
</style>
