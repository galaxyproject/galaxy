<script setup lang="ts">
import { type IconDefinition } from "@fortawesome/fontawesome-svg-core";
import { faFile } from "@fortawesome/free-regular-svg-icons";
import { faDatabase, faFolder } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBadge, BFormCheckbox } from "bootstrap-vue";
import { computed } from "vue";

import { bytesToString } from "@/utils/utils";

import { SELECTION_STATES, type SelectionItem } from "./selectionTypes";

import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";

interface Props {
    item: SelectionItem;
    isEncoded?: boolean;
    leafSizeTitle?: string;
    parentSizeTitle?: string;
    showSelectIcon?: boolean;
    leafIcon?: IconDefinition;
    folderIcon?: IconDefinition;
}

const props = withDefaults(defineProps<Props>(), {
    isEncoded: false,
    leafSizeTitle: "Size of the file",
    parentSizeTitle: "Number of files",
    showSelectIcon: true,
    leafIcon: () => faFile,
    folderIcon: () => faFolder,
});

const emit = defineEmits<{
    (e: "open", item: SelectionItem): void;
    (e: "select", item: SelectionItem): void;
    (e: "update-filter", key: string, value: any): void;
}>();

const checked = computed(() => props.item._rowVariant === SELECTION_STATES.SELECTED);

function formatTime(value: Date | string) {
    if (value) {
        const date = new Date(value);

        return date.toLocaleString("default", {
            day: "numeric",
            month: "short",
            year: "numeric",
            minute: "numeric",
            hour: "numeric",
        });
    } else {
        return "-";
    }
}

function onSelect(item: SelectionItem) {
    emit("select", item);
}

function onOpen(item: SelectionItem) {
    if (!item.isLeaf) {
        emit("open", item);
    }
}
</script>

<template>
    <div :id="`selection-card-item-${props.item.id}`" class="selection-card-item">
        <div
            class="selection-card-container"
            :class="{
                'selection-card-selected': props.item._rowVariant === 'success',
            }">
            <div class="selection-card-control">
                <BFormCheckbox
                    v-if="props.showSelectIcon"
                    class="cursor-pointer align-self-end"
                    :checked="checked"
                    @change="onSelect(props.item)" />
            </div>

            <div class="selection-card-data" @click="onSelect(props.item)">
                <div class="selection-card-body">
                    <span>
                        <pre v-if="isEncoded" :title="`label-${props.item.url}`">
                                <code>{{ props.item.label }}</code>
                            </pre>
                        <span v-else-if="props.item.isLeaf">
                            <FontAwesomeIcon :icon="props.leafIcon" fixed-width size="sm" />
                            <span :title="`label-${props.item.url}`">
                                {{ props.item.label }}
                            </span>
                        </span>
                        <span v-else :title="`label-${props.item.url}`" @click="onOpen(props.item)">
                            <FontAwesomeIcon :icon="props.folderIcon" fixed-width size="sm" />

                            <span class="parent-title">
                                {{ props.item.label }}
                            </span>
                        </span>
                    </span>

                    <span v-if="props.item.update_time || props.item.time" class="selection-card-header-right">
                        <BBadge
                            v-if="!props.item.isLeaf"
                            v-b-tooltip.hover.noninteractive
                            :title="parentSizeTitle"
                            class="outline-badge cursor-pointer">
                            <FontAwesomeIcon :icon="faDatabase" fixed-width />
                            {{ props.item.size || 0 }}
                        </BBadge>

                        {{ formatTime(props.item.update_time ?? props.item.time) }}
                    </span>
                </div>

                <div class="selection-card-footer">
                    <StatelessTags
                        v-if="(props.item.tags ?? []).length > 0"
                        :value="props.item.tags"
                        :disabled="true" />

                    <div class="selection-card-description" :title="`details-${props.item.url}`">
                        {{ props.item.details }}
                    </div>

                    <BBadge
                        v-if="props.item.isLeaf"
                        v-b-tooltip.hover.noninteractive
                        :title="leafSizeTitle"
                        class="outline-badge cursor-pointer">
                        <FontAwesomeIcon :icon="faDatabase" fixed-width />
                        {{ bytesToString(props.item.size || 0) }}
                    </BBadge>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";
@import "breakpoints.scss";

.selection-card-selected {
    background-color: #abe3ab;
}

.selection-card-item {
    container: selection-card-item / inline-size;
    padding: 0;

    border-bottom: 0.1rem solid $brand-secondary;

    @container (max-width: #{$breakpoint-md}) {
        & {
            padding: 0 0.25rem 0.5rem 0.25rem;
        }
    }

    &.selection-card-selected {
        background-color: $brand-success;
    }

    &:hover {
        cursor: pointer;
        border-radius: 0.25rem;

        background-color: $brand-secondary;
    }

    .selection-card-container {
        height: 100%;
        display: flex;
        padding: 0.5rem;

        .selection-card-control {
            display: flex;
            gap: 0.4rem;
            flex-direction: column;
        }

        .selection-card-data {
            width: 100%;
            display: flex;
            flex-direction: column;
            justify-content: space-between;

            .selection-card-header {
                display: flex;
                justify-content: space-between;
            }

            .selection-card-body {
                display: flex;
                justify-content: space-between;

                .parent-title {
                    color: $brand-primary;

                    &:hover {
                        text-decoration: underline;
                    }
                }

                .selection-card-header-right {
                    display: flex;
                    gap: 0.25rem;
                    align-items: center;
                }
            }

            .selection-card-footer {
                display: flex;
                justify-content: space-between;
                align-items: end;
                padding-top: 0.25rem;
            }
        }
    }
}
</style>
