<script setup lang="ts">
import { faUndoAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { computed } from "vue";

import { Preference, useLocalPreferencesStore } from "@/stores/localPreferencesStore";

import FormBoolean from "@/components/Form/Elements/FormBoolean.vue";
import FormSelect from "@/components/Form/Elements/FormSelect.vue";

const props = defineProps<{
    preference: Preference<unknown>;
}>();

const name = computed(() => props.preference.name);
const description = computed(() => props.preference.description);
const type = computed(() => props.preference.type);
const id = computed(() => props.preference.id);

const localPreferencesStore = useLocalPreferencesStore();

const preferenceValue = computed<any>({
    get() {
        return localPreferencesStore.getValueForId(id.value);
    },
    set(value) {
        localPreferencesStore.setValueForId(id.value, value);
    },
});

function resetPreference() {
    localPreferencesStore.resetPreference(id.value);
}
</script>

<template>
    <div class="local-preference">
        <div class="preference-heading">
            <b> {{ name }} </b>
            <BButton variant="primary" size="sm" @click="resetPreference">
                <FontAwesomeIcon :icon="faUndoAlt"></FontAwesomeIcon>
                Reset
            </BButton>
        </div>

        <p v-if="description">
            {{ description }}
        </p>

        <FormSelect v-if="'option' in type" v-model="preferenceValue" :options="type.options"></FormSelect>
        <FormBoolean v-if="'boolean' in type" v-model="preferenceValue"></FormBoolean>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.preference-heading {
    display: grid;
    grid-template-columns: auto 1fr auto;
    gap: 0.75rem;
    grid-template-areas: "a b c";
    align-items: center;

    &::before {
        content: "";
        display: block;
        height: 1px;
        background-color: $brand-secondary;
        grid-area: b;
    }
}

p {
    margin-bottom: 0.2rem;
}
</style>
