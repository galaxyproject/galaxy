<template>
    <div class="rule-column-selector" v-if="!multiple || !ordered">
        <label class="d-flex justify-content-end align-items-center">
            <span class="mr-auto" v-b-tooltip.hover :title="help">{{ label }}</span>
            <div class="mr-1" v-b-tooltip.hover :title="title">
                <select2 :value="target" @input="handleInput" :multiple="multiple">
                    <option v-for="(col, index) in colHeaders" :value="index" :key="col">{{ col }}</option>
                </select2>
            </div>
            <slot></slot>
        </label>
    </div>
    <div class="rule-column-selector" v-else>
        <span>{{ label }}</span>
        <slot></slot>
        <ol>
            <li v-for="(targetEl, index) in target" :index="index" :key="targetEl" class="rule-column-selector-target">
                {{ colHeaders[targetEl] }}
                <span class="fa fa-times rule-column-selector-target-remove" @click="handleRemove(index)"></span>
                <span class="fa fa-arrow-up rule-column-selector-up" v-if="index !== 0" @click="moveUp(index)"></span>
                <span
                    class="fa fa-arrow-down rule-column-selector-down"
                    v-if="index < target.length - 1"
                    @click="moveUp(index + 1)"></span>
            </li>
            <li v-if="this.target.length < this.colHeaders.length">
                <span class="rule-column-selector-target-add" v-if="!orderedEdit">
                    <i @click="$emit('update:orderedEdit', true)">... {{ l("Assign Another Column") }}</i>
                </span>
                <span class="rule-column-selector-target-select" v-else>
                    <select2 @input="handleAdd" placeholder="Select a column">
                        <option />
                        <!-- empty option selection for placeholder -->
                        <option v-for="(col, index) in remainingHeaders" :value="index" :key="col">{{ col }}</option>
                    </select2>
                </span>
            </li>
        </ol>
    </div>
</template>

<script>
import Vue from "vue";
import _l from "utils/localization";
import Select2 from "components/Select2";
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
            default: _l("From Column"),
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
            return _l("Select a column");
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
