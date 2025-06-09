<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faCheckCircle, faExclamationCircle } from "font-awesome-6";
import { computed } from "vue";

const props = defineProps<{
    title?: string;
    description?: string;
    state?: boolean;
    invalidFeedback?: string;
}>();

const stateClasses = computed(() => {
    return {
        valid: props.state === true,
        invalid: props.state === false,
    };
});
</script>

<template>
    <div class="g-form-label" :class="stateClasses">
        <label>
            <span v-if="props.title" class="label-text">
                {{ props.title }}
            </span>

            <div class="input">
                <slot></slot>
                <FontAwesomeIcon v-if="props.state === true" :icon="faCheckCircle" class="indicator valid" />
                <FontAwesomeIcon v-if="props.state === false" :icon="faExclamationCircle" class="indicator invalid" />
            </div>
        </label>

        <span v-if="props.invalidFeedback && props.state === false" class="feedback-invalid">
            {{ props.invalidFeedback }}
        </span>

        <span v-if="description" class="description">
            {{ props.description }}
        </span>
    </div>
</template>

<style scoped lang="scss">
.g-form-label {
    display: flex;
    flex-direction: column;

    label {
        // bootstrap override
        margin-bottom: 0;
    }

    .feedback-invalid {
        color: var(--color-red-600);
    }

    .description {
        color: var(--color-grey-300);
    }

    &.valid {
        :deep(input) {
            border-color: var(--color-green-500) !important;
        }
    }

    &.invalid {
        :deep(input) {
            border-color: var(--color-red-500) !important;
        }
    }

    .input {
        position: relative;
        display: flex;
        flex-direction: column;

        .indicator {
            position: absolute;
            right: var(--spacing-2);
            top: 50%;
            transform: translateY(-50%);

            &.valid {
                color: var(--color-green-500);
            }

            &.invalid {
                color: var(--color-red-500);
            }
        }
    }
}
</style>
