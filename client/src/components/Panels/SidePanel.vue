<template>
    <div :id="side" class="unified-panel-outer-wrap" :style="styles">
        <slot name="panel">
            <component :is="currentPanel" v-bind="currentPanelProperties" />
        </slot>
        <div class="unified-panel-footer">
            <div
                class="panel-collapse"
                :class="{
                    left: side === 'left',
                    right: side === 'right',
                    hidden: !show,
                }"
                @click="toggle" />
            <div class="drag" @mousedown="dragHandler" />
        </div>
    </div>
</template>

<script>
const MIN_PANEL_WIDTH = 160;
const MAX_PANEL_WIDTH = 800;

export default {
    name: "SidePanel",
    props: ["currentPanel", "currentPanelProperties", "side"],
    data() {
        return {
            show: true,
            width: 288,
        };
    },
    computed: {
        styles() {
            const styles = {};
            styles[this.side] = this.show ? "0" : `-${this.width}px`;
            styles["width"] = this.width + "px";
            return styles;
        },
    },
    methods: {
        dragHandler(e) {
            const self = this;
            const draggingLeft = this.side === "left";

            const initialX = e.pageX;
            const initialWidth = this.width;

            function move(e) {
                const delta = e.pageX - initialX;
                let newWidth = draggingLeft ? initialWidth + delta : initialWidth - delta;
                newWidth = Math.min(MAX_PANEL_WIDTH, Math.max(MIN_PANEL_WIDTH, newWidth));
                self.resize(newWidth);
            }

            function moved() {
                document.getElementById("dd-helper").style.display = "none";
                document.getElementById("dd-helper").removeEventListener("mousemove", move);
                document.getElementById("dd-helper").removeEventListener("mouseup", moved);
            }

            document.getElementById("dd-helper").style.display = "block";
            document.getElementById("dd-helper").addEventListener("mousemove", move);
            document.getElementById("dd-helper").addEventListener("mouseup", moved);
        },
        resize(newWidth) {
            this.width = newWidth;
            document.getElementById("center").style[this.side] = newWidth + "px";
        },
        toggle() {
            this.show = !this.show;

            if (this.show) {
                document.getElementById("center").style.transition = `${this.side} 200ms linear`;
                document.getElementById("center").style[this.side] = this.width + "px";
                setTimeout(() => {
                    document.getElementById("center").style.transition = "";
                }, 250);
            } else {
                document.getElementById("center").style.transition = `${this.side} 200ms linear`;
                document.getElementById("center").style[this.side] = "0";
                setTimeout(() => {
                    document.getElementById("center").style.transition = "";
                }, 250);
            }
        },
        hide(timeout = 250) {
            this.show = false;
            document.getElementById("center").style.transition = `${this.side} 200ms linear`;
            document.getElementById("center").style[this.side] = "0";
            setTimeout(() => {
                document.getElementById("center").style.transition = "";
            }, timeout);
        },
    },
};
</script>

<style scoped>
.collapsed {
    position: absolute;
    bottom: 0;
    margin: 0;
}

.unified-panel-outer-wrap {
    transition-property: left, right;
    transition-duration: 200ms;
    transition-timing-function: linear;
}
</style>
