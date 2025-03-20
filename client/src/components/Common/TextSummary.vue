<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faChevronDown, faChevronUp } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref } from "vue";

library.add(faChevronUp, faChevronDown);

interface Props {
    /** The maximum length of the unexpanded text / summary */
    maxLength?: number;
    /** The text to summarize */
    description: string;
    /** If `true`, doesn't let unexpanded text go beyond height of one line
     * and ignores `maxLength` */
    oneLineSummary?: boolean;
    /** If `true`, doesn't show expand/collapse buttons */
    noExpand?: boolean;
    /** The component to use for the summary, default = `<p>` */
    component?: string;
}

const props = withDefaults(defineProps<Props>(), {
    maxLength: 150,
    component: "p",
});

const showDetails = ref(false);
const refOneLineSummary = ref<HTMLElement | null>(null);

const textTooLong = computed(() => {
    if (!props.oneLineSummary) {
        return props.description.length > props.maxLength;
    } else if (refOneLineSummary.value) {
        return refOneLineSummary.value.scrollWidth > refOneLineSummary.value.clientWidth;
    } else {
        return false;
    }
});
const text = computed(() =>
    textTooLong.value && !showDetails.value
        ? props.description.slice(0, Math.round(props.maxLength - props.maxLength / 2)) + "..."
        : props.description
);
</script>

<template>
    <div :class="{ 'd-flex': props.oneLineSummary && !noExpand }">
        <component
            :is="props.component"
            v-if="props.oneLineSummary"
            ref="refOneLineSummary"
            :class="{ 'one-line-summary': !showDetails }">
            {{ props.description }}
        </component>
        <span v-else>{{ text }}</span>
        <span
            v-if="!noExpand && textTooLong"
            v-b-tooltip.hover
            class="info-icon cursor-pointer"
            :title="showDetails ? 'Show less' : 'Show more'"
            role="button"
            tabindex="0"
            @keyup.enter="showDetails = !showDetails"
            @click="showDetails = !showDetails">
            <FontAwesomeIcon :icon="showDetails ? 'chevron-up' : 'chevron-down'" />
        </span>
    </div>
</template>

<style scoped>
.one-line-summary {
    max-height: 2em;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
</style>
