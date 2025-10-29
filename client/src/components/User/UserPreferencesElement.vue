<script setup lang="ts">
import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import { useRouter } from "vue-router/composables";

import GCard from "@/components/Common/GCard.vue";

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
    <GCard
        :id="props.id"
        class="user-preference-element"
        :class="{ 'danger-zone': !!dangerZone }"
        :container-class="[dangerZone ? 'danger-zone' : '']"
        :title-icon="{ icon: props.icon }"
        :title="props.title"
        :description="props.description"
        full-description
        :to="props.to"
        clickable
        grid-view
        @click="onClick" />
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";

.user-preference-element {
    :deep(.g-card-content h1) {
        color: $brand-primary;
    }

    :deep(.g-card-content [id*="title-link"]) {
        color: $brand-primary;
    }
}

.danger-zone {
    :deep(.g-card-content) {
        border-color: $brand-danger;
    }

    :deep(.g-card-content h1) {
        color: $brand-danger;
    }

    :deep(.g-card-content [id*="title-link"]) {
        color: $brand-danger;
    }
}
</style>
