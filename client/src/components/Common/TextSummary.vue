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
    /** If `true`, the description is HTML and should be rendered as such */
    isHtml?: boolean;
    /** If `true`, shows the full text */
    showExpandText?: boolean;
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
            <template v-if="props.isHtml">
                <div v-html="props.description" />
            </template>
            <template v-else>
                {{ props.description }}
            </template>
        </component>
        <template v-else-if="isHtml">
            <div v-html="text" />
        </template>
        <span v-else>{{ text }}</span>
        <span
            v-if="!noExpand && textTooLong"
            v-b-tooltip.hover
            class="text-summary-expand-button"
            :class="{ 'text-summary-expand-float': !props.showExpandText && props.isHtml }"
            :title="showDetails ? 'Show less' : 'Show more'"
            role="button"
            tabindex="0"
            @keyup.enter="showDetails = !showDetails"
            @click="showDetails = !showDetails">
            <template v-if="showExpandText">
                <template v-if="showDetails">Show less</template>
                <template v-else>Show more</template>
            </template>

            <FontAwesomeIcon :icon="showDetails ? 'chevron-up' : 'chevron-down'" />
        </span>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.one-line-summary {
    max-height: 2em;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.text-summary-expand-button {
    cursor: pointer;
    width: fit-content;
    float: right;
    color: $text-light;
    margin-left: auto;

    .text-summary-expand-float {
        position: absolute;
        right: 5px;
        bottom: 0;
    }
}
</style>
