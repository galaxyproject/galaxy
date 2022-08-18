<script setup>
import { computed } from "vue";
import { useCurrentUser } from "composables/user";
import ariaAlert from "utils/ariaAlert";
import { addFavorite, removeFavorite } from "components/Tool/services";

const props = defineProps({
    id: {
        type: String,
        required: true,
    },
});

const emit = defineEmits(["onSetError", "onUpdateFavorites"]);

const user = useCurrentUser();

const hasUser = computed(() => !user.value.isAnonymous);
const isFavorite = computed(() => getFavorites().tools.includes(props.id));
const showAddFavorite = computed(() => hasUser && !isFavorite);
const showRemoveFavorite = computed(() => hasUser && isFavorite);

const title = computed(() => {
    if (showAddFavorite) {
        return "Add to Favorites";
    } else if (showRemoveFavorite) {
        return "Remove from Favorites";
    } else {
        return null;
    }
});

function onToggleFavorite() {
    if (isFavorite) {
        onRemoveFavorite();
    } else {
        onAddFavorite();
    }
}

async function onAddFavorite() {
    try {
        const data = await addFavorite(user.value.id, props.id);
        updateFavorites("tools", data);
        emit("onSetError", null);
        ariaAlert("added to favorites");
    } catch {
        emit("onSetError", `Failed to add '${props.id}' to favorites.`);
        ariaAlert("failed to add to favorites");
    }
}

async function onRemoveFavorite() {
    try {
        const data = await removeFavorite(user.value.id, props.id);
        updateFavorites("tools", data);
        emit("onSetError", null);
        ariaAlert("removed from favorites");
    } catch {
        emit("onSetError", `Failed to remove '${props.id}' from favorites.`);
        ariaAlert("failed to remove from favorites");
    }
}

function getFavorites() {
    const preferences = user.value.preferences;

    if (preferences?.favorites) {
        return JSON.parse(preferences.favorites);
    } else {
        return { tools: [] };
    }
}

function updateFavorites(objectType, newFavorites) {
    const favorites = getFavorites();
    favorites[objectType] = newFavorites[objectType];
    emit("onUpdateFavorites", user.value, JSON.stringify(favorites));
}
</script>

<template>
    <b-button v-b-tooltip.hover role="button" variant="link" size="sm" :title="title" @click="onToggleFavorite">
        <icon v-if="showAddFavorite" icon="star" />
        <icon v-if="showRemoveFavorite" icon="far fa-star" />
    </b-button>
</template>
