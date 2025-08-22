<script setup lang="ts">
import { faStar as farStar } from "@fortawesome/free-regular-svg-icons";
import { faStar as fasStar } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import type { ComponentColor } from "@/components/BaseComponents/componentVariants";
import { useUserStore } from "@/stores/userStore";
import ariaAlert from "@/utils/ariaAlert";

import GButton from "@/components/BaseComponents/GButton.vue";

interface Props {
    id: string;
    color?: ComponentColor;
    detailed?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    color: "blue",
});

const emit = defineEmits(["onSetError", "onUpdateFavorites"]);

const loading = ref(false);

const userStore = useUserStore();
const { currentFavorites, isAnonymous } = storeToRefs(userStore);
const isFavorite = computed(() => currentFavorites.value.tools?.includes(props.id));

const title = computed(() => {
    if (isAnonymous.value) {
        return "Login or Register to Favorite Tools";
    }
    if (isFavorite.value) {
        return "Remove from Favorites";
    } else {
        return "Add to Favorites";
    }
});

const icon = computed(() => (isAnonymous.value || !isFavorite.value ? farStar : fasStar));

function onToggleFavorite() {
    if (isAnonymous.value) {
        emit("onSetError", "You must be signed in to manage favorites.");
        ariaAlert("sign in to manage favorites");
        return;
    }

    if (isFavorite.value) {
        onRemoveFavorite();
    } else {
        onAddFavorite();
    }
}

async function onAddFavorite() {
    try {
        loading.value = true;
        await userStore.addFavoriteTool(props.id);
        emit("onSetError", null);
        ariaAlert("added to favorites");
    } catch {
        emit("onSetError", `Failed to add '${props.id}' to favorites.`);
        ariaAlert("failed to add to favorites");
    } finally {
        loading.value = false;
    }
}

async function onRemoveFavorite() {
    try {
        loading.value = true;
        await userStore.removeFavoriteTool(props.id);
        emit("onSetError", null);
        ariaAlert("removed from favorites");
    } catch {
        emit("onSetError", `Failed to remove '${props.id}' from favorites.`);
        ariaAlert("failed to remove from favorites");
    } finally {
        loading.value = false;
    }
}
</script>

<template>
    <GButton
        :color="props.color"
        :disabled="isAnonymous || loading"
        :disabled-title="title"
        tooltip
        size="small"
        :transparent="!props.detailed"
        :title="title"
        @click="onToggleFavorite">
        <FontAwesomeIcon :icon="icon" />
        <span v-if="props.detailed">
            <span v-if="isAnonymous || !isFavorite"> Add to Favorites </span>
            <span v-else> Remove </span>
        </span>
    </GButton>
</template>
