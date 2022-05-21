<template>
    <div>
        <b-form-group
            v-for="(field, fieldName) in fieldDefs"
            :key="fieldName"
            :label="field.label || fieldName"
            :label-for="'config-' + fieldName"
            label-cols-lg="3"
            :state="config.fieldValid(fieldName)"
            :invalid-feedback="config.errorMessage(fieldName)">
            <masked-input
                :id="'config-' + fieldName"
                v-model="config[fieldName]"
                :mask="field.mask"
                :placeholder="field.placeholder"
                :maxlength="field.maxlength || Math.Infinity"
                :state="config.fieldValid(fieldName)"
                trim />
        </b-form-group>
    </div>
</template>

<script>
import MaskedInput from "components/MaskedInput";

export default {
    components: {
        MaskedInput,
    },
    props: {
        value: { type: Object, required: true },
    },
    computed: {
        config() {
            return this.value;
        },
        fieldDefs() {
            return this.value.constructor.fields;
        },
    },
};
</script>
