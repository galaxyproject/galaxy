<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faStar } from "@fortawesome/free-regular-svg-icons";
import { faStar as faRegStar } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { watchImmediate } from "@vueuse/core";
import { BButton } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import { useUserStore } from "@/stores/userStore";

library.add(faStar, faRegStar);

interface Props {
    value?: boolean;
    query?: string;
}

const props = defineProps<Props>();

const currentValue = computed(() => props.value ?? false);
const toggle = ref(false);

watchImmediate(
    () => currentValue.value,
    (val) => (toggle.value = val)
);

const emit = defineEmits<{
    (e: "change", toggled: boolean): void;
    (e: "input", toggled: boolean): void;
}>();

const { isAnonymous } = storeToRefs(useUserStore());

const FAVORITES = ["#favorites", "#favs", "#favourites"];

const tooltipText = computed(() => {
    if (isAnonymous.value) {
        return "Log in to Favorite Tools";
    } else {
        if (toggle.value) {
            return "Clear";
        } else {
            return "Show favorites";
        }
    }
});

watch(
    () => props.query,
    () => {
        toggle.value = FAVORITES.includes(props.query ?? "");
    }
);

function toggleFavorites() {
    toggle.value = !toggle.value;
    emit("input", toggle.value);
    emit("change", toggle.value);
}
</script>

<template>
    <BButton
        v-b-tooltip.hover.top.noninteractive
        class="panel-header-button-toolbox"
        size="sm"
        variant="link"
        aria-label="Show favorite tools"
        :disabled="isAnonymous"
        :title="tooltipText"
        @click="toggleFavorites">
        <FontAwesomeIcon :icon="toggle ? faRegStar : faStar" />
    </BButton>
</template>
