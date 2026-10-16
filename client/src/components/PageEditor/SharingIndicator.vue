<script setup lang="ts">
import { faExclamationTriangle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { ref, watch } from "vue";

import GCheckbox from "@/components/BaseComponents/GCheckbox.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface SharingIndicatorProps {
    accessible: Boolean | String | null;
}

const emit = defineEmits<{
    (e: "makeAccessible"): void;
}>();

const props = defineProps<SharingIndicatorProps>();

const makingAccessible = ref(false);

function makeAccessible() {
    makingAccessible.value = true;
    emit("makeAccessible");
}

watch(props, () => {
    makingAccessible.value = false;
});
</script>
<template>
    <div>
        <LoadingSpan v-if="accessible == null || makingAccessible" spinner-only> </LoadingSpan>
        <div v-else-if="typeof accessible == 'string'">
            <FontAwesomeIcon
                :title="accessible"
                :icon="faExclamationTriangle"
                class="make-page-object-accessible-sharing-error-icon" />
        </div>
        <GCheckbox
            v-else
            switch
            aria-label="Make accessible"
            class="make-page-object-accessible"
            :model-value="accessible === true"
            :disabled="accessible === true"
            @update:model-value="makeAccessible" />
    </div>
</template>

<style lang="scss">
/* scoped doesn't seem to work to prefixing with a class name */
@import "@/style/scss/theme/blue.scss";

.make-page-object-accessible-sharing-error-icon {
    color: $brand-danger;
}

// Off reads as a warning and the locked on-state as success, so the table shows what still needs sharing
label.make-page-object-accessible.g-checkbox.g-switch > .g-checkbox-input {
    --g-switch-knob-color: white;

    border-color: lighten($brand-warning, 15%);
    background-color: lighten($brand-warning, 15%);

    &:disabled {
        border-color: lighten($brand-success, 15%);
        background-color: lighten($brand-success, 15%);
    }
}

label.make-page-object-accessible.g-checkbox.g-disabled {
    opacity: 1;
}
</style>
