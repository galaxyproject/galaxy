<script setup lang="ts">
import { faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBadge } from "bootstrap-vue";

import GButton from "@/components/BaseComponents/GButton.vue";

const emit = defineEmits(["stop-flagging"]);
</script>

<template>
    <BBadge class="form-input-changed-input-badge" pill size="sm">
        <span
            v-localize
            v-b-tooltip.hover.noninteractive
            title="This input has a different value than in the original run">
            Changed Input
        </span>
        <GButton
            class="p-0"
            transparent
            size="small"
            icon-only
            pill
            title="Stop flagging inputs that do not match the original run"
            tooltip
            @click="emit('stop-flagging')">
            <FontAwesomeIcon :icon="faTimes" fixed-width />
        </GButton>
    </BBadge>
</template>

<style scoped lang="scss">
@import "scss/theme/blue.scss";

.form-input-changed-input-badge {
    display: flex;
    gap: 0.25rem;
    align-items: center;
    background-color: $state-info-bg;
    font-weight: normal;
}
</style>
