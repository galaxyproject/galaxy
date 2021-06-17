<template>
    <div>
        <FormCard :title="title" icon="fa-wrench">
            <template v-slot:body>
                <Form :inputs="model.inputs" />
            </template>
        </FormCard>
    </div>
</template>

<script>
import { getGalaxyInstance } from "app";
import Form from "components/Form/Form";
import FormCard from "components/Form/FormCard";

export default {
    components: {
        Form,
        FormCard,
    },
    props: {
        model: {
            type: Object,
            required: true,
        },
    },
    data() {
        return {};
    },
    created() {
        console.log(this.model);
    },
    computed: {
        title() {
            return `${this.model.name} ${this.model.description} (Galaxy Version ${this.model.version})`;
        },
    },
    methods: {},
};
</script>
