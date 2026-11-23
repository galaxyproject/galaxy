<script setup lang="ts">
import GFormInput from "@/components/BaseComponents/Form/GFormInput.vue";

const props = defineProps<{
    width: number;
    height: number;
}>();

const emit = defineEmits<{
    (e: "update:width", value: number): void;
    (e: "update:height", value: number): void;
}>();

// v-model casts a type="number" input's value to a number, but an empty or partial
// number ("-", "1e") comes through as ""; keep the last size then
function toSize(value: string | number | null, current: number) {
    if (typeof value === "number") {
        return value;
    }
    const size = parseFloat(value ?? "");
    return Number.isNaN(size) ? current : size;
}
</script>

<template>
    <div class="dimension-controls">
        <label>
            Width
            <GFormInput
                :model-value="String(props.width)"
                type="number"
                min="200"
                max="2000"
                step="50"
                @update:model-value="emit('update:width', toSize($event, props.width))" />
        </label>
        <label>
            Height
            <GFormInput
                :model-value="String(props.height)"
                type="number"
                min="200"
                max="2000"
                step="50"
                @update:model-value="emit('update:height', toSize($event, props.height))" />
        </label>
    </div>
</template>

<style scoped lang="scss">
.dimension-controls {
    display: flex;
    gap: 1rem;
    margin-top: 0.5rem;

    label {
        flex: 1;
        font-size: 0.875rem;
    }
}
</style>
