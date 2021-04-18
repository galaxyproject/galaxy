<template>
    <Form :inputs="inputs" />
</template>

<script>
import Form from "components/Form/Form";
import makeSection from "./makeSection";

export default {
    components: {
        Form,
    },
    props: {
        getNode: {
            type: Function,
            required: true,
        },
        datatypes: {
            type: Array,
            required: true,
        },
    },
    computed: {
        inputs() {
            const node = this.getNode();
            const datatypes = this.datatypes;
            return makeSection(
                node,
                datatypes,
                () => {
                    alert("here");
                },
                () => {
                    alert("here");
                }
            );
        },
    },
};
</script>
