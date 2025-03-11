<script setup lang="ts">
import { faStar as farStar } from "@fortawesome/free-regular-svg-icons";
import { faCaretDown, faEdit, faPen, faSpinner, faStar } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBadge, BButton, BButtonGroup, BDropdown, BDropdownItem, BFormCheckbox, BLink } from "bootstrap-vue";
import { ref } from "vue";

import localize from "@/utils/localization";

import { type CardAttributes, type CardBadge, type Title } from "./GCard.types";

import Heading from "@/components/Common/Heading.vue";
import TextSummary from "@/components/Common/TextSummary.vue";
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";
import UtcDate from "@/components/UtcDate.vue";

interface Props {
    /** Unique identifier for the card */
    id: string;
    /** Title of the card, can be a string or an object with label, title, and handler */
    title: Title;
    /** Array of badges to display on the card */
    badges?: CardBadge[];
    /** Indicates if the card is bookmarked */
    bookmarked?: boolean;
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
    /** Array of badges to display next to the card title */
    titleBadges?: CardBadge[];
    /** Timestamp of the last update to the card */
    updateTime?: string;
    /** Tooltip title for the update time */
    updateTimeTitle?: string;
}

const props = withDefaults(defineProps<Props>(), {
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
    updateTime: "",
    updateTimeTitle: "",
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

const getElementId = (cardId: string, element: string) => `g-card-${cardId}-${element}`;
const getIndicatorId = (cardId: string, indicatorId: string) => `g-card-${cardId}-indicator-${indicatorId}`;
const getBadgeId = (cardId: string, badgeId: string) => `g-card-${cardId}-badge-${badgeId}`;
const getActionId = (cardId: string, actionId: string) => `g-card-${cardId}-action-${actionId}`;
</script>

<template>
    <!-- eslint-disable-next-line vuejs-accessibility/no-static-element-interactions vuejs-accessibility/click-events-have-key-events -->
    <div
        :id="`g-card-${props.id}`"
        class="g-card"
        :class="[
            { 'g-card-grid-view': gridView },
            { 'g-card-selected': selected },
            { 'g-card-current': current },
            { 'g-card-published': published },
            containerClass,
        ]"
        @click="emit('click')">
        <div :id="`g-card-content-${props.id}`" class="g-card-content" :class="contentClass">
            <slot>
                <div :id="`g-card-${props.id}-header`" class="g-card-header">
                    <div :id="`g-card-${props.id}-header-left`" class="g-card-header-left">
                        <slot name="select">
                            <BFormCheckbox
                                v-if="selectable"
                                :id="getElementId(props.id, 'select')"
                                v-b-tooltip.hover
                                :checked="selected"
                                class="g-card-select"
                                :title="props.selectTitle || localize('Select for bulk actions')"
                                @change="emit('select')" />
                        </slot>

                        <div :id="getElementId(props.id, 'indicators')" class="g-card-indicators">
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
                                        @click.stop="indicator.handler">
                                        <FontAwesomeIcon v-if="indicator.icon" :icon="indicator.icon" fixed-width />
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

                        <slot name="title">
                            <Heading :id="getElementId(props.id, 'title')" bold inline class="g-card-title" size="sm">
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

                    <div :id="getElementId(props.id, 'header-right')" class="g-card-header-right">
                        <div :id="getElementId(props.id, 'badges')" class="g-card-badges">
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

                            <BBadge
                                v-if="props.updateTime"
                                :id="`g-card-${props.id}-update-time`"
                                v-b-tooltip.hover.noninteractive
                                pill
                                variant="secondary"
                                :title="localize(props.updateTimeTitle)">
                                <FontAwesomeIcon :icon="faEdit" fixed-width />

                                <UtcDate :date="props.updateTime" mode="elapsed" />
                            </BBadge>
                        </div>

                        <slot v-if="props.showBookmark" name="bookmark">
                            <BButton
                                v-if="!bookmarkLoading"
                                :id="getElementId(props.id, 'bookmark')"
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
                                        @click="ea.handler && ea.handler()">
                                        <FontAwesomeIcon v-if="ea.icon" :icon="ea.icon" fixed-width />
                                        {{ localize(ea.label) }}
                                    </BDropdownItem>
                                </template>
                            </BDropdown>
                        </slot>
                    </div>
                </div>

                <div :id="getElementId(props.id, 'description')" class="g-card-description">
                    <slot name="description">
                        <TextSummary
                            v-if="props.description"
                            :id="getElementId(props.id, 'text-summary')"
                            :description="props.description"
                            :max-length="props.gridView ? 100 : 250" />
                    </slot>
                </div>

                <div :id="getElementId(props.id, 'footer')" class="g-card-footer">
                    <slot name="tags">
                        <StatelessTags
                            :id="getElementId(props.id, 'tags')"
                            class="my-1"
                            :clickable="props.tagsEditable"
                            :value="props.tags"
                            :disabled="!props.tagsEditable"
                            :max-visible-tags="props.maxVisibleTags"
                            @input="emit('tagsUpdate', $event)"
                            @tag-click="emit('tagClick', $event)" />
                    </slot>

                    <div :id="getElementId(props.id, 'actions')" class="g-card-actions">
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
                                        @click.stop="sa.handler">
                                        <FontAwesomeIcon
                                            v-if="sa.icon"
                                            :icon="sa.icon"
                                            fixed-width
                                            :size="sa.size || undefined" />
                                        {{ localize(sa.label) }}
                                    </BButton>
                                </template>
                            </BButtonGroup>
                        </slot>

                        <div :id="getElementId(props.id, 'primary-actions')" class="g-card-primary-actions">
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
            </slot>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";
@import "_breakpoints.scss";

.g-card {
    container: cards-list / inline-size;

    width: 100%;
    padding: 0 0.25rem 0.5rem 0.25rem;

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
        position: relative;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        border: 1px solid $brand-secondary;
        border-radius: 0.5rem;
        padding: 0.75rem;

        .g-card-header {
            display: grid;
            position: relative;
            align-items: start;
            grid-template-areas:
                "i d b"
                "n n n"
                "s s s";

            grid-template-columns: auto 1fr auto;

            .g-card-header-left {
                grid-area: i;
                display: flex;
                gap: 0.25rem;

                .g-card-select {
                    margin: 0%;
                }
            }

            .g-card-header-right {
                grid-area: b;
                display: flex;
                gap: 0.25rem;
                align-items: center;

                .g-card-badges {
                    display: flex;
                    gap: 0.25rem;
                }
            }
        }

        .g-card-footer {
            display: flex;
            justify-content: space-between;
            align-items: end;
            margin-top: 0.5rem;

            .g-card-actions {
                grid-area: b;
                display: flex;
                gap: 0.25rem;
                align-items: center;
                justify-content: end;

                .g-card-primary-actions {
                    display: flex;
                    gap: 0.25rem;
                }
            }
        }
    }
}
</style>
