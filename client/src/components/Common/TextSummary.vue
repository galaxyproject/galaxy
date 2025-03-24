<script setup lang="ts">
import { faChevronDown, faChevronUp } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref } from "vue";

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
    /** If `true`, shows the full text */
    showExpandText?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    maxLength: 150,
    component: "span",
    showExpandText: true,
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
</script>

<template>
    <div class="text-summary" :class="{ 'text-summary-short': !showDetails || props.oneLineSummary }">
        <component :is="props.component" ref="refOneLineSummary">
            <div class="html-paragraph d-inline-block overflow-hidden w-100" v-html="props.description" />
        </component>

        <span
            v-if="!noExpand && textTooLong"
            v-b-tooltip.hover
            class="text-summary-expand-button"
            :class="{ 'text-summary-expand-float': !props.showExpandText }"
            :title="showDetails ? 'Show less' : 'Show more'"
            role="button"
            tabindex="0"
            @keyup.enter="showDetails = !showDetails"
            @click="showDetails = !showDetails">
            <template v-if="showExpandText">
                <template v-if="showDetails">Show less</template>
                <template v-else>Show more</template>
            </template>

            <FontAwesomeIcon :icon="showDetails ? faChevronUp : faChevronDown" />
        </span>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.text-summary {
    &.text-summary-short {
        .html-paragraph {
            text-overflow: ellipsis;
            white-space: nowrap;

            :deep(p) {
                white-space: nowrap;
            }
        }
    }

    &:deep(p) {
        margin: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        width: 100%;

        &:not(:first-child) {
            display: none;
        }
    }
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
