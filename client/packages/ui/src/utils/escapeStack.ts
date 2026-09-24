// Open popovers that Escape dismisses, most recently opened last, so one key press closes only the top one.
export interface EscapeLayer {
    // False while the layer cannot take the key, e.g. behind a modal dialog, so the next one down gets it.
    canHandle: () => boolean;
}

const layers: EscapeLayer[] = [];

export function closeEscapeLayer(layer: EscapeLayer) {
    const index = layers.indexOf(layer);
    if (index !== -1) {
        layers.splice(index, 1);
    }
}

export function openEscapeLayer(layer: EscapeLayer) {
    closeEscapeLayer(layer);
    layers.push(layer);
}

export function isTopEscapeLayer(layer: EscapeLayer) {
    for (let i = layers.length - 1; i >= 0; i--) {
        if (layers[i]!.canHandle()) {
            return layers[i] === layer;
        }
    }
    return false;
}
