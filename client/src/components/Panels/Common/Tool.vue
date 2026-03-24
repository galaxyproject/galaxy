<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed } from "vue";

import type { Tool as ToolType } from "@/stores/toolStore";
import { useToolStore } from "@/stores/toolStore";
import { useUserStore } from "@/stores/userStore";
import ariaAlert from "@/utils/ariaAlert";

import ToolFavoriteButton from "@/components/Tool/Buttons/ToolFavoriteButton.vue";

interface Props {
    tool: ToolType;
    hideName?: boolean;
    showFavoriteButton?: boolean;
    showDragHandle?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    hideName: false,
    showFavoriteButton: false,
    showDragHandle: false,
});

const emit = defineEmits<{
    (e: "onClick", tool: ToolType, evt: MouseEvent): void;
}>();

const toolStore = useToolStore();
const userStore = useUserStore();
const { currentFavorites } = storeToRefs(userStore);

const isFavorite = computed(() => currentFavorites.value.tools?.includes(props.tool.id));

const toolLink = computed(() => toolStore.getLinkById(props.tool.id));
const toolTarget = computed(() => toolStore.getTargetById(props.tool.id));

function onClick(evt: MouseEvent) {
    ariaAlert(`${props.tool.name} selected from panel`);
    emit("onClick", props.tool, evt);
}
</script>

<template>
    <div class="toolTitle">
        <a
            v-if="props.tool.disabled"
            :class="['title-link', 'name', 'text-muted', 'tool-link', { 'favorite-top-level-drag-target': props.showDragHandle }]"
            :data-tool-id="props.tool.id"
            :data-description="props.showDragHandle ? 'favorite-top-level-drag-target' : null">
            <span v-if="!props.hideName">{{ props.tool.name }}</span>
            <span class="description">{{ props.tool.description }}</span>
        </a>
        <a
            v-else
            :class="['title-link', 'cursor-pointer', 'tool-link', { 'favorite-top-level-drag-target': props.showDragHandle }]"
            :data-tool-id="props.tool.id"
            :data-description="props.showDragHandle ? 'favorite-top-level-drag-target' : null"
            :href="toolLink"
            :target="toolTarget"
            :title="props.tool.help"
            @click="onClick">
            <span class="labels">
                <span
                    v-for="(label, index) in props.tool.labels"
                    :key="index"
                    :class="['badge', 'badge-primary', `badge-${label}`]">
                    {{ label }}
                </span>
            </span>
            <span v-if="!props.hideName" class="name font-weight-bold">{{ props.tool.name }}</span>
            <span class="description">{{ props.tool.description }}</span>
        </a>
        <div v-if="props.showFavoriteButton || isFavorite" class="toolTitleActions">
            <ToolFavoriteButton
                v-if="props.showFavoriteButton || isFavorite"
                :id="props.tool.id"
                :class="['tool-favorite-button', { 'tool-favorite-button-hover': isFavorite }]"
                :data-tool-id="props.tool.id"
                color="grey" />
        </div>
    </div>
</template>

<style scoped>
.toolTitle {
    display: flex;
    align-items: center;
    overflow-wrap: anywhere;
}
.tool-link {
    flex: 1 1 auto;
    min-width: 0;
}
.toolTitleActions {
    align-items: center;
    display: inline-flex;
    gap: 0.25rem;
    margin-left: auto;
}
.tool-favorite-button {
    margin-left: 0;
}
.tool-favorite-button-hover {
    opacity: 0;
    transition: opacity 0.2s ease;
    transition-delay: 0s;
    pointer-events: none;
}
.toolTitle:hover .tool-favorite-button-hover {
    opacity: 1;
    transition-delay: 0.5s;
    pointer-events: auto;
}
.toolTitle:focus-within .tool-favorite-button-hover {
    opacity: 1;
    transition-delay: 0s;
    pointer-events: auto;
}
.tool-favorite-button-hover:focus {
    opacity: 1;
    transition-delay: 0s;
    pointer-events: auto;
}
.favorite-top-level-drag-target {
    cursor: grab;
    user-select: none;
}
.favorite-top-level-drag-target:active {
    cursor: grabbing;
}
</style>
