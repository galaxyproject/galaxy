<script setup lang="ts">
import { faStar } from "@fortawesome/free-regular-svg-icons";
import { faStar as faRegStar } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { watchImmediate } from "@vueuse/core";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import { useUserStore } from "@/stores/userStore";

import GButton from "@/components/BaseComponents/GButton.vue";

interface Props {
    value?: boolean;
    query?: string;
    tooltip?: string;
}

const props = withDefaults(defineProps<Props>(), {
    value: false,
    query: undefined,
    tooltip: "Show favorites",
});

const currentValue = computed(() => props.value ?? false);
const toggle = ref(false);

watchImmediate(
    () => currentValue.value,
    (val) => (toggle.value = val),
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
            return props.tooltip;
        }
    }
});

watch(
    () => props.query,
    () => {
        toggle.value = FAVORITES.includes(props.query ?? "");
    },
);

function toggleFavorites() {
    toggle.value = !toggle.value;
    emit("input", toggle.value);
    emit("change", toggle.value);
}
</script>

<template>
    <GButton
        class="d-block"
        transparent
        tooltip
        aria-label="Show favorite tools"
        :disabled="isAnonymous"
        :title="tooltipText"
        @click="toggleFavorites">
        <FontAwesomeIcon :icon="toggle ? faRegStar : faStar" />
    </GButton>
</template>
