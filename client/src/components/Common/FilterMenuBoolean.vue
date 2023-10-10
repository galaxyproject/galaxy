<script setup lang="ts">
import { computed } from "vue";

const props = defineProps({
    filter: { type: Object, required: true },
    name: { type: String, required: true },
    filters: { type: Object, required: true },
});

const boolType = computed(() => props.filter.boolType || "default");

const options =
    boolType.value == "default"
        ? [
              { text: "Any", value: "any" },
              { text: "Yes", value: true },
              { text: "No", value: false },
          ]
        : [
              { text: "Yes", value: true },
              { text: "No", value: "any" },
          ];

const emit = defineEmits<{
    (e: "change", name: string, value: boolean | string | undefined): void;
    (e: "on-enter"): void;
    (e: "on-esc"): void;
}>();

const value = computed({
    get: () => {
        const value = props.filters[props.name];
        return value !== undefined ? value : "any";
    },
    set: (newVal: boolean | string | undefined) => {
        const value = newVal !== null ? newVal : "any";
        emit("change", props.name, value);
    },
});
</script>

<template>
    <!-- eslint-disable-next-line vuejs-accessibility/no-static-element-interactions -->
    <div @keyup.enter="emit('on-enter')" @keyup.esc="emit('on-esc')">
        <small>{{ props.filter.placeholder }}:</small>
        <b-form-group class="m-0">
            <b-form-radio-group
                v-model="value"
                :options="options"
                size="sm"
                buttons
                :data-description="`filter ${props.name}`" />
        </b-form-group>
    </div>
</template>
