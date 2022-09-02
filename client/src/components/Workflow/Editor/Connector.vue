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
        position: {
            type: Object,
            required: true,
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
        offsetStart() {
            return 0;
        },
        offsetEnd() {
            return 0;
        },
        lineData() {
            const data = [
                { x: this.position.startX, y: this.position.startY + this.offsetStart },
                { x: this.position.startX + this.lineShift, y: this.position.startY + this.offsetStart },
                { x: this.position.endX - this.lineShift, y: this.position.endY + this.offsetEnd },
                { x: this.position.endX, y: this.position.endY + this.offsetEnd },
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
