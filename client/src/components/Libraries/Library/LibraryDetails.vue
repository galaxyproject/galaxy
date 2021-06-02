<template>
    <div>
        <h2>Library details</h2>
        <input v-model="name" />
        <input v-model="description" />
        <input v-model="synopsis" />
    </div>
</template>

<script>
import { debounce } from "underscore";
import { Library } from "../model";

const fieldDef = (fieldName) => ({
    get() {
        return this.tempValue[fieldName];
    },
    set(newFieldVal) {
        this.tempValue = this.tempValue.clone({
            [fieldName]: newFieldVal,
        });
    },
});

const makeFields = (arrFields = []) => {
    return arrFields.reduce((objFields, fieldName) => {
        return { ...objFields, [fieldName]: fieldDef(fieldName) };
    }, {});
};

export default {
    props: {
        library: { type: Library, required: true },
        debouncePeriod: { type: Number, required: false, default: 500 },
    },
    data() {
        return {
            tempValue: this.library.clone(),
        };
    },
    computed: {
        ...makeFields(["name", "description", "synopsis"]),
    },
    created() {
        this.debouncedUpdate = debounce(this.updateLibrary, this.debouncePeriod);
    },
    watch: {
        tempValue(newLibrary, oldVal) {
            if (!(oldVal && newLibrary.equals(oldVal))) {
                this.debouncedUpdate(newLibrary);
            }
        },
    },
    methods: {
        updateLibrary(newLib) {
            this.$emit("update:library", newLib);
        },
    },
};
</script>
