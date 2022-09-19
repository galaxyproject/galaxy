<template>
    <b-row>
        <b-col class="form-color-input">
            <b-form-input :id="id" v-model="currentValue" class="cursor-pointer" type="color" size="sm" />
        </b-col>
        <b-col class="pl-0">
            <label class="pt-1 cursor-pointer" :for="id">Select a color</label>
        </b-col>
    </b-row>
</template>

<script>
export default {
    props: {
        value: {
            type: String,
            default: "",
        },
        id: {
            type: String,
            required: true,
        },
    },
    computed: {
        currentValue: {
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
<style scoped>
.form-color-input {
    max-width: 3.6rem;
}
</style>
