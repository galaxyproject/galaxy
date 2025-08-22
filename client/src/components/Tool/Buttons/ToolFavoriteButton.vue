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
        return undefined;
    }
});

const icon = computed(() => {
    if (showAddFavorite.value) {
        return farStar;
    } else if (showRemoveFavorite.value) {
        return fasStar;
    }
    return farStar;
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
        :disabled="!title || loading"
        tooltip
        size="small"
        :transparent="!props.detailed"
        :title="title"
        @click="onToggleFavorite">
        <FontAwesomeIcon :icon="icon" />
        <span v-if="props.detailed" class="ms-1">
            {{ showAddFavorite ? "Add to Favorites" : "" }}
            {{ showRemoveFavorite ? "Remove" : "" }}
        </span>
    </GButton>
</template>
