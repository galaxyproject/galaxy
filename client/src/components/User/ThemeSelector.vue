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
function getStyle(themeDetails, variantKey) {
    return {
        background: themeDetails[`--masthead-link-${variantKey}`],
        color: themeDetails[`--masthead-text-${variantKey}`],
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
            <b-form-radio v-for="(themeDetails, theme) in config.themes" :key="theme" :value="theme" class="mb-2">
                <span class="font-weight-bold mb-1">{{ theme }}</span>
                <div class="rounded p-1" :style="{ background: themeDetails['--masthead-color'] }">
                    <img :src="safePath(themeDetails['--masthead-logo-img'])" alt="image" />
                    <span v-localize :style="getStyle(themeDetails, 'color')" class="rounded p-1">Text</span>
                    <span v-localize :style="getStyle(themeDetails, 'hover')" class="rounded p-1">Hover</span>
                    <span v-localize :style="getStyle(themeDetails, 'active')" class="rounded p-1">Active</span>
                </div>
            </b-form-radio>
        </b-form-radio-group>
    </b-card>
</template>
<style scoped>
img {
    cursor: pointer;
    display: inline;
    border: none;
    height: 2rem;
}
</style>
