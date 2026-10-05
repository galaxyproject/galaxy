<script setup lang="ts">
import { GAlert, GButton } from "@galaxyproject/galaxy-ui"
import { ref, watch, computed } from "vue"

const show = ref(true)

interface ErrorProps {
    error: string
}

const props = defineProps<ErrorProps>()

type Emits = {
    (eventName: "dismiss"): void
}

const emits = defineEmits<Emits>()

function dismiss() {
    show.value = false
    emits("dismiss")
}

watch(
    () => props.error,
    () => {
        show.value = true
    },
)
const effectiveShow = computed(() => props.error && show.value)
</script>

<template>
    <div class="q-pa-md q-gutter-sm">
        <GAlert v-if="effectiveShow" variant="danger" aria-live="assertive" class="error-banner">
            <strong>{{ props.error }}</strong>
            <GButton transparent class="error-banner-dismiss" @click="dismiss">Dismiss</GButton>
        </GAlert>
    </div>
</template>

<style scoped>
.error-banner {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--spacing-2);
}

.error-banner-dismiss {
    flex-shrink: 0;
}
</style>
