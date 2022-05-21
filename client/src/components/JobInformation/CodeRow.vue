<template>
    <tr
        v-b-tooltip.hover
        :title="`click to ${action}`"
        @mousedown="mouseIsDown = true"
        @mousemove="mouseIsDown ? (mouseMoved = true) : (mouseMoved = false)"
        @mouseup="toggleExpanded()">
        <td>
            {{ codeLabel }}
        </td>
        <td v-if="codeItem">
            <b-row align-v="center">
                <b-col cols="11">
                    <pre :class="codeClass">{{ codeItem }}</pre>
                </b-col>
                <b-col class="nopadding pointer">
                    <font-awesome-icon :icon="iconClass" />
                </b-col>
            </b-row>
        </td>
        <td v-else><i>empty</i></td>
    </tr>
</template>
<script>
import { faCompressAlt, faExpandAlt } from "@fortawesome/free-solid-svg-icons";
import { library } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

library.add(faCompressAlt, faExpandAlt);
export default {
    components: {
        FontAwesomeIcon,
    },
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
            return this.expanded ? ["fas", "compress-alt"] : ["fas", "expand-alt"];
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

<style scoped>
.pointer {
    cursor: pointer;
}
.nopadding {
    padding: 0;
    margin: 0;
}
</style>
