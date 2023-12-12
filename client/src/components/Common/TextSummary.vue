<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faChevronDown, faChevronUp } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref } from "vue";

library.add(faChevronUp, faChevronDown);

interface Props {
    maxLength?: number;
    description: string;
}

const props = withDefaults(defineProps<Props>(), {
    maxLength: 150,
});

const showDetails = ref(false);

const textTooLong = computed(() => props.description.length > props.maxLength);
const text = computed(() =>
    textTooLong.value && !showDetails.value
        ? props.description.slice(0, Math.round(props.maxLength - props.maxLength / 2)) + "..."
        : props.description
);
</script>

<template>
    <div>
        {{ text }}
        <span
            v-if="textTooLong"
            v-b-tooltip.hover
            class="info-icon cursor-pointer"
            :title="textTooLong ? 'Show more' : 'Show less'"
            @click="showDetails = !showDetails">
            <FontAwesomeIcon :icon="showDetails ? 'chevron-up' : 'chevron-down'" />
        </span>
    </div>
</template>
