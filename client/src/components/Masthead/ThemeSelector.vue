<script setup>
import { useCurrentTheme } from "composables/userFlags";
import { useConfig } from "composables/useConfig";
import { watch } from "vue";

import { library } from "@fortawesome/fontawesome-svg-core";
import { faPalette } from "@fortawesome/free-solid-svg-icons";

const { currentTheme, setCurrentTheme } = useCurrentTheme();
const { config, isLoaded } = useConfig();

watch(
    () => isLoaded.value,
    () => {
        if (config.value.themes && !(currentTheme.value in config.value.themes)) {
            setCurrentTheme(Object.keys(config.value.themes)[0]);
        }
    }
);

library.add(faPalette);
</script>

<template>
    <b-nav-item-dropdown text="Theme">
        <b-dropdown-item v-for="(theme, name) in config.themes" :key="name" :active="name === currentTheme">
            <icon v-if="name === currentTheme" icon="fas fa-check" />
            <icon v-else icon="fas fa-palette" />
            <span>{{ name }}</span>
        </b-dropdown-item>
    </b-nav-item-dropdown>
</template>
