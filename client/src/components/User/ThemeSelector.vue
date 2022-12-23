<script setup>
import { useCurrentTheme } from "@/composables/userFlags";
import { useConfig } from "@/composables/config";
import { computed, watch, ref } from "vue";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faPalette } from "@fortawesome/free-solid-svg-icons";
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
        <b-form-radio-group v-model="currentValue" stacked>
            <b-form-radio v-for="(theme, name) in config.themes" :key="name" :value="name">
                <span>{{ name }}</span>
                <div class="rounded p-2" :style="{ background: theme['--masthead-color'] }">
                    <div
                        class="rounded p-1"
                        :style="{
                            background: theme['--masthead-link-color'],
                            color: theme['--masthead-text-color'],
                        }"
                        v-localize>
                        Text
                    </div>
                    <div
                        class="rounded p-1"
                        :style="{
                            background: theme['--masthead-link-active'],
                            color: theme['--masthead-text-active'],
                        }"
                        v-localize>
                        Active
                    </div>
                    <div
                        class="rounded p-1"
                        :style="{
                            background: theme['--masthead-link-hover'],
                            color: theme['--masthead-text-hover'],
                        }"
                        v-localize>
                        Hover
                    </div>
                </div>
            </b-form-radio>
        </b-form-radio-group>
    </b-card>
</template>
