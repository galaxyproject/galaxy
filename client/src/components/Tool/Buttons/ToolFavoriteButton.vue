<script setup>
import { computed } from "vue";
import { useCurrentUser } from "composables/user";
import ariaAlert from "utils/ariaAlert";

const props = defineProps({
    id: {
        type: String,
        required: true,
    },
});

const emit = defineEmits(["onSetError", "onUpdateFavorites"]);

const { currentUser: user, currentFavorites, addFavoriteTool, removeFavoriteTool } = useCurrentUser();

const hasUser = computed(() => !user.value.isAnonymous);
const isFavorite = computed(() => currentFavorites.value.tools.includes(props.id));
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
        await addFavoriteTool(props.id);
        emit("onSetError", null);
        ariaAlert("added to favorites");
    } catch {
        emit("onSetError", `Failed to add '${props.id}' to favorites.`);
        ariaAlert("failed to add to favorites");
    }
}

async function onRemoveFavorite() {
    try {
        await removeFavoriteTool(props.id);
        emit("onSetError", null);
        ariaAlert("removed from favorites");
    } catch {
        emit("onSetError", `Failed to remove '${props.id}' from favorites.`);
        ariaAlert("failed to remove from favorites");
    }
}
</script>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faStar as fasStar } from "@fortawesome/free-solid-svg-icons";
import { faStar as farStar } from "@fortawesome/free-regular-svg-icons";

library.add(fasStar, farStar);
</script>

<template>
    <b-button v-b-tooltip.hover role="button" variant="link" size="sm" :title="title" @click="onToggleFavorite">
        <icon v-if="showAddFavorite" icon="far fa-star" />
        <icon v-if="showRemoveFavorite" icon="fas fa-star" />
    </b-button>
</template>
