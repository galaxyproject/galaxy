<script setup lang="ts">
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

watch(ref(props.error), () => {
    show.value = true
})
const effectiveShow = computed(() => props.error && show.value)
</script>

<template>
    <div class="q-pa-md q-gutter-sm">
        <q-banner inline-actions rounded class="bg-negative text-white" v-if="effectiveShow">
            <strong>{{ props.error }}</strong>
            <template #action>
                <q-btn flat label="Dismiss" @click="dismiss" />
            </template>
        </q-banner>
    </div>
</template>
