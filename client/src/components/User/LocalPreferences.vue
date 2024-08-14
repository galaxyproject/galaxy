<script setup lang="ts">
import { faLaptop, faUndoAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";

import { useLocalPreferencesStore } from "@/stores/localPreferencesStore";

import Heading from "../Common/Heading.vue";
import LocalPreference from "./LocalPreference.vue";
import PreferencePage from "./PreferencePage.vue";

const preferencesStore = useLocalPreferencesStore();
</script>

<template>
    <PreferencePage
        heading="Local Preferences"
        :icon="faLaptop"
        description="Settings specific to this client. These settings will not be synced when logging in on another device.">
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

        <BButton
            class="reset-all-button"
            variant="primary"
            title="Reset all client-side preferences to their default value"
            @click="preferencesStore.resetAllPreferences">
            <FontAwesomeIcon :icon="faUndoAlt"></FontAwesomeIcon>
            Reset all local preferences
        </BButton>
    </PreferencePage>
</template>

<style scoped lang="scss">
.reset-all-button {
    align-self: flex-start;
}

.preference-list {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.preference-category {
    margin-top: 1rem;
    margin-bottom: 1rem;

    .preference-list {
        padding-left: 0.5rem;
    }
}
</style>
