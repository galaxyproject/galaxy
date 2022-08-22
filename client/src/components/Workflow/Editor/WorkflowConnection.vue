<template>
    <div>
        <node-connector
            :startX="connection.startX"
            :endX="connection.endX"
            :startY="connection.startY"
            :endY="connection.endY"
            :cpShift="connection.cpShift"
            :width="connection.width"
            :height="connection.height"
            :left="connection.left"
            :top="connection.top"
            v-for="connection in connections"
            :key="connection.key" />
    </div>
</template>
<script>
import $ from "jquery";

// import Connector from "./modules/connector";
import NodeConnector from "./Connector.vue";

export default {
    components: {
        NodeConnector,
    },
    props: {
        canvasManager: {
            type: Object,
            required: true,
        },
        step: {
            type: Object,
            required: true,
        },
        getManager: {
            type: Function,
            required: true,
        },
    },
    data() {
        return {
            handleMarginX: 8,
            canvasExtra: 100,
            zIndex: 1000,
            cpFactor: 10,
        };
    },
    methods: {
        getCoordinates(outputTerminal, inputTerminal) {
            // Find the position of each handle
            const canvasContainer = $("#canvas-container");
            const relativeLeft = (e) =>
                ($(e).offset().left - canvasContainer.offset().left) / this.canvasManager.canvasZoom +
                this.handleMarginX;
            const relativeTop = (e) =>
                ($(e).offset().top - canvasContainer.offset().top) / this.canvasManager.canvasZoom +
                0.5 * $(e).height();
            let startX = relativeLeft(outputTerminal.element);
            let startY = relativeTop(outputTerminal.element);
            let endX = relativeLeft(inputTerminal.element);
            let endY = relativeTop(inputTerminal.element);

            // Calculate canvas area
            const canvas_min_x = Math.min(startX, endX);
            const canvas_max_x = Math.max(startX, endX);
            const canvas_min_y = Math.min(startY, endY);
            const canvas_max_y = Math.max(startY, endY);
            const canvas_left = canvas_min_x - this.canvasExtra;
            const canvas_top = canvas_min_y - this.canvasExtra;
            const width = canvas_max_x - canvas_min_x + 2 * this.canvasExtra;
            const height = canvas_max_y - canvas_min_y + 2 * this.canvasExtra;
            const cpShift = Math.min(
                Math.max(Math.abs(canvas_max_y - canvas_min_y) / 2, this.cpFactor),
                3 * this.cpFactor
            );

            // Adjust points to be relative to the canvas
            startX -= canvas_left;
            startY -= canvas_top;
            endX -= canvas_left;
            endY -= canvas_top;

            return { startX, startY, endX, endY, cpShift, width, height, left: canvas_left, top: canvas_top };
        },
    },
    computed: {
        connections() {
            const rval = [];
            if (!this.step.input_connections) {
                return rval;
            }
            Object.entries(this.step.input_connections).forEach(([k, v]) => {
                if (v) {
                    const source = `node-${this.step.id}-input-${k}`;
                    const inputTerminal = this.$store.getters.getInputTerminal(source);
                    if (!Array.isArray(v)) {
                        v = [v];
                    }
                    v.forEach((x) => {
                        const target = `node-${x.id}-output-${x.output_name}`;
                        let outputTerminal = this.$store.getters.getOutputTerminal(target);
                        console.log(outputTerminal);
                        if (inputTerminal && outputTerminal) {
                            const coordinates = this.getCoordinates(outputTerminal, inputTerminal);
                            console.log(coordinates);
                            coordinates.key = `${source}-${target}`;
                            rval.push(coordinates);
                        }
                    });
                }
            });
            return rval;
        },
    },
};
</script>
