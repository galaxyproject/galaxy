<script setup lang="ts">
import type { IconDefinition } from "@fortawesome/free-solid-svg-icons";
import { faChevronLeft, faHome } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import ActivityBarSeparator from "./ActivityBarSeparator.vue";

interface Props {
    /** Whether an activity's side panel is currently open. */
    isSideBarOpen: boolean;
    /** The icon to display in the header. */
    icon?: IconDefinition;
    /** The title to display in the header. */
    title?: string;
}
const props = withDefaults(defineProps<Props>(), {
    icon: () => faHome,
    title: "Activities",
});

const emit = defineEmits<{
    (e: "close-sidebar"): void;
}>();

function closeSidebar(event: KeyboardEvent | MouseEvent) {
    if (props.isSideBarOpen && (event instanceof MouseEvent || event.key === "Enter" || event.key === " ")) {
        emit("close-sidebar");
    }
}
</script>

<template>
    <div>
        <!-- eslint-disable-next-line vuejs-accessibility/no-static-element-interactions -->
        <div
            class="rounded activity-bar-header-badge"
            :class="{ 'sidebar-opened': props.isSideBarOpen }"
            data-description="activity bar header"
            :role="props.isSideBarOpen ? 'button' : undefined"
            :tabindex="props.isSideBarOpen ? 0 : undefined"
            :title="props.isSideBarOpen ? 'Close panel' : 'Activity Bar'"
            @click="closeSidebar"
            @keydown="closeSidebar">
            <FontAwesomeIcon :icon="props.isSideBarOpen ? faChevronLeft : props.icon" size="sm" fixed-width />
            <span class="activity-bar-header-text">{{ props.title }}</span>
        </div>
        <ActivityBarSeparator />
    </div>
</template>

<style scoped lang="scss">
.activity-bar-header-badge {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--spacing);
    margin: var(--spacing-1);
    padding: var(--spacing-1) 0;
    color: var(--color-blue-600);

    &.sidebar-opened {
        background: var(--color-grey-200);
        &:hover {
            color: var(--color-blue-700);
        }
    }

    .activity-bar-header-text {
        font-size: var(--font-size-small);
    }
}
</style>
