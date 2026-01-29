<template>
    <tr>
        <td>
            <span v-if="helpUri">
                <HelpText :uri="helpUri" :text="codeLabel" />
            </span>
            <span v-else>
                {{ codeLabel }}
            </span>
        </td>
        <td v-if="codeItem">
            <b-row align-v="center">
                <b-col cols="11">
                    <pre :class="codeClass">{{ codeItem }}</pre>
                </b-col>
                <b-col
                    v-b-tooltip.hover
                    class="nopadding pointer"
                    :title="`click to ${action}`"
                    @mousedown="mouseIsDown = true"
                    @mousemove="mouseIsDown ? (mouseMoved = true) : (mouseMoved = false)"
                    @mouseup="toggleExpanded()">
                    <FontAwesomeIcon :icon="iconClass" />
                </b-col>
            </b-row>
        </td>
        <td v-else><i>empty</i></td>
    </tr>
</template>
<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCompressAlt, faExpandAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import HelpText from "components/Help/HelpText";

library.add(faCompressAlt, faExpandAlt);
export default {
    components: {
        FontAwesomeIcon,
        HelpText,
    },
    props: {
        codeLabel: String,
        codeItem: String,
        helpUri: String,
    },
    data() {
        return {
            mouseIsDown: false,
            mouseMoved: false,
            expanded: false,
            lastPos: 0,
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
    updated() {
        try {
            var codeDiv = this.$el.querySelector(".code");
            if (codeDiv.scrollTop + codeDiv.offsetHeight >= this.lastPos - 5) {
                // scroll is at the bottom
                codeDiv.scrollTop = codeDiv.scrollHeight;
            }
            this.lastPos = codeDiv.scrollHeight;
        } catch (exception) {
            console.debug("Code div is not present");
        }
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
.code {
    max-height: 50em;
    overflow: auto;
}
</style>
