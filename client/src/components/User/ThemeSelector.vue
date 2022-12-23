<script setup>
import { useCurrentTheme } from "@/composables/user";
import { useConfig } from "@/composables/config";
import { computed, watch, ref } from "vue";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faPalette } from "@fortawesome/free-solid-svg-icons";
import { safePath } from "@/utils/redirect";
const { currentTheme, setCurrentTheme } = useCurrentTheme();
const { config, isLoaded } = useConfig();
const show = ref(false);
const currentValue = computed({
    get: () => {
        return currentTheme;
    },
    set: (theme) => {
        setCurrentTheme(theme);
    },
});
function getStyle(theme, variantKey) {
    return {
        background: theme[`--masthead-link-${variantKey}`],
        color: theme[`--masthead-text-${variantKey}`],
    };
}
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
    <b-card :show="show">
        <b-form-radio-group v-model="currentValue">
            <b-form-radio v-for="(theme, name) in config.themes" :key="name" :value="name" class="mb-2">
                <span class="font-weight-bold mb-1">{{ name }}</span>
                <div class="rounded p-1" :style="{ background: theme['--masthead-color'] }">
                    <img :src="safePath(theme['--masthead-logo-img'])" alt="image" />
                    <span v-localize :style="getStyle(theme, 'color')" class="rounded p-1">Text</span>
                    <span v-localize :style="getStyle(theme, 'active')" class="rounded p-1">Active</span>
                    <span v-localize :style="getStyle(theme, 'hover')" class="rounded p-1">Hover</span>
                </div>
            </b-form-radio>
        </b-form-radio-group>
    </b-card>
</template>
<style scoped>
img {
    display: inline;
    border: none;
    height: 2rem;
}
</style>
