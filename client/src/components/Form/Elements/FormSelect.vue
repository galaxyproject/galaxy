<template>
    <div>
        <b-alert
            class="mt-2"
            v-if="errorMessage"
            :show="dismissCountDown"
            variant="info"
            @dismissed="dismissCountDown = 0"
        >
            {{ errorMessage }}
        </b-alert>
        <b-row align-v="center">
            <b-col>
                <multiselect v-model="currentValue" 
                    :options="optArray"
                    label="label"
                    track-by="value" 
                    />
                    {{ currentValue }}
            </b-col>
        </b-row>
    </div>
</template>

<script>

import Multiselect from 'vue-multiselect'

export default {
    components: {
        Multiselect
    },
    props: {
        value: {
            required: true,
        },
        default_value: {
            type: String,
            required: true,
        },
        options: {
            type: Array,
            required: true,
            default: undefined,
        },
    },
    data() {
        return {
            errorMessage: "",
        };
    },
    computed: {
        optArray() {
            const formattedOptions = []
            for (let i = 0, len = this.options.length; i < len; i++){
                formattedOptions[i] = {"label": this.options[i][0], "value": this.options[i][1], "default": this.options[i][2]}
            }
            return formattedOptions
        },
        currentValue: {
            get() {
                return this.value
            },
            set(val) {
                this.$emit("input", val.value);
            },
        },
    },
    // methods: {
    //     onInputChange(value) {
    //         // hide error message after value has changed
    //         this.currentValue = value
    //         console.log('helloworld"')
    //         this.$emit("input", this.currentValue.value);
    //     },
    //     onSelectItem(currentValue) {
    //         this.$emit("update:currentValue", currentValue);
    //     },
    // },
    created() {
        this.currentValue = this.optArray.find(element => element.value == this.default_value) || this.optArray[0];
    },
};
</script>