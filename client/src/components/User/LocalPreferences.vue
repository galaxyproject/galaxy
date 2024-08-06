<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faLaptop } from "@fortawesome/free-solid-svg-icons";

import { useLocalPreferencesStore } from "@/stores/localPreferencesStore";

import LocalPreference from "./LocalPreference.vue";
import PreferencePage from "./PreferencePage.vue";

library.add(faLaptop);

const preferencesStore = useLocalPreferencesStore();
</script>

<template>
    <PreferencePage heading="Local Preferences" icon="fa-laptop">
        <LocalPreference
            v-for="(preference, i) in preferencesStore.allPreferences.uncategorized"
            :key="i"
            :preference="preference"></LocalPreference>
    </PreferencePage>
</template>

<style scoped lang="scss"></style>
