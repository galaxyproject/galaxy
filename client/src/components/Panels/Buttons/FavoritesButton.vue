<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faStar } from "@fortawesome/free-regular-svg-icons";
import { faStar as faRegStar } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import { useUserStore } from "@/stores/userStore";

library.add(faStar, faRegStar);

interface Props {
    query: string;
}
const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "onFavorites", filter: string): void;
}>();

const { isAnonymous } = storeToRefs(useUserStore());

const FAVORITES = ["#favorites", "#favs", "#favourites"];
const toggle = ref(false);

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
        toggle.value = FAVORITES.includes(props.query);
    }
);

function onFavorites() {
    toggle.value = !toggle.value;
    if (toggle.value) {
        emit("onFavorites", "#favorites");
    } else {
        emit("onFavorites", "");
    }
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
        @click="onFavorites">
        <FontAwesomeIcon :icon="toggle ? faRegStar : faStar" />
    </BButton>
</template>
