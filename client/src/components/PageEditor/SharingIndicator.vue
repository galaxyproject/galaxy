<script setup lang="ts">
import { ref, watch } from "vue";

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
            <Icon
                :title="accessible"
                icon="exclamation-triangle"
                class="make-page-object-accessible-sharing-error-icon" />
        </div>
        <BFormCheckbox
            v-else
            switch
            :checked="accessible"
            class="make-page-object-accessible"
            :disabled="accessible"
            @change="
                (event) => {
                    makeAccessible(event);
                }
            ">
        </BFormCheckbox>
    </div>
</template>

<style lang="scss">
/* scoped doesn't seem to work to prefixing with a class name */
@import "theme/blue.scss";

.make-page-object-accessible-sharing-error-icon {
    color: $brand-danger;
}

.make-page-object-accessible .custom-control-label::after {
    background-color: white;
}

.make-page-object-accessible .custom-control-label::before {
    background-color: lighten($brand-warning, 15%) !important;
}

.make-page-object-accessible .custom-control-input[disabled] ~ .custom-control-label::before {
    background-color: lighten($brand-success, 15%) !important;
}
</style>
