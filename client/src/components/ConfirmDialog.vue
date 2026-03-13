<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert } from "bootstrap-vue";
import { ref } from "vue";

import { type ConfirmDialogOptions, DEFAULT_CONFIRM_OPTIONS } from "@/composables/confirmDialog";

import GButton from "@/components/BaseComponents/GButton.vue";
import GModal from "@/components/BaseComponents/GModal.vue";

const show = ref(false);
const message = ref("");
const currentOptions = ref<ConfirmDialogOptions>({ ...DEFAULT_CONFIRM_OPTIONS });

let resolveCallback: ((value: boolean) => void) | null = null;

function confirm(msg: string, options: ConfirmDialogOptions = {}): Promise<boolean> {
    // Resolve any pending dialog as false before showing a new one
    resolveCallback?.(false);
    resolveCallback = null;

    message.value = msg;
    currentOptions.value = { ...DEFAULT_CONFIRM_OPTIONS, ...options };

    if (!show.value) {
        show.value = true;
    }

    return new Promise((resolve) => {
        resolveCallback = resolve;

        options.signal?.addEventListener("abort", () => handleResponse(false), { once: true });
    });
}

function handleResponse(isOk: boolean) {
    resolveCallback?.(isOk);
    resolveCallback = null;
    show.value = false;
}

defineExpose({ confirm });
</script>

<template>
    <GModal
        id="galaxy-confirm-dialog"
        footer
        :show="show"
        size="small"
        :title="currentOptions.title"
        @close="handleResponse(false)">
        <BAlert class="mb-0" data-description="confirm dialog message" variant="info" show>
            {{ message }}
        </BAlert>
        <template v-slot:footer>
            <div class="button-container">
                <GButton
                    class="confirm-button"
                    data-description="confirm dialog cancel"
                    @click="handleResponse(false)"
                    >{{ currentOptions.cancelText }}</GButton
                >
                <GButton
                    class="confirm-button"
                    :color="currentOptions.okColor"
                    data-description="confirm dialog ok"
                    @click="handleResponse(true)">
                    <FontAwesomeIcon v-if="currentOptions.okIcon" :icon="currentOptions.okIcon" fixed-width />
                    {{ currentOptions.okText }}
                </GButton>
            </div>
        </template>
    </GModal>
</template>

<style scoped lang="scss">
.button-container {
    display: flex;
    width: 100%;
    gap: 0.5rem;
}

.confirm-button {
    flex: 1;
}
</style>
