<template>
    <svg class="check-draw" viewBox="0 0 36 36" fill="none" aria-hidden="true">
        <circle class="check-draw-circle" cx="18" cy="18" r="16" pathLength="100" />
        <path class="check-draw-check" d="M10.5 18.5L15.5 23.5L25.5 12.5" pathLength="100" />
    </svg>
</template>

<style lang="scss" scoped>
.check-draw {
    width: 1.1em;
    height: 1.1em;
}

// Both shapes declare pathLength="100" so this dash math is exact (100 == the whole path),
// instead of a guessed/measured length that can undershoot and leave a stray segment visible
// before the animation starts.
.check-draw-circle {
    stroke: var(--color-green-700);
    stroke-width: 2.5;
    stroke-linecap: round;
    fill: none;
    stroke-dasharray: 100;
    stroke-dashoffset: 100;
    animation: check-draw-circle 0.4s ease-out forwards;
}

.check-draw-check {
    stroke: var(--color-green-700);
    stroke-width: 3;
    stroke-linecap: round;
    stroke-linejoin: round;
    fill: none;
    stroke-dasharray: 100;
    stroke-dashoffset: 100;
    animation: check-draw-check 0.3s ease-out 0.35s forwards;
}

@keyframes check-draw-circle {
    to {
        stroke-dashoffset: 0;
    }
}

@keyframes check-draw-check {
    to {
        stroke-dashoffset: 0;
    }
}
</style>
