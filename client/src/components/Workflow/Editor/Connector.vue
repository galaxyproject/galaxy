<template>
    <svg class="ribbon" :style="style">
        <path class="ribbon-outer" :d="line" stroke-width="6" fill="none"></path>
        <path class="ribbon-inner" :d="line" stroke-width="4" fill="none"></path>
    </svg>
</template>
<script>
import * as d3 from "d3";

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
        cpShift: {
            type: Number,
            default: 0,
        },
        width: {
            default: 800,
            type: Number,
        },
        height: {
            default: 800,
            type: Number,
        },
        left: {
            default: 800,
            type: Number,
        },
        top: {
            default: 800,
            type: Number,
        },
    },
    computed: {
        style() {
            return {
                position: "absolute",
                width: `${this.width}px`,
                height: `${this.height}px`,
                left: `${this.left}px`,
                top: `${this.top}px`,
            };
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
                { x: this.startX + this.cpShift, y: this.startY + this.offsetStart },
                { x: this.endX - this.cpShift, y: this.endY + this.offsetEnd },
                { x: this.endX, y: this.endY + this.offsetEnd },
            ];
            console.log(data);
            return data;
        },
        path() {
            return d3.svg
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
