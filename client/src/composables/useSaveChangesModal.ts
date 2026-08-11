import { type Ref, ref } from "vue";
import type VueRouter from "vue-router";
import { onBeforeRouteLeave, onBeforeRouteUpdate } from "vue-router/composables";

/**
 * Composable that works with `SaveChangesModal.vue` to intercept in-app navigation when
 * there are changes to save and the user can decide whether to cancel navigation, discard changes and proceed,
 * or save changes and proceed.
 *
 * **IMPORTANT:** this composable does not render anything!
 * The caller MUST render `client/src/components/Workflow/Editor/SaveChangesModal.vue` in
 * its template, taking the two returned refs and the handler as props/events, e.g.:
 *
 * ```vue
 * <SaveChangesModal
 *     :show-modal.sync="showSaveChangesModal"
 *     :nav-url="pendingNavUrl"
 *     :append-version="false"
 *     @on-proceed="handleSaveChangesProceed" />
 * ```
 *
 * Without that template usage, `isDirty` navigation is blocked (`next(false)`) but the
 * user is never given a way to proceed as the guard would strand them on the page.
 *
 * Covers in-app navigation only (Vue Router's `onBeforeRouteLeave`/`onBeforeRouteUpdate`).
 * Page refresh/tab close/URL bar navigation isn't interceptable by Vue Router and needs
 * its own `beforeunload` listener in the caller -- keep it separate from this composable so
 * it never races with the monkeypatched `router.push()` confirmation check
 * (`client/src/entry/analysis/router-push.js`), which runs ahead of these guards.
 */
export function useSaveChangesModal(isDirty: Ref<boolean>, onSave: () => Promise<unknown>, router: VueRouter) {
    // TODO: When/If `client/src/components/Workflow/Editor/Index.vue` is modernized to use this composable,
    // that also includes a `appendVersion` prop which might be needed here. Maybe `extraProps` or something...
    // Then, also move the `SaveChangesModal.vue` component to a more generic location, not under `Workflow/Editor`.

    const showSaveChangesModal = ref(false);
    const pendingNavUrl = ref("");

    /** True while we're pushing a navigation the user already resolved via the modal. */
    let bypassGuard = false;

    function guard(to: { fullPath: string }, _from: unknown, next: (arg?: false) => void) {
        if (isDirty.value && !bypassGuard) {
            pendingNavUrl.value = to.fullPath;
            showSaveChangesModal.value = true;
            next(false);
        } else {
            next();
        }
    }

    onBeforeRouteLeave(guard);
    onBeforeRouteUpdate(guard);

    async function handleSaveChangesProceed(url: string, forceSave: boolean, ignoreChanges: boolean) {
        showSaveChangesModal.value = false;
        if (forceSave) {
            await onSave();
        } else if (!ignoreChanges) {
            return;
        }
        bypassGuard = true;
        await router.push(url);
        bypassGuard = false;
    }

    return {
        showSaveChangesModal,
        pendingNavUrl,
        handleSaveChangesProceed,
    };
}
