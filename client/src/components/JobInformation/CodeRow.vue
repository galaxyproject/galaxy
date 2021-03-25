<template>
    <tr
        @mousedown="mouseIsDown = true"
        @mousemove="mouseIsDown ? (mouseMoved = true) : (mouseMoved = false)"
        @mouseup="toggleExpanded()"
    >
        <td>
            {{ codeLabel }}
        </td>
        <td v-if="codeItem">
            <pre @click.stop :class="codeClass">{{ codeItem }}</pre>
            <i :class="iconClass" />
            <b>Click to {{ action }}</b>
        </td>
        <td v-else><i>empty</i></td>
    </tr>
</template>
<script>
export default {
    props: {
        codeLabel: String,
        codeItem: String,
    },
    data() {
        return {
            mouseIsDown: false,
            mouseMoved: false,
            expanded: false,
        };
    },
    computed: {
        action() {
            return this.expanded ? "collapse" : "expand";
        },
        codeClass() {
            return this.expanded ? "code" : "code preview";
        },
        iconClass() {
            return this.expanded ? "fa fa-minus" : "fa fa-plus";
        },
    },
    methods: {
        toggleExpanded() {
            this.mouseIsDown = false;
            if (this.codeItem && !this.mouseMoved) {
                this.expanded = !this.expanded;
            }
        },
    },
};
</script>
