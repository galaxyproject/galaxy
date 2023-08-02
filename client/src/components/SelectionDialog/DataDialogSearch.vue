<template>
    <GInputGroup>
        <GInput v-model="filter" :placeholder="placeholder" />
        <GInputGroupAppend>
            <GButton :disabled="!filter" @click="filter = ''">
                <i class="fa fa-times" />
            </GButton>
        </GInputGroupAppend>
    </GInputGroup>
</template>

<script>
import { GButton, GInput, GInputGroup, GInputGroupAppend } from "@/component-library";

export default {
    components: {
        GButton,
        GInput,
        GInputGroup,
        GInputGroupAppend,
    },
    props: {
        value: {
            type: String,
            default: null,
        },
        title: {
            type: String,
            default: "",
        },
    },
    computed: {
        placeholder() {
            return `Type to Search ${this.title}`;
        },
        filter: {
            get() {
                return this.value;
            },
            set(val) {
                this.$emit("input", val);
            },
        },
    },
};
</script>
