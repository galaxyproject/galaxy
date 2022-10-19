<script setup>
const props = defineProps({
    historyId: {
        type: String,
        required: true,
    },
});
//TODO
</script>
<template>
    <div>
        <h2 class="text-center my-3">
            <b>History Storage Overview</b>
        </h2>
        <p class="text-center">
            TODO: This will contain some Graphs displaying the storage taken by datasets in history:
            <b>{{ props.historyId }}</b>
        </p>
    </div>
</template>
