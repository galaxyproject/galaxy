<template>
    <FormGeneric v-bind="formConfig" />
</template>
<script>
import Query from "utils/query-string-parsing";
import { getUserPreferencesModel } from "components/User/UserPreferencesModel";
import FormGeneric from "components/Form/FormGeneric";
export default {
    components: {
        FormGeneric,
    },
    props: {
        formId: {
            type: String,
            required: true,
        },
    },
    computed: {
        formConfig() {
            const userId = Query.get("id");
            const model = getUserPreferencesModel(userId);
            return model[this.formId];
        },
    },
};
</script>
