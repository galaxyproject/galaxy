import { useEventListener } from "@vueuse/core";
import { type Ref, watch } from "vue";

import { useWorkflowStores } from "@/composables/workflowStores";

import { vecSnap } from "../modules/geometry";

/**
 * Common functionality required for handling a user resizable element.
 * `resize: both` needs to be set on the elements style, this composable
 * will not apply it.
 *
 * @param target Element to attach to
 * @param sizeControl External override for the size. Will override the user resize when set
 * @param onResized Function to run when the target element receives a mouseup event, and it's size changed
 */
export function useResizable(
    target: Ref<HTMLElement | undefined | null>,
    sizeControl: Ref<[number, number]>,
    onResized: (size: [number, number]) => void
) {
    // override user resize if size changes externally
    watch(
        () => sizeControl.value,
        ([width, height]) => {
            const element = target.value;

            if (element) {
                element.style.width = `${width}px`;
                element.style.height = `${height}px`;
            }
        }
    );

    let prevWidth = sizeControl.value[0];
    let prevHeight = sizeControl.value[1];

    const { toolbarStore } = useWorkflowStores();
    useEventListener(target, "mouseup", () => {
        const element = target.value;

        if (element) {
            const width = element.offsetWidth;
            const height = element.offsetHeight;

            if (prevWidth !== width || prevHeight !== height) {
                if (toolbarStore.snapActive) {
                    onResized(vecSnap([width, height], toolbarStore.snapDistance));
                } else {
                    onResized([width, height]);
                }

                prevWidth = width;
                prevHeight = height;
            }
        }
    });
}
