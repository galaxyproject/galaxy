<template>
    <g class="ribbon">
        <path class="ribbon-outer" :d="line" stroke-width="6" fill="none"></path>
        <path class="ribbon-inner" :d="line" stroke-width="4" fill="none"></path>
    </g>
</template>
<script>
import { svg } from "d3";

export default {
    props: {
        id: {
            type: String,
            required: false,
        },
        startX: {
            type: Number,
        },
        startY: {
            type: Number,
        },
        endX: {
            type: Number,
        },
        endY: {
            type: Number,
        },
    },
    data() {
        return {
            lineShift: 30,
        };
    },
    beforeDestroy() {
        console.log("Destroying connector");
        // this.terminal.destroy();
    },
    computed: {
        left() {
            return Math.min(this.startX, this.endX);
        },
        top() {
            return Math.max(this.startY, this.endY);
        },
        offsetStart() {
            return 0;
        },
        offsetEnd() {
            return 0;
        },
        lineData() {
            const data = [
                { x: this.startX, y: this.startY + this.offsetStart },
                { x: this.startX + this.lineShift, y: this.startY + this.offsetStart },
                { x: this.endX - this.lineShift, y: this.endY + this.offsetEnd },
                { x: this.endX, y: this.endY + this.offsetEnd },
            ];
            return data;
        },
        path() {
            return svg
                .line()
                .x(function (d) {
                    return d.x;
                })
                .y(function (d) {
                    return d.y;
                })
                .interpolate("basis");
        },
        line() {
            return this.path(this.lineData);
        },
    },
};
</script>
