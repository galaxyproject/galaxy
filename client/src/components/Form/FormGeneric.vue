<template>
    <UrlDataProvider v-slot="{ result: config, loading }" :url="url" @error="onError">
        <div v-if="!loading" :id="id">
            <b-alert v-if="config.message" :variant="configMessageVariant(config)" show>
                {{ config.message }}
            </b-alert>
            <b-alert v-if="messageText" :variant="messageVariant" show>
                {{ messageText }}
            </b-alert>
            <FormCard :title="configTitle(config)" :icon="configIcon(config)">
                <template v-slot:body>
                    <FormDisplay :inputs="config.inputs" :replace-params="replaceParams" @onChange="onChange" />
                </template>
            </FormCard>
            <div class="mt-3">
                <b-button id="submit" variant="primary" class="mr-1" @click="onSubmit()">
                    <span :class="submitIconClass" />{{ submitTitle | l }}
                </b-button>
                <b-button v-if="cancelRedirect" @click="onCancel()">
                    <span class="mr-1 fa fa-times" />{{ "Cancel" | l }}
                </b-button>
            </div>
        </div>
    </UrlDataProvider>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import { submitData } from "./services";
import { UrlDataProvider } from "components/providers/UrlDataProvider";
import { visitInputs } from "components/Form/utilities";
import FormCard from "components/Form/FormCard";
import FormDisplay from "components/Form/FormDisplay";

export default {
    components: {
        FormCard,
        FormDisplay,
        UrlDataProvider,
    },
    props: {
        id: {
            type: String,
            default: null,
        },
        title: {
            type: String,
            default: null,
        },
        icon: {
            type: String,
            default: null,
        },
        submitIcon: {
            type: String,
            default: "fa-save",
        },
        submitTitle: {
            type: String,
            default: "Save",
        },
        cancelRedirect: {
            type: String,
            default: null,
        },
        url: {
            type: String,
            required: true,
        },
        redirect: {
            type: String,
            default: null,
        },
    },
    data() {
        return {
            messageText: null,
            messageVariant: null,
            formData: {},
            replaceParams: null,
        };
    },
    computed: {
        submitIconClass() {
            return `mr-1 fa ${this.submitIcon}`;
        },
    },
    methods: {
        configTitle(options) {
            return this.title || options.title;
        },
        configIcon(options) {
            return this.icon || options.icon;
        },
        configMessageVariant(options) {
            return options.status || "warning";
        },
        onChange(formData) {
            this.formData = formData;
        },
        onCancel() {
            window.location = `${getAppRoot()}${this.cancelRedirect}`;
        },
        onSubmit() {
            submitData(this.url, this.formData).then((response) => {
                let params = {};
                if (response.id) {
                    params.id = response.id;
                } else {
                    params = {
                        message: response.message,
                        status: "success",
                        persistent: false,
                    };
                }
                if (this.redirect) {
                    const urlParams = new URLSearchParams(params);
                    window.location = `${getAppRoot()}${this.redirect}?${urlParams.toString()}`;
                } else {
                    const replaceParams = {};
                    visitInputs(response.inputs, (input, name) => {
                        replaceParams[name] = input.value;
                    });
                    this.replaceParams = replaceParams;
                    this.showMessage(response.message);
                }
            }, this.onError);
        },
        onError(error) {
            this.showMessage(error || `Failed to load resource ${this.url}.`, "danger");
        },
        showMessage(message, variant = "success") {
            this.messageText = message;
            this.messageVariant = variant;
            document.querySelector(".center-panel").scrollTop = 0;
        },
    },
};
</script>
