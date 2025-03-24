<script setup>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faStar as farStar } from "@fortawesome/free-regular-svg-icons";
import { faStar as fasStar } from "@fortawesome/free-solid-svg-icons";
import { storeToRefs } from "pinia";
import ariaAlert from "utils/ariaAlert";
import { computed } from "vue";

import { useUserStore } from "@/stores/userStore";

library.add(fasStar, farStar);

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
        return "添加到收藏夹";
    } else if (showRemoveFavorite.value) {
        return "从收藏夹移除";
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
        ariaAlert("已添加到收藏夹");
    } catch {
        emit("onSetError", `添加 '${props.id}' 到收藏夹失败。`);
        ariaAlert("添加到收藏夹失败");
    }
}

async function onRemoveFavorite() {
    try {
        await userStore.removeFavoriteTool(props.id);
        emit("onSetError", null);
        ariaAlert("已从收藏夹移除");
    } catch {
        emit("onSetError", `从收藏夹移除 '${props.id}' 失败。`);
        ariaAlert("从收藏夹移除失败");
    }
}
</script>

<template>
    <b-button v-b-tooltip.hover role="button" variant="link" size="sm" :title="title" @click="onToggleFavorite">
        <icon v-if="showAddFavorite" icon="far fa-star" />
        <icon v-if="showRemoveFavorite" icon="fas fa-star" />
    </b-button>
</template>
