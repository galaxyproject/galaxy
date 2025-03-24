<template>
    <div v-if="!multiple || !ordered" class="rule-column-selector">
        <label class="d-flex justify-content-end align-items-center">
            <span v-b-tooltip.hover class="mr-auto" :title="help">{{ label }}</span>
            <div v-b-tooltip.hover class="mr-1" :title="title">
                <Select2 :value="target" :multiple="multiple" @input="handleInput">
                    <option v-for="(col, index) in colHeaders" :key="col" :value="index">{{ col }}</option>
                </Select2>
            </div>
            <slot></slot>
        </label>
    </div>
    <div v-else class="rule-column-selector">
        <span>{{ label }}</span>
        <slot></slot>
        <ol>
            <li v-for="(targetEl, index) in target" :key="targetEl" :index="index" class="rule-column-selector-target">
                {{ colHeaders[targetEl] }}
                <span class="fa fa-times rule-column-selector-target-remove" @click="handleRemove(index)"></span>
                <span v-if="index !== 0" class="fa fa-arrow-up rule-column-selector-up" @click="moveUp(index)"></span>
                <span
                    v-if="index < target.length - 1"
                    class="fa fa-arrow-down rule-column-selector-down"
                    @click="moveUp(index + 1)"></span>
            </li>
            <li v-if="target.length < colHeaders.length">
                <span v-if="!orderedEdit" class="rule-column-selector-target-add">
                    <i @click="$emit('update:orderedEdit', true)">... {{ l("分配另一列") }}</i>
                </span>
                <span v-else class="rule-column-selector-target-select">
                    <Select2 placeholder="选择一列" @input="handleAdd">
                        <option />
                        <!-- empty option selection for placeholder -->
                        <option v-for="(col, index) in remainingHeaders" :key="col" :value="index">{{ col }}</option>
                    </Select2>
                </span>
            </li>
        </ol>
    </div>
</template>

<script>
import Select2 from "components/Select2";
import _l from "utils/localization";
import Vue from "vue";

export default {
    components: {
        Select2,
    },
    props: {
        target: {
            required: true,
        },
        label: {
            required: false,
            type: String,
            default: _l("从列"),
        },
        help: {
            required: false,
        },
        colHeaders: {
            type: Array,
            required: true,
        },
        multiple: {
            type: Boolean,
            required: false,
            default: false,
        },
        ordered: {
            type: Boolean,
            required: false,
            default: false,
        },
        valueAsList: {
            type: Boolean,
            required: false,
            default: false,
        },
        orderedEdit: {
            type: Boolean,
            required: false,
            default: false,
        },
    },
    computed: {
        remainingHeaders() {
            const colHeaders = this.colHeaders;
            if (!this.multiple) {
                return colHeaders;
            }
            const remaining = {};
            for (const key in colHeaders) {
                if (this.target.indexOf(parseInt(key)) === -1) {
                    remaining[key] = colHeaders[key];
                }
            }
            return remaining;
        },
        title() {
            return _l("选择列");
        },
    },
    methods: {
        handleInput(value) {
            if (this.multiple) {
                // https://stackoverflow.com/questions/262427/why-does-parseint-yield-nan-with-arraymap
                const val = value.map((idx) => parseInt(idx));
                this.$emit("update:target", val);
            } else {
                let val = parseInt(value);
                if (this.valueAsList) {
                    val = [val];
                }
                this.$emit("update:target", val);
            }
        },
        handleAdd(value) {
            // TODO: Rework add/remove here to not mutate props.
            // eslint-disable-next-line vue/no-mutating-props
            this.target.push(parseInt(value));
            this.$emit("update:orderedEdit", false);
        },
        handleRemove(index) {
            // TODO: See above.
            // eslint-disable-next-line vue/no-mutating-props
            this.target.splice(index, 1);
        },
        moveUp(value) {
            const swapVal = this.target[value - 1];
            Vue.set(this.target, value - 1, this.target[value]);
            Vue.set(this.target, value, swapVal);
        },
    },
};
</script>
