<!--
A thin wrapper for bootstrap form-tags.
The original b-form-tags attributes can be assigned externally and will be inherited in here

Bootstrap required that I re-create the entire default layout just to provide the following:
    1. An input change handler so we can get auto complete options
    2. A slot to customize tag rendering
-->

<template>
    <b-form-tags
        v-on="$listeners"
        v-bind="{ ...$attrs, value }"
        v-slot="{ tags, inputAttrs, inputHandlers, addTag, removeTag }"
    >
        <ul class="b-form-tags-list list-group list-group-horizontal list-unstyled d-flex flex-wrap">
            <!-- list of tags -->
            <li v-for="tag in tags" :key="tag">
                <slot name="tag" :tag="tag" :removeTag="removeTag">
                    {{ tag }}
                </slot>
            </li>
            <!-- new tag input -->
            <li class="b-form-tags-field flex-grow-1 d-flex">
                <input
                    class="b-form-tags-input w-100 flex-grow-1 bg-transparent border-0"
                    style="outline: 0px; min-width: 5rem;"
                    v-bind="{ ...$attrs, ...inputAttrs }"
                    v-on="inputHandlers"
                    v-model="localQuery"
                    tabindex="1"
                />
            </li>
        </ul>
    </b-form-tags>
</template>

<script>
import { BFormTags } from "bootstrap-vue";

export default {
    components: {
        BFormTags,
    },
    props: {
        // need to separate value from $attrs so we can watch it
        value: { type: Array, default: () => [] },
        query: { type: String, default: "" },
    },
    computed: {
        localQuery: {
            get() {
                return this.query;
            },
            set(val) {
                this.$emit("update:query", val);
            },
        },
    },
    watch: {
        value() {
            this.localQuery = "";
        },
    },
};
</script>
