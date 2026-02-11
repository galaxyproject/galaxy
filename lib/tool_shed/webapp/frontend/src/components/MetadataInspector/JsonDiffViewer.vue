<script setup lang="ts">
import { computed } from "vue"
import { create } from "jsondiffpatch"
import { format as htmlFormat } from "jsondiffpatch/formatters/html"

interface Props {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    before: any
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    after: any
}
const props = defineProps<Props>()

const diffpatcher = create({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    objectHash: (obj: any) => obj.id || obj.changeset_revision || JSON.stringify(obj),
    arrays: { detectMove: true },
})

const delta = computed(() => diffpatcher.diff(props.before, props.after))

const formattedHtml = computed(() => {
    if (!delta.value) return '<div class="text-grey">No changes detected</div>'
    return htmlFormat(delta.value, props.before)
})
</script>

<template>
    <div class="json-diff-viewer" v-html="formattedHtml"></div>
</template>

<style>
/* jsondiffpatch HTML formatter styles */
.jsondiffpatch-delta {
    font-family: monospace;
    font-size: 12px;
    margin: 0;
    padding: 0;
    display: inline-block;
}
.jsondiffpatch-delta pre {
    font-family: monospace;
    font-size: 12px;
    margin: 0;
    padding: 0;
    display: inline-block;
}
ul.jsondiffpatch-delta {
    list-style-type: none;
    padding: 0 0 0 20px;
    margin: 0;
}
.jsondiffpatch-delta ul {
    list-style-type: none;
    padding: 0 0 0 20px;
    margin: 0;
}
.jsondiffpatch-added .jsondiffpatch-property-name,
.jsondiffpatch-added .jsondiffpatch-value pre,
.jsondiffpatch-modified .jsondiffpatch-right-value pre,
.jsondiffpatch-textdiff-added {
    background: #bbffbb;
}
.jsondiffpatch-deleted .jsondiffpatch-property-name,
.jsondiffpatch-deleted pre,
.jsondiffpatch-modified .jsondiffpatch-left-value pre,
.jsondiffpatch-textdiff-deleted {
    background: #ffbbbb;
    text-decoration: line-through;
}
.jsondiffpatch-unchanged,
.jsondiffpatch-movedestination {
    color: gray;
}
.jsondiffpatch-unchanged,
.jsondiffpatch-movedestination > .jsondiffpatch-value {
    transition: all 0.5s;
    -webkit-transition: all 0.5s;
    overflow-y: hidden;
}
.jsondiffpatch-unchanged-showing .jsondiffpatch-unchanged,
.jsondiffpatch-unchanged-showing .jsondiffpatch-movedestination > .jsondiffpatch-value {
    max-height: 100px;
}
.jsondiffpatch-unchanged-hidden .jsondiffpatch-unchanged,
.jsondiffpatch-unchanged-hidden .jsondiffpatch-movedestination > .jsondiffpatch-value {
    max-height: 0;
}
.jsondiffpatch-unchanged-hiding .jsondiffpatch-movedestination > .jsondiffpatch-value,
.jsondiffpatch-unchanged-hiding .jsondiffpatch-unchanged {
    max-height: 0;
}
.jsondiffpatch-unchanged-showing .jsondiffpatch-arrow,
.jsondiffpatch-unchanged-hiding .jsondiffpatch-arrow {
    display: none;
}
.jsondiffpatch-value {
    display: inline-block;
}
.jsondiffpatch-property-name {
    display: inline-block;
    padding-right: 5px;
    vertical-align: top;
}
.jsondiffpatch-property-name:after {
    content: ": ";
}
.jsondiffpatch-child-node-type-array > .jsondiffpatch-property-name:after {
    content: ": [";
}
.jsondiffpatch-child-node-type-array:after {
    content: "],";
}
li:last-child > .jsondiffpatch-child-node-type-array:after {
    content: "]";
}
.jsondiffpatch-child-node-type-object > .jsondiffpatch-property-name:after {
    content: ": {";
}
.jsondiffpatch-child-node-type-object:after {
    content: "},";
}
li:last-child > .jsondiffpatch-child-node-type-object:after {
    content: "}";
}
.jsondiffpatch-value pre:after {
    content: ",";
}
li:last-child > .jsondiffpatch-value pre:after,
.jsondiffpatch-modified > .jsondiffpatch-left-value pre:after {
    content: "";
}
.jsondiffpatch-modified > .jsondiffpatch-value {
    display: inline-block;
}
.jsondiffpatch-modified > .jsondiffpatch-right-value:before {
    content: " => ";
}
.jsondiffpatch-moved > .jsondiffpatch-value {
    display: none;
}
.jsondiffpatch-moved > .jsondiffpatch-moved-destination {
    display: inline-block;
    background: #ffffbb;
    color: #888;
}
.jsondiffpatch-moved > .jsondiffpatch-moved-destination:before {
    content: " => ";
}
ul.jsondiffpatch-textdiff {
    padding: 0;
}
.jsondiffpatch-textdiff-location {
    color: #bbb;
    display: inline-block;
    min-width: 60px;
}
.jsondiffpatch-textdiff-line {
    display: inline-block;
}
.jsondiffpatch-textdiff-line-number:after {
    content: ",";
}
.jsondiffpatch-error {
    background: red;
    color: white;
    font-weight: bold;
}
</style>
