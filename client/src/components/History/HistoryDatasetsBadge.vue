<script setup lang="ts">
import { faDatabase, faSave } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBadge } from "bootstrap-vue";

interface Props {
    historyId: string;
    niceSize?: string;
    count?: number;
    contentsActive?: {
        deleted?: number;
        hidden?: number;
        active?: number;
    };
    contentsStates?: {
        error?: number;
        ok?: number;
        new?: number;
        running?: number;
        queued?: number;
    };
}

const props = defineProps<Props>();
</script>

<template>
    <BBadge
        v-b-tooltip.hover.top.noninteractive
        class="history-datasets d-flex flex-gapx-1 flex-gapy-1 align-items-center outline-badge cursor-pointer font-size-small"
        pill
        :title="`View history storage overview`"
        variant="light"
        :to="`/storage/history/${props.historyId}`">
        <small v-if="props.count">
            <FontAwesomeIcon :icon="faDatabase" fixed-width />
            <template v-if="props.count"> {{ props.count }} <span class="items">items</span> </template>
        </small>

        <template v-if="props.count && props.niceSize"> | </template>

        <small v-if="props.niceSize">
            <FontAwesomeIcon :icon="faSave" fixed-width />
            {{ props.niceSize }}
        </small>

        <template
            v-if="
                (props.contentsStates && Object.values(props.contentsStates).some((count) => count)) ||
                (props.contentsActive && Object.values(props.contentsActive).some((count) => count))
            ">
            |
        </template>

        <span
            v-for="(stateCount, state) of props.contentsStates"
            :key="state"
            class="stats px-1 rounded"
            :class="`state-color-${state}`">
            {{ stateCount }}
        </span>

        <span v-if="props.contentsActive?.deleted" class="stats px-1 rounded state-color-deleted">
            {{ props.contentsActive.deleted }}
        </span>

        <span v-if="props.contentsActive?.hidden" class="stats px-1 rounded state-color-hidden">
            {{ props.contentsActive.hidden }}
        </span>
    </BBadge>
</template>

<style lang="scss" scoped>
@import "_breakpoints.scss";

.history-datasets {
    font-size: smaller;

    .items {
        @container g-card (max-width: #{$breakpoint-sm}) {
            display: none;
        }
    }

    .stats {
        border-width: 1px;
        border-style: solid;
    }
}
</style>
