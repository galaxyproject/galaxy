<script setup lang="ts">
import { computed } from "vue";

import { Preference, useLocalPreferencesStore } from "@/stores/localPreferencesStore";

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
</script>

<template>
    <div class="local-preference">
        <b> {{ name }} </b>

        <p v-if="description">
            {{ description }}
        </p>

        <FormSelect v-if="'option' in type" v-model="preferenceValue" :options="type.options"></FormSelect>
    </div>
</template>

<style scoped lang="scss">
p {
    margin-bottom: 0.2rem;
}
</style>
