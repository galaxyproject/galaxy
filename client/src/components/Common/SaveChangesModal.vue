<script setup lang="ts">
/**
 * Self-contained "unsaved changes" guard + modal: intercepts in-app navigation
 * (Vue Router's `onBeforeRouteLeave`/`onBeforeRouteUpdate`) while `hasChanges` is true,
 * and lets the user choose to save, discard, or cancel via the rendered modal.
 *
 * Also guards non-in-app navigation (tab close, refresh, URL bar) via `beforeunload`,
 * showing the browser's own native confirmation instead -- Vue Router can't intercept those.
 */

import { faSave, faTimes, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { onMounted, onUnmounted, ref } from "vue";
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRouter } from "vue-router/composables";

import { useToast } from "@/composables/toast";
import localize from "@/utils/localization";
import { errorMessageAsString } from "@/utils/simple-error";

import GButton from "@/components/BaseComponents/GButton.vue";
import GModal from "@/components/BaseComponents/GModal.vue";

// TODO: Remove the `@/components/Workflow/Editor/SaveChangesModal.vue` component and replace
// it with this one, though keep in mind!: we would require an `appendVersion` prop as well.

interface Props {
    /** Whether there are unsaved changes to guard against losing */
    hasChanges: boolean;
    /** Saves the pending changes. A rejected promise is caught and Toasted as an error */
    onSave: () => Promise<unknown>;
}

const props = defineProps<Props>();

const router = useRouter();
const Toast = useToast();

const showModal = ref(false);
const pendingNavUrl = ref("");
const busy = ref(false);

/** True while we're pushing a navigation the user already resolved via the modal. */
let bypassGuard = false;

function guard(to: { fullPath: string }, _from: unknown, next: (arg?: false) => void) {
    if (props.hasChanges && !bypassGuard) {
        pendingNavUrl.value = to.fullPath;
        showModal.value = true;
        next(false);
    } else {
        next();
    }
}

onBeforeRouteLeave(guard);
onBeforeRouteUpdate(guard);

function handleBeforeUnload(event: BeforeUnloadEvent) {
    if (props.hasChanges) {
        event.preventDefault();
        event.returnValue = "";
    }
}

onMounted(() => {
    window.addEventListener("beforeunload", handleBeforeUnload);
});

onUnmounted(() => {
    window.removeEventListener("beforeunload", handleBeforeUnload);
});

/**
 *
 * @param url The `URL` we are attempting to navigate to
 * @param forceSave Whether to force saving changes
 * @param ignoreChanges Whether to ignore changes and proceed without saving
 */
async function proceed(url: string, forceSave: boolean, ignoreChanges: boolean) {
    if (forceSave) {
        try {
            await props.onSave();
        } catch (e) {
            Toast.error(errorMessageAsString(e));
            busy.value = false;
            closeModal();
            return;
        }
    } else if (!ignoreChanges) {
        return;
    }

    closeModal();
    bypassGuard = true;
    try {
        // Await the push and only reset bypassGuard/busy once it settles, so a rejected
        // push (Galaxy's patched router.push rethrows on failure) doesn't leave navigation
        // permanently unguarded or the modal's buttons permanently disabled.
        await router.push(url);
    } catch {
        // Navigation failures here are already-decided (modal is closed, user chose to
        // proceed), so nothing further to recover in the UI, just avoid an unhandled rejection.
    } finally {
        bypassGuard = false;
        busy.value = false;
    }
}

function closeModal() {
    showModal.value = false;
}

function dontSave() {
    busy.value = true;
    proceed(pendingNavUrl.value, false, true);
}

function saveChanges() {
    busy.value = true;
    proceed(pendingNavUrl.value, true, false);
}

const title = localize("You have unsaved changes. Do you want to save them before proceeding?");
const body = localize(
    "Click 'Save' to save your changes and proceed, 'Don't Save' to discard them and proceed, or 'Cancel' to return to the editor.",
);

const buttonTitles = {
    cancel: localize("Do not run proceed and return to editor"),
    dontSave: localize("Discard changes and proceed"),
    save: localize("Save changes and proceed"),
};
</script>

<template>
    <GModal footer :title="title" size="small" :show="showModal" @close="closeModal">
        <div>
            {{ body }}
        </div>
        <template v-slot:footer>
            <div class="save-changes-modal-button-container">
                <GButton tooltip :title="buttonTitles['cancel']" :disabled="busy" @click="closeModal">
                    <FontAwesomeIcon :icon="faTimes" />
                    {{ localize("Cancel") }}
                </GButton>
                <GButton tooltip :title="buttonTitles['dontSave']" color="red" :disabled="busy" @click="dontSave">
                    <FontAwesomeIcon :icon="faTrash" />
                    {{ localize("Don't Save") }}
                </GButton>
                <GButton tooltip :title="buttonTitles['save']" color="blue" :disabled="busy" @click="saveChanges">
                    <FontAwesomeIcon :icon="faSave" />
                    {{ localize("Save") }}
                </GButton>
            </div>
        </template>
    </GModal>
</template>

<style scoped lang="scss">
.save-changes-modal-button-container {
    display: flex;
    justify-content: flex-end;
    gap: var(--spacing-2);
}
</style>
