<script setup lang="ts">
import { onMounted } from "vue";
import { useRouter } from "vue-router/composables";

// Thin wrapper that simply routes to the existing Rule-based Data Import activity
const router = useRouter();

onMounted(() => {
    router.push({ path: "/rules" });
});
</script>

<template>
    <div class="text-center my-4">
        <p>Launching Rule Based Data Import…</p>
    </div>
</template>
