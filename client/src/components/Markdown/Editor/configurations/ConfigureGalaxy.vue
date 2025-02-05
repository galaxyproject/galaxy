<template>
    <div class="p-4 bg-white mb-2">
        <div class="mb-3">
            <label class="form-label">Workflow</label>
            <input type="text" class="form-control" />
        </div>
        <div class="mb-3">
            <label class="form-label">History Dataset</label>
            <input type="text" class="form-control" />
        </div>
    </div>
</template>

<script setup lang="ts">
defineProps<{
    content: string;
}>();

defineEmits<{
    (e: "change", content: string): void;
}>();
</script>
