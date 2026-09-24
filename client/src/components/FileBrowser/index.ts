/**
 * FileBrowser — reusable remote file source browser components.
 *
 * Primary entry points:
 * - `RemoteFileBrowserModal`  — GModal-backed dialog for selecting remote files/directories
 * - `RemoteFileBrowserContent` — standalone inline browser (no modal wrapper)
 * - `useRemoteFileBrowser`    — headless composable for fully custom UIs
 *
 * @example
 * ```vue
 * <RemoteFileBrowserModal
 *   v-model:show="isOpen"
 *   mode="file"
 *   :multiple="true"
 *   @select="onFilesSelected" />
 * ```
 */

export { default as RemoteFileBrowserContent } from "./RemoteFileBrowserContent.vue";
export { default as RemoteFileBrowserModal } from "./RemoteFileBrowserModal.vue";
export type { SelectionItem } from "@/components/SelectionDialog/selectionTypes";
export type { RemoteFileBrowserMode } from "@/composables/useRemoteFileBrowser";
export { useRemoteFileBrowser } from "@/composables/useRemoteFileBrowser";
