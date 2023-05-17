import { ref } from "vue";

const globalSnap = ref(false);
const snapGrid = 10;

export function useMagnetSnap() {
    const snappedPosition = (position: { x: number; y: number }) => {
        if (globalSnap.value) {
            return {
                x: Math.round(position.x / snapGrid) * snapGrid,
                y: Math.round(position.y / snapGrid) * snapGrid,
            };
        } else {
            return {
                x: position.x,
                y: position.y,
            };
        }
    };

    return {
        snappedPosition,
        active: globalSnap,
    };
}
