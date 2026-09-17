<script setup lang="ts">
import { faChevronCircleRight } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import type { ConnectorVariant } from "./types";

interface Props {
    /** "multiple" renders a larger connector — used to mark collections. */
    variant?: ConnectorVariant;
}

withDefaults(defineProps<Props>(), {
    variant: "single",
});
</script>

<template>
    <span class="graph-connector" :class="`graph-connector--${variant}`">
        <FontAwesomeIcon :icon="faChevronCircleRight" class="graph-connector-icon" />
    </span>
</template>

<style lang="scss" scoped>
@import "@/style/scss/theme/blue.scss";

.graph-connector {
    --size: 12px;
    position: relative;
    display: block;
    width: var(--size);
    height: var(--size);

    // White disc behind the chevron icon — the icon's negative space reads white.
    &::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        width: var(--size);
        height: var(--size);
        border-radius: 50%;
        background-color: $white;
    }
}

.graph-connector--multiple {
    --size: 20px;
}

.graph-connector-icon {
    position: absolute;
    top: -1px;
    left: -1px;
    width: calc(var(--size) + 2px);
    height: calc(var(--size) + 2px);
    color: $brand-primary;
}
</style>
