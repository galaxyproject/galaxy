<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faLaptop } from "@fortawesome/free-solid-svg-icons";

import { useLocalPreferencesStore } from "@/stores/localPreferencesStore";

import Heading from "../Common/Heading.vue";
import LocalPreference from "./LocalPreference.vue";
import PreferencePage from "./PreferencePage.vue";

library.add(faLaptop);

const preferencesStore = useLocalPreferencesStore();
</script>

<template>
    <PreferencePage heading="Local Preferences" icon="fa-laptop">
        <div class="preference-list">
            <LocalPreference
                v-for="(preference, i) in preferencesStore.allPreferences.uncategorized"
                :key="i"
                :preference="preference"></LocalPreference>
        </div>

        <section
            v-for="(category, id) in preferencesStore.allPreferences.categories"
            :key="id"
            class="preference-category">
            <Heading h2 inline size="md"> {{ category.name }} </Heading>
            <p v-if="category.description">
                {{ category.description }}
            </p>

            <div class="preference-list">
                <LocalPreference
                    v-for="(preference, i) in category.preferences"
                    :key="i"
                    :preference="preference"></LocalPreference>
            </div>
        </section>
    </PreferencePage>
</template>

<style scoped lang="scss">
.preference-list {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.preference-category {
    margin-top: 1rem;

    .preference-list {
        padding-left: 0.5rem;
    }
}
</style>
