<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBadge } from "bootstrap-vue";
import type { IconDefinition } from "font-awesome-6";
import { useRouter } from "vue-router/composables";

interface Props {
    id: string;
    icon: IconDefinition;
    title: string;
    description: string;
    to?: string;
    badge?: string;
    dangerZone?: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "click"): void;
}>();

const router = useRouter();

function onClick() {
    if (props.to) {
        router.push(props.to);
    } else {
        emit("click");
    }
}
</script>

<template>
    <div class="user-preference-element" :class="{ 'danger-zone': !!dangerZone }" @click="onClick">
        <div class="user-preference-element-title">
            <FontAwesomeIcon :icon="props.icon" />

            <b v-localize>{{ title }}</b>

            <BBadge v-if="!!badge" variant="danger">
                {{ badge }}
            </BBadge>
        </div>

        <div>
            {{ description }}
        </div>

        <slot />
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";
@import "breakpoints.scss";

.user-preference-element {
    display: flex;
    cursor: pointer;
    gap: 0.5rem;
    flex-direction: column;
    border: 1px solid $brand-secondary;
    border-radius: 0.5rem;
    padding: 0.75rem;

    .user-preference-element-title {
        color: $brand-primary;
    }

    width: calc(100% / 3 - 1rem);

    @container user-preferences (max-width: #{$breakpoint-xl}) {
        width: calc(100% / 2 - 1rem);
    }

    @container user-preferences (max-width: #{$breakpoint-lg}) {
        width: 100%;
    }

    &:hover {
        background-color: $brand-secondary;
    }

    &.danger-zone {
        border-color: $brand-danger;

        .user-preference-element-title {
            color: $brand-danger;
        }
    }
}
</style>
