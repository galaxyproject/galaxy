<script setup>
import { useCurrentTheme } from "composables/userFlags";
import { useConfig } from "@/composables/config";
import { watch, ref } from "vue";

import { library } from "@fortawesome/fontawesome-svg-core";
import { faPalette } from "@fortawesome/free-solid-svg-icons";

const { currentTheme, setCurrentTheme } = useCurrentTheme();
const { config, isLoaded } = useConfig();

const show = ref(false);

watch(
    () => isLoaded.value,
    () => {
        const themes = Object.keys(config.value.themes);
        show.value = themes?.length > 1 ?? false;

        if (!themes.includes(currentTheme.value)) {
            setCurrentTheme(themes[0]);
        }
    }
);

library.add(faPalette);
</script>

<template>
    <b-nav-item-dropdown v-show="show" text="Theme">
        <b-dropdown-item
            v-for="(theme, name) in config.themes"
            :key="name"
            :active="name === currentTheme"
            @click="() => setCurrentTheme(name)">
            <icon v-if="name === currentTheme" icon="fas fa-check" />
            <icon v-else icon="fas fa-palette" />

            <span>{{ name }}</span>
        </b-dropdown-item>
    </b-nav-item-dropdown>
</template>
