<script setup>
import { faStar as farStar } from "@fortawesome/free-regular-svg-icons";
import { faStar as fasStar } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import ariaAlert from "utils/ariaAlert";
import { computed } from "vue";

import { useUserStore } from "@/stores/userStore";

import GButton from "@/components/BaseComponents/GButton.vue";

const props = defineProps({
    id: {
        type: String,
        required: true,
    },
});

const emit = defineEmits(["onSetError", "onUpdateFavorites"]);

const userStore = useUserStore();
const { currentFavorites, isAnonymous } = storeToRefs(userStore);
const hasUser = computed(() => !isAnonymous.value);
const isFavorite = computed(() => currentFavorites.value.tools?.includes(props.id));
const showAddFavorite = computed(() => hasUser.value && !isFavorite.value);
const showRemoveFavorite = computed(() => hasUser.value && isFavorite.value);

const title = computed(() => {
    if (showAddFavorite.value) {
        return "Add to Favorites";
    } else if (showRemoveFavorite.value) {
        return "Remove from Favorites";
    } else {
        return null;
    }
});

function onToggleFavorite() {
    if (isFavorite.value) {
        onRemoveFavorite();
    } else {
        onAddFavorite();
    }
}

async function onAddFavorite() {
    try {
        await userStore.addFavoriteTool(props.id);
        emit("onSetError", null);
        ariaAlert("added to favorites");
    } catch {
        emit("onSetError", `Failed to add '${props.id}' to favorites.`);
        ariaAlert("failed to add to favorites");
    }
}

async function onRemoveFavorite() {
    try {
        await userStore.removeFavoriteTool(props.id);
        emit("onSetError", null);
        ariaAlert("removed from favorites");
    } catch {
        emit("onSetError", `Failed to remove '${props.id}' from favorites.`);
        ariaAlert("failed to remove from favorites");
    }
}
</script>

<template>
    <GButton tooltip transparent :title="title" @click="onToggleFavorite">
        <FontAwesomeIcon v-if="showAddFavorite" :icon="farStar" />
        <FontAwesomeIcon v-if="showRemoveFavorite" :icon="fasStar" />
    </GButton>
</template>
