<script setup lang="ts">
import { faStar as farStar } from "@fortawesome/free-regular-svg-icons";
import { faCaretDown, faEdit, faPen, faSpinner, faStar, type IconDefinition } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBadge, BButton, BButtonGroup, BDropdown, BDropdownItem, BFormCheckbox, BLink } from "bootstrap-vue";
import { computed, ref } from "vue";

import { useMarkdown } from "@/composables/markdown";
import { useUid } from "@/composables/utils/uid";
import localize from "@/utils/localization";

import type { CardAction, CardBadge, CardIndicator, Title, TitleIcon, TitleSize } from "./GCard.types";

import Heading from "@/components/Common/Heading.vue";
import TextSummary from "@/components/Common/TextSummary.vue";
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";
import UtcDate from "@/components/UtcDate.vue";

interface Props {
    /** Unique identifier for the card
     * @default useUid("g-card-").value
     */
    id?: string;

    /** Badges displayed in the top-right corner
     * @default []
     */
    badges?: CardBadge[];

    /** Whether the card is bookmarked
     * @default undefined
     */
    bookmarked?: boolean;

    /** Whether the card is clickable (emits click events)
     * @default undefined
     */
    clickable?: boolean;

    /** Additional CSS classes for the card container
     * @default ""
     */
    containerClass?: string | string[];

    /** Additional CSS classes for the card content
     * @default ""
     */
    contentClass?: string | string[];

    /** Whether the card is marked as current/active
     * @default false
     */
    current?: boolean;

    /** Description text (supports Markdown)
     * @default ""
     */
    description?: string;

    /** Extra actions shown in dropdown menu
     * @default []
     */
    extraActions?: CardAction[];

    /** Whether to show full description (no truncation)
     * @default undefined
     */
    fullDescription?: boolean;

    /** Whether displayed in grid view mode
     * @default false
     */
    gridView?: boolean;

    /** Indicators shown as small buttons/icons
     * @default []
     */
    indicators?: CardIndicator[];

    /** Max visible tags before "show more"
     * @default 3
     */
    maxVisibleTags?: number;

    /** Primary actions in card footer
     * @default []
     */
    primaryActions?: CardAction[];

    /** Whether the card represents published content
     * @default false
     */
    published?: boolean;

    /** Tooltip text for rename button
     * @default "Rename"
     */
    renameTitle?: string;

    /** Whether the card title is editable
     * @default false
     */
    canRenameTitle?: boolean;

    /** Secondary actions in card footer
     * @default []
     */
    secondaryActions?: CardAction[];

    /** Whether the card is selectable via checkbox
     * @default false
     */
    selectable?: boolean;

    /** Whether the card is currently selected
     * @default false
     */
    selected?: boolean;

    /** Tooltip text for select checkbox
     * @default ""
     */
    selectTitle?: string;

    /** Whether to show bookmark button
     * @default undefined
     */
    showBookmark?: boolean;

    /** Tags displayed in card footer
     * @default []
     */
    tags?: string[];

    /** Whether tags are editable/clickable
     * @default false
     */
    tagsEditable?: boolean;

    /** Card title (string or interactive object)
     * @default ""
     */
    title?: Title;

    /** Badges displayed next to title
     * @default []
     */
    titleBadges?: CardBadge[];

    /** Icon displayed before title
     * @default undefined
     */
    titleIcon?: TitleIcon;

    /** Whether the title should be truncated to a certain number of lines
     * @default undefined
     */
    titleNLines?: number;

    /** Size of the card title
     * @default "sm"
     */
    titleSize?: TitleSize;

    /** Icon for update time badge
     * @default faEdit
     */
    updateTimeIcon?: IconDefinition;

    /** Last update timestamp
     * @default ""
     */
    updateTime?: string;

    /** Tooltip for update time badge
     * @default "Last updated"
     */
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
    titleNLines: undefined,
    titleSize: "sm",
    updateTime: "",
    updateTimeIcon: () => faEdit,
    updateTimeTitle: "Last updated",
});

/**
 * Events emitted by the GCard component
 */
const emit = defineEmits<{
    /** Emitted when card is clicked
     * @event click
     */
    (e: "click", event: MouseEvent | KeyboardEvent): void;

    /** Emitted when bookmark button is clicked
     * @event bookmark
     */
    (e: "bookmark"): Promise<void>;

    /** Emitted when dropdown opens/closes
     * @event dropdown
     */
    (e: "dropdown", open: boolean): void;

    /** Emitted when rename button is clicked
     * @event rename
     */
    (e: "rename"): void;

    /** Emitted when selection checkbox is toggled
     * @event select
     */
    (e: "select"): void;

    /** Emitted when title is clicked
     * @event titleClick
     */
    (e: "titleClick"): void;

    /** Emitted when tag is clicked
     * @event tagClick
     */
    (e: "tagClick", tag: string): void;

    /** Emitted when tags are updated
     * @event tagsUpdate
     */
    (e: "tagsUpdate", tags: string[]): void;
    (e: "keydown", event: KeyboardEvent): void;
}>();

const bookmarkLoading = ref(false);

/**
 * Toggles bookmark status with loading state
 */
async function toggleBookmark() {
    bookmarkLoading.value = true;
    await emit("bookmark");
    bookmarkLoading.value = false;
}

const { renderMarkdown } = useMarkdown({ noMargin: true, openLinksInNewPage: true });

/**
 * Helper functions for generating consistent element IDs
 */
const getElementId = (cardId: string, element: string) => `g-card-${element}-${cardId}`;
const getIndicatorId = (cardId: string, indicatorId: string) => `g-card-indicator-${indicatorId}-${cardId}`;
const getBadgeId = (cardId: string, badgeId: string) => `g-card-badge-${badgeId}-${cardId}`;
const getActionId = (cardId: string, actionId: string) => `g-card-action-${actionId}-${cardId}`;

/**
 * Number of lines before title truncation (undefined = no truncation)
 */
const allowedTitleLines = computed(() => props.titleNLines);

function onKeyDown(event: KeyboardEvent) {
    if ((props.clickable && event.key === "Enter") || event.key === " ") {
        emit("click", event);
    } else if (props.clickable) {
        emit("keydown", event);
    }
}
</script>

<template>
    <component
        :is="'div'"
        :id="`g-card-${props.id}`"
        :role="props.clickable ? 'button' : undefined"
        class="g-card pt-0 px-1 mb-2"
        :class="[
            { 'g-card-grid-view': gridView },
            { 'g-card-selected': selected },
            { 'g-card-current': current },
            { 'g-card-published': published },
            { 'g-card-clickable': props.clickable },
            containerClass,
        ]"
        :tabindex="props.clickable ? 0 : undefined"
        @click="props.clickable ? emit('click', $event) : undefined"
        @keydown="onKeyDown">
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
                                            v-b-tooltip.hover.noninteractive
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
                                            :size="props.titleSize">
                                            <div class="d-flex">
                                                <FontAwesomeIcon
                                                    v-if="props.titleIcon?.icon"
                                                    class="mr-1"
                                                    :class="props.titleIcon.class"
                                                    :icon="props.titleIcon.icon"
                                                    :title="props.titleIcon.title"
                                                    :size="props.titleIcon.size"
                                                    fixed-width />
                                                <BLink
                                                    v-if="typeof title === 'object'"
                                                    :id="getElementId(props.id, 'title-link')"
                                                    v-b-tooltip.hover.noninteractive
                                                    :title="localize(title.title)"
                                                    :class="{ 'g-card-title-truncate': props.titleNLines }"
                                                    @click.stop.prevent="title.handler">
                                                    {{ title.label }}
                                                </BLink>
                                                <template v-else>
                                                    <span
                                                        :id="getElementId(props.id, 'title-text')"
                                                        v-b-tooltip.hover.noninteractive
                                                        :title="localize(title)"
                                                        :class="{ 'g-card-title-truncate': props.titleNLines }">
                                                        {{ title }}
                                                    </span>
                                                </template>
                                            </div>

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
                                            v-if="badge.visible ?? true"
                                            :id="getBadgeId(props.id, badge.id)"
                                            :key="badge.id"
                                            v-b-tooltip.hover.noninteractive
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
                                                props.bookmarked ? 'bookmark-remove' : 'bookmark-add',
                                            )
                                        "
                                        v-b-tooltip.hover.noninteractive
                                        class="inline-icon-button"
                                        variant="link"
                                        :title="props.bookmarked ? 'Remove bookmark' : 'Add to bookmarks'"
                                        @click="toggleBookmark">
                                        <FontAwesomeIcon :icon="props.bookmarked ? faStar : farStar" fixed-width />
                                    </BButton>
                                    <BButton
                                        v-else
                                        :id="getElementId(props.id, 'bookmark-loading')"
                                        v-b-tooltip.hover.noninteractive
                                        class="inline-icon-button"
                                        variant="link"
                                        :title="localize('Bookmarking...')"
                                        disabled>
                                        <FontAwesomeIcon :icon="faSpinner" spin fixed-width />
                                    </BButton>
                                </slot>

                                <slot name="extra-actions">
                                    <BDropdown
                                        v-if="
                                            props.extraActions?.length &&
                                            props.extraActions.some((ea) => ea.visible ?? true)
                                        "
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
                                                v-if="ea.visible ?? true"
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
                                                v-if="badge.visible ?? true"
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
                                                :href="badge.href"
                                                @click.stop="badge.handler">
                                                <FontAwesomeIcon
                                                    v-if="badge.icon"
                                                    :icon="badge.icon"
                                                    fixed-width
                                                    :spin="badge.spin" />
                                                {{ localize(badge.label) }}
                                            </BBadge>
                                        </template>
                                    </slot>
                                </div>

                                <div :id="getElementId(props.id, 'indicators')" class="align-self-baseline">
                                    <slot name="indicators">
                                        <template v-for="indicator in props.indicators">
                                            <BButton
                                                v-if="(indicator.visible ?? true) && !indicator.disabled"
                                                :id="getIndicatorId(props.id, indicator.id)"
                                                :key="`${indicator.id}-button`"
                                                v-b-tooltip.hover.noninteractive
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
                                                v-else-if="(indicator.visible ?? true) && indicator.disabled"
                                                :id="getIndicatorId(props.id, indicator.id)"
                                                :key="`${indicator.id}-icon`"
                                                v-b-tooltip.hover.noninteractive
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

                    <div :id="getElementId(props.id, 'description')" class="g-card-description">
                        <slot name="description">
                            <template v-if="props.description">
                                <TextSummary
                                    v-if="!props.fullDescription"
                                    :id="getElementId(props.id, 'text-summary')"
                                    :description="props.description" />
                                <div v-else v-html="renderMarkdown(props.description)" />
                            </template>
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

                        <div class="align-items-center d-flex flex-gapx-1 justify-content-end ml-auto">
                            <slot name="secondary-actions">
                                <BButtonGroup
                                    v-if="props.secondaryActions?.length"
                                    :id="getElementId(props.id, 'secondary-actions')"
                                    size="sm"
                                    class="mt-1">
                                    <template v-for="sa in props.secondaryActions">
                                        <BButton
                                            v-if="sa.visible ?? true"
                                            :id="getActionId(props.id, sa.id)"
                                            :key="sa.id"
                                            v-b-tooltip.hover.noninteractive
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
                                    <template v-if="props.primaryActions?.length">
                                        <template v-for="pa in props.primaryActions">
                                            <BButton
                                                v-if="pa.visible ?? true"
                                                :id="getActionId(props.id, pa.id)"
                                                :key="pa.id"
                                                v-b-tooltip.hover.noninteractive
                                                class="mt-1"
                                                :disabled="pa.disabled"
                                                :title="localize(pa.title)"
                                                :variant="pa.variant || 'primary'"
                                                :size="pa.size || 'sm'"
                                                :to="pa.to"
                                                :href="pa.href"
                                                :class="{
                                                    'inline-icon-button': pa.inline,
                                                    [String(pa.class)]: pa.class,
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

    &.g-card-clickable {
        cursor: pointer;

        &:hover,
        &:focus-within {
            .g-card-content {
                border-color: $brand-secondary;
                box-shadow: 0 0 0 0.5px;
                background-color: lighten($brand-light, 0.5);
            }
        }
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

        .g-card-title-truncate {
            display: -webkit-box;
            -webkit-box-orient: vertical;
            -webkit-line-clamp: v-bind(allowedTitleLines);
            line-clamp: v-bind(allowedTitleLines);
            overflow: hidden;
            line-height: 1.2;
            white-space: normal;
            text-overflow: unset;
        }

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
