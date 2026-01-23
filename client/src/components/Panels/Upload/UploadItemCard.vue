<script setup lang="ts">
import { computed } from "vue";

import GCard from "@/components/Common/GCard.vue";

interface Props {
    nested?: boolean;
    hasError?: boolean;
    badges?: any[];
    titleBadges?: any[];
    clickable?: boolean;
}

const props = defineProps<Props>();

defineEmits<{
    (e: "click", event: MouseEvent | KeyboardEvent): void;
}>();

const contentClasses = computed(() => {
    const classes: string[] = [];
    if (props.nested) {
        classes.push("nested");
    }
    if (props.hasError) {
        classes.push("has-error");
    }
    return classes;
});
</script>

<template>
    <GCard
        container-class=""
        :content-class="contentClasses"
        :badges="badges"
        :title-badges="titleBadges"
        :clickable="clickable"
        @click="$emit('click', $event)">
        <template v-slot:title>
            <slot name="title" />
        </template>

        <template v-slot:indicators>
            <slot name="indicators" />
        </template>

        <template v-slot:description>
            <slot name="description" />
        </template>
    </GCard>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";

:deep(.g-card-content.nested) {
    background-color: $white;
}

:deep(.g-card-content.has-error) {
    background-color: lighten($brand-danger, 48%);
    border-color: lighten($brand-danger, 30%);
}
</style>
