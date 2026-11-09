<script setup lang="ts">
import { faStar as regularStar } from "@fortawesome/free-regular-svg-icons";
import { faStar, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import { type FavoriteObjectKind, useFavoriteObjects } from "@/composables/useFavoriteObjects";

import GButton from "@/components/BaseComponents/GButton.vue";
import GButtonGroup from "@/components/BaseComponents/GButtonGroup.vue";

const props = defineProps<{
    label: string;
    value: string;
    /** What the value is favorited as; without it, the chip only offers removal */
    kind?: FavoriteObjectKind;
    removeTitle: string;
    disabled?: boolean;
}>();
const emit = defineEmits<{ (e: "remove"): void }>();
const { canFavorite, isFavorite, isSaving, toggleFavorite } = useFavoriteObjects();
const favorited = computed(() => Boolean(props.kind && isFavorite(props.kind, props.value)));
const saving = computed(() => Boolean(props.kind && isSaving(props.kind, props.value)));
const favoriteTitle = computed(() =>
    !canFavorite.value
        ? "Sign in to manage favorites"
        : `${favorited.value ? "Remove" : "Add"} ${props.label} ${favorited.value ? "from" : "to"} Favorites`,
);
</script>

<template>
    <GButtonGroup>
        <GButton
            v-if="kind"
            :title="favoriteTitle"
            :disabled="disabled || saving || !canFavorite"
            :disabled-title="favoriteTitle"
            :pressed="favorited"
            :aria-pressed="favorited ? 'true' : 'false'"
            size="small"
            outline
            icon-only
            @click="toggleFavorite(kind, value, label)">
            <FontAwesomeIcon :icon="favorited ? faStar : regularStar" />
        </GButton>
        <GButton :title="removeTitle" :disabled="disabled" size="small" outline @click="emit('remove')">
            {{ label }}
            <FontAwesomeIcon :icon="faTimes" />
        </GButton>
    </GButtonGroup>
</template>
