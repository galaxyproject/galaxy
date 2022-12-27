<template>
    <div ref="overview" class="workflow-overview" :style="style" aria-hidden="true">
        <div class="workflow-overview-body" @click="onClick">
            <svg width="100%" height="100%" :viewBox="viewBox">
                <MinimapNode
                    v-for="node of Object.values(nodes)"
                    :key="node.id"
                    class="mini-node"
                    :node="node"
                    :step="steps[node.id]" />
                <rect
                    ref="rect"
                    class="viewport"
                    :x="visible.x"
                    :y="visible.y"
                    :width="visible.width"
                    :height="visible.height"
                    stroke-width="1%"
                    rx="1%"
                    fill="white"
                    fill-opacity="0.5"
                    @click.stop />
            </svg>
        </div>
    </div>
</template>
<script>
import MinimapNode from "./MinimapNode.vue";
import { computed, reactive, ref } from "vue";
import { useDraggable } from "@vueuse/core";
import { storeToRefs } from "pinia";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";

export default {
    components: {
        MinimapNode,
    },
    props: {
        steps: {
            type: Object,
            required: true,
        },
        width: {
            type: Number,
            default: 200,
        },
        height: {
            type: Number,
            default: 200,
        },
        scale: {
            type: Number,
            default: 1,
        },
        pan: {
            type: Object,
            default() {
                return { x: 0, y: 0 };
            },
        },
        rootOffset: {
            type: Object,
        },
    },
    setup(props, { emit }) {
        const overview = ref(null);
        const overviewPosition = reactive(useDraggable(overview, { preventDefault: true, exact: true }));
        const size = ref(parseInt(localStorage.getItem("overview-size")) || 150);
        const visible = computed(() => {
            const x = props.pan.x / -props.scale;
            const y = props.pan.y / -props.scale;
            const width = props.rootOffset.width / props.scale;
            const height = props.rootOffset.bottom / props.scale;
            const rval = { x, y, width, height };
            return rval;
        });
        const { nodes } = storeToRefs(useWorkflowStateStore());
        const bounds = computed(() => {
            let left = props.pan.x * -1;
            let right = props.rootOffset.width;
            let top = props.pan.y * -1;
            let bottom = props.rootOffset.bottom;
            let p;
            Object.values(props.steps).forEach((step) => {
                const node = nodes.value[step.id];
                // TODO: something here isn't fully "reactive", this breaks when HMR kicks in,
                // because position is not a reactive property of node (and I guess it shouldn't be?)
                p = node.position;
                if (p) {
                    left = Math.min(left, step.position.left);
                    right = Math.max(right, p.right);
                    top = Math.min(top, step.position.top);
                    bottom = Math.max(bottom, p.bottom);
                }
            });

            return {
                left: left / props.scale,
                right: right / props.scale,
                top: top / props.scale,
                bottom: bottom / props.scale,
            };
        });
        const scaleFactorX = computed(() => {
            return (bounds.value.right - bounds.value.left) / size.value;
        });
        const scaleFactorY = computed(() => {
            return (bounds.value.bottom - bounds.value.top) / size.value;
        });
        const rect = ref(null);
        let startX = null;
        let startY = null;
        const rectPosition = reactive(
            useDraggable(rect, {
                onStart: (position, event) => {
                    startX = event.clientX;
                    startY = event.clientY;
                },
                onMove: (position, event) => {
                    const offsetX = event.clientX - startX;
                    const offsetY = event.clientY - startY;
                    emit("pan-by", { x: -offsetX * scaleFactorX.value, y: -offsetY * scaleFactorY.value });
                    startX = event.clientX;
                    startY = event.clientY;
                },
            })
        );
        return {
            overview,
            overviewPosition,
            rect,
            rectPosition,
            size,
            visible,
            bounds,
            scaleFactorX,
            scaleFactorY,
            startX,
            startY,
            nodes,
        };
    },
    data() {
        return {
            maxSize: 300,
            minSize: 50,
        };
    },
    computed: {
        style() {
            if (this.overviewPosition.x) {
                let newSize = Math.max(
                    this.rootOffset.right - this.overviewPosition.x,
                    this.rootOffset.bottom - this.overviewPosition.y
                );
                if (newSize > this.maxSize) {
                    newSize = this.maxSize;
                } else if (newSize < this.minSize) {
                    newSize = this.minSize;
                }
                if (!this.overviewPosition.isDragging) {
                    localStorage.setItem("overview-size", newSize);
                }
                this.setSize(newSize);
            }
            return { width: `${this.size}px`, height: `${this.size}px` };
        },
        viewBox() {
            return `${this.bounds.left} ${this.bounds.top} ${this.bounds.right} ${this.bounds.bottom}`;
        },
    },
    methods: {
        setSize(size) {
            this.size = size;
        },
        onClick(e) {
            const x = e.offsetX * this.scaleFactorX;
            const y = e.offsetY * this.scaleFactorY;
            this.$emit("moveTo", { x, y });
        },
    },
};
</script>
