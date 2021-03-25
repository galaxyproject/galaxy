<template>
    <tr
        @mousedown="mouseIsDown = true"
        @mousemove="mouseIsDown ? (isDragging = true) : (isDragging = false)"
        @mouseup="toggleExpanded()"
    >
        <td>
            {{ codeLabel }}
        </td>
        <td v-if="expanded">
            <pre class="code">{{ codeItem }}</pre>
        </td>
        <td v-else-if="codeItem">
            <pre class="code preview">{{ codeItem }}</pre>
            <b>(Click to expand)</b>
        </td>
        <td v-else><i>empty</i></td>
    </tr>
</template>
<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

Vue.use(BootstrapVue);

export default {
    props: {
        codeLabel: String,
        codeItem: String,
    },
    data() {
        return {
            mouseIsDown: false,
            isDragging: false,
            expanded: false,
        };
    },
    methods: {
        toggleExpanded() {
            console.log(this.mouseIsDown)
            console.log(this.isDragging)
            this.mouseIsDown = false;
            if (this.codeItem && !this.isDragging) {
                this.expanded = !this.expanded;
            }
        },
    },
};
</script>
