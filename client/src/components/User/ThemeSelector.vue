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
function getBackground(themeDetails, variantKey) {
    const background = themeDetails[`--${variantKey}`];
    const styles = {};
    if (background) {
        styles["background"] = background;
    }
    return styles;
}
function getImage(themeDetails, imageKey) {
    return themeDetails[`--masthead-${imageKey}`] ?? config.value.logo_src;
}
function getStyle(themeDetails, variantKey) {
    const backgroundKey = `--masthead-link-${variantKey}`;
    const colorKey = `--masthead-text-${variantKey}`;
    const background = themeDetails[backgroundKey];
    const color = themeDetails[colorKey];
    const styles = {};
    if (background) {
        styles["background"] = background;
    }
    if (color) {
        styles["color"] = color;
    }
    return styles;
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
    <b-card :show="show" class="overflow-auto">
        <b-form-radio-group v-model="currentValue">
            <b-form-radio v-for="(themeDetails, theme) in config.themes" :key="theme" :value="theme" class="mb-2">
                <span class="font-weight-bold mb-1">{{ theme }}</span>
                <div class="default-theme-masthead" :style="getBackground(themeDetails, 'masthead-color')">
                    <img :src="safePath(getImage(themeDetails, 'logo-img'))" alt="image" />
                    <span v-localize :style="getStyle(themeDetails, 'color')" class="default-theme-color"> Text </span>
                    <span v-localize :style="getStyle(themeDetails, 'hover')" class="default-theme-hover"> Hover </span>
                    <span v-localize :style="getStyle(themeDetails, 'active')" class="default-theme-active">
                        Active
                    </span>
                </div>
            </b-form-radio>
        </b-form-radio-group>
    </b-card>
</template>
<style lang="scss" scoped>
@import "~bootstrap/scss/bootstrap.scss";
@import "custom_theme_variables.scss";
.default-element {
    @extend .rounded;
    @extend .p-1;
}
.default-theme-masthead {
    @extend .default-element;
    background: $masthead-color;
}
.default-theme-color {
    @extend .default-element;
    color: $masthead-text-color;
    background: $masthead-link-color;
}
.default-theme-hover {
    @extend .default-element;
    color: $masthead-text-hover;
    background: $masthead-link-hover;
}
.default-theme-active {
    @extend .default-element;
    color: $masthead-text-active;
    background: $masthead-link-active;
}
img {
    cursor: pointer;
    display: inline;
    border: none;
    height: 2rem;
}
</style>
