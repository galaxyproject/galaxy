<template>
    <div>
        <FormCard :title="title" icon="fa-wrench" :collapsible="false">
            <template v-slot:body>
                <Form :inputs="model.inputs" :placeholderParams="placeholderParams" />
            </template>
        </FormCard>
    </div>
</template>

<script>
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
        placeholderParams: {
            type: Object,
            default: null,
        },
    },
    data() {
        return {};
    },
    computed: {
        title() {
            return `${this.model.name} ${this.model.description} (Galaxy Version ${this.model.version})`;
        },
    },
};
</script>
