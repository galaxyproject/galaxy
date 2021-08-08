<template>
    <UrlDataProvider :url="url" v-slot="{ result: config, loading }" @error="onError">
        <div :id="id" v-if="!loading">
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
            <div class="mt-2">
                <b-button id="submit" variant="primary" class="mr-1" @click="onSubmit()">
                    <span :class="submitIcon(config)" />{{ submitTitle(config) | l }}
                </b-button>
                <b-button v-if="config.cancel_redirect" @click="onCancel(config)">
                    <span :class="cancelIcon(config)" />{{ cancelTitle(config) | l }}
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
    props: {
        id: {
            type: String,
            required: false,
        },
        title: {
            type: String,
            required: false,
        },
        icon: {
            type: String,
            required: false,
        },
        url: {
            type: String,
            required: true,
        },
        redirect: {
            type: String,
            required: true,
        },
    },
    components: {
        FormCard,
        FormDisplay,
        UrlDataProvider,
    },
    data() {
        return {
            messageText: null,
            messageVariant: null,
            formData: {},
            replaceParams: null,
        };
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
        cancelTitle(options) {
            return options.cancel_title || "Cancel";
        },
        cancelIcon(options) {
            const icon = options.cancel_icon || "fa-times";
            return `mr-1 fa ${icon}`;
        },
        submitTitle(options) {
            return options.submit_title || "Save";
        },
        submitIcon(options) {
            const icon = options.submit_icon || "fa-save";
            return `mr-1 fa ${icon}`;
        },
        onChange(formData) {
            this.formData = formData;
        },
        onCancel(options) {
            window.location = `${getAppRoot()}${options.cancel_redirect}`;
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
