const OFFSET_RANGE = 100;

export function defaultPosition(rootOffset, transform) {
    const left = transform.x + (rootOffset.width / 2 + offsetVaryPosition() * transform.k);
    const top = transform.y + (rootOffset.height / 2 + offsetVaryPosition() * transform.k);
    return { left, top };
}

const offsetVaryPosition = () => {
    return Math.floor(Math.random() * OFFSET_RANGE);
};
