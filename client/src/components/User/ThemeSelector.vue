<script setup>
import { computed, ref, watch } from "vue";

import { useConfig } from "@/composables/config";
import { useCurrentTheme } from "@/composables/user";
import { withPrefix } from "@/utils/redirect";

const { currentTheme, setCurrentTheme } = useCurrentTheme();
const { config, isConfigLoaded } = useConfig();

const show = ref(false);
const currentValue = computed({
    get: () => {
        return currentTheme;
    },
    set: (theme) => {
        setCurrentTheme(theme);
    },
});

function getLogo(themeDetails) {
    return themeDetails["--masthead-logo-img"] ?? config.value.logo_src;
}

watch(
    () => isConfigLoaded.value,
    () => {
        const themes = Object.keys(config.value.themes);
        show.value = themes?.length > 1 ?? false;
        if (!themes.includes(currentTheme.value)) {
            setCurrentTheme(themes[0]);
        }
    }
);
</script>

<template>
    <b-card :show="show" class="mr-3 overflow-auto reset-theme-variables">
        <b-form-radio-group v-model="currentValue">
            <b-form-radio
                v-for="(themeDetails, theme, index) in config.themes"
                :key="theme"
                :value="theme"
                class="mb-2">
                <span v-if="index === 0" class="font-weight-bold mb-1"> 默认主题 ({{ theme }}). </span>
                <span v-else class="font-weight-bold mb-1">主题: {{ theme }}</span>
                <div :style="themeDetails" class="theme-masthead">
                    <img :src="withPrefix(getLogo(themeDetails))" alt="图片" />
                    <span v-localize class="theme-color">文本</span>
                    <span v-localize class="theme-hover">悬停</span>
                    <span v-localize class="theme-active">激活</span>
                </div>
            </b-form-radio>
        </b-form-radio-group>
    </b-card>
</template>

<style lang="scss" scoped>
@import "~bootstrap/scss/bootstrap.scss";
@import "custom_theme_variables.scss";
.theme-element {
    @extend .rounded;
    @extend .p-1;
}
.theme-masthead {
    @extend .theme-element;
    background: var(--masthead-color);
}
.theme-color {
    @extend .theme-element;
    color: var(--masthead-text-color);
    background: var(--masthead-link-color);
}
.theme-hover {
    @extend .theme-element;
    color: var(--masthead-text-hover);
    background: var(--masthead-link-hover);
}
.theme-active {
    @extend .theme-element;
    color: var(--masthead-text-active);
    background: var(--masthead-link-active);
}
img {
    filter: $text-shadow;
    cursor: pointer;
    display: inline;
    border: none;
    height: 2rem;
}
</style>
