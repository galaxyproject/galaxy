import type { Decorator } from "@storybook/vue3-vite";
import { h, onUnmounted } from "vue";

import { getGalaxyInstance, setGalaxyInstance } from "@/app";
import { GalaxyApp } from "@/app/galaxy";

/**
 * Gives the story a legacy Galaxy instance with `config`, for code that reads
 * `getGalaxyInstance().config`, and puts back the previous one on unmount.
 */
export function withGalaxyInstance(config: Record<string, unknown> = {}): Decorator {
    return (story) => ({
        setup() {
            const previous = getGalaxyInstance();
            setGalaxyInstance(new GalaxyApp({ config: { ...config } }));
            onUnmounted(() => {
                // `setGalaxyInstance` refuses anything but a GalaxyApp, and there may have been none.
                (window as { _galaxyInstance?: unknown })._galaxyInstance = previous;
            });
        },
        render: () => h(story()),
    });
}
