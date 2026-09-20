<template>
    <div class="clarification-card">
        <div class="clarification-question">{{ question }}</div>
        <div v-if="options.length > 0" class="clarification-options">
            <GButton
                v-for="(option, index) in options"
                :key="`${index}-${option}`"
                outline
                size="small"
                color="blue"
                @click="$emit('select-option', option)">
                {{ option }}
            </GButton>
        </div>
    </div>
</template>

<script setup lang="ts">
import GButton from "@/components/BaseComponents/GButton.vue";

withDefaults(
    defineProps<{
        question: string;
        options?: string[];
    }>(),
    {
        options: () => [],
    },
);

defineEmits<{
    "select-option": [option: string];
}>();
</script>

<style lang="scss" scoped>
@import "@/style/scss/theme/blue.scss";

.clarification-question {
    margin-bottom: 0.5rem;
}

.clarification-options {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
}
</style>
