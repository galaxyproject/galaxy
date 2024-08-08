<script setup lang="ts">
import { faUndoAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { computed } from "vue";

import { type Preference, type PreferenceTypeNumber, useLocalPreferencesStore } from "@/stores/localPreferencesStore";

import FormNumber from "../Form/Elements/FormNumber.vue";
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

function getNumberType(type: PreferenceTypeNumber): "float" | "integer" {
    if (!type.step) {
        return "float";
    }

    const isWholeNumber = type.step % 1 === 0;

    if (isWholeNumber) {
        return "integer";
    } else {
        return "float";
    }
}
</script>

<template>
    <div class="local-preference">
        <div class="preference-heading">
            <b> {{ name }} </b>
            <BButton size="sm" title="Reset" @click="resetPreference">
                <FontAwesomeIcon :icon="faUndoAlt"></FontAwesomeIcon>
            </BButton>
        </div>

        <p v-if="description">
            {{ description }}
        </p>

        <FormSelect v-if="type.option" v-model="preferenceValue" :options="type.options"></FormSelect>
        <FormBoolean v-if="type.boolean" v-model="preferenceValue"></FormBoolean>
        <FormNumber
            v-if="type.number"
            v-model="preferenceValue"
            :type="getNumberType(type)"
            :min="type.range?.min"
            :max="type.range?.max"></FormNumber>
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
