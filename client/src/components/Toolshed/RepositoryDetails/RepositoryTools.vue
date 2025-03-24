<template>
    <table v-if="tools" class="table table-borderless">
        <tbody>
            <tr v-if="canExpand && expanded" class="bg-transparent">
                <td :class="clsFirstColumn">
                    <a href="javascript:void(0)" role="button" @click.stop.prevent="onExpand">
                        <span class="fa fa-angle-double-up" />
                        <span>显示更少</span>
                    </a>
                </td>
                <td :class="clsSecondColumn" />
            </tr>
            <tr v-for="tool in visibleTools" :key="tool.guid" :class="clsRow">
                <td :class="clsFirstColumn">
                    {{ tool.id }}
                </td>
                <td :class="clsSecondColumn">
                    {{ tool.version }}
                </td>
            </tr>
            <tr v-if="canExpand && !expanded" class="bg-transparent">
                <td :class="clsFirstColumn">
                    <a href="javascript:void(0)" role="button" @click.stop.prevent="onExpand">
                        <span class="fa fa-angle-double-down" />
                        <span>显示更多</span>
                    </a>
                </td>
                <td :class="clsSecondColumn" />
            </tr>
        </tbody>
    </table>
    <span v-else>-</span>
</template>
<script>
export default {
    props: {
        tools: {
            type: Array,
            required: true,
        },
    },
    data() {
        return {
            clsExpanded: "bg-transparent border-bottom",
            clsCollapsed: "bg-transparent",
            clsFirstColumn: "p-0 w-50 text-left",
            clsSecondColumn: "p-0 w-50 text-center",
            expanded: false,
            preview: 2,
        };
    },
    computed: {
        clsRow() {
            return this.expanded ? this.clsExpanded : this.clsCollapsed;
        },
        canExpand() {
            return this.tools && this.tools.length > this.preview;
        },
        visibleTools() {
            if (this.canExpand && !this.expanded) {
                return this.tools.slice(0, this.preview);
            }
            return this.tools;
        },
    },
    methods: {
        onExpand() {
            this.expanded = !this.expanded;
        },
    },
};
</script>
