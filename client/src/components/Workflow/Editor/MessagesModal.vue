<script setup lang="ts">
import { ref, watch } from "vue";

import GAlert from "@/components/BaseComponents/GAlert.vue";
import GModal from "@/components/BaseComponents/GModal.vue";

const props = defineProps<{
    title?: string;
    message?: string;
    error?: boolean;
}>();

const emit = defineEmits(["onHidden"]);

const show = ref(!!props.title);

watch(
    () => props.message,
    () => {
        show.value = !!props.title;
    },
);
</script>

<template>
    <!-- TODO: Implement no close on no error; as in it's unclosable when no error
     or, we remove the progress functionality entirely. -->
    <GModal :show.sync="show" size="small" :title="props.title" @close="emit('onHidden')">
        <div class="workflow-message-modal">
            <div v-if="props.message == 'progress'">
                <div class="progress progress-striped active">
                    <div class="progress-bar" style="width: 100%"></div>
                </div>
            </div>
            <GAlert v-else :variant="props.error ? 'danger' : 'info'">
                {{ props.message }}
            </GAlert>
        </div>
    </GModal>
</template>
