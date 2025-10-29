<template>
    <UrlDataProvider v-slot="{ result: config, loading }" :url="url" @error="onError">
        <div v-if="!loading" :id="id">
            <b-alert v-if="config.message" :variant="configMessageVariant(config)" show>
                {{ config.message }}
            </b-alert>
            <b-alert v-if="messageText" :variant="messageVariant" show dismissible @dismissed="messageText = null">
                {{ messageText }}
            </b-alert>
            <FormCard :title="configTitle(config)" :icon="configIcon(config)">
                <template v-slot:body>
                    <FormDisplay :inputs="config.inputs" :replace-params="replaceParams" @onChange="onChange" />
                </template>
            </FormCard>
            <div class="mt-3">
                <GButton id="submit" color="blue" class="mr-1" :disabled="submitLoading" @click="onSubmit()">
                    <span :class="submitLoading ? 'fa fa-spinner fa-spin' : submitIconClass" />{{ submitTitle | l }}
                </GButton>
                <GButton v-if="cancelRedirect" @click="onCancel()">
                    <span class="mr-1 fa fa-times" />{{ "Cancel" | l }}
                </GButton>
            </div>
        </div>
    </UrlDataProvider>
</template>

<script>
import FormCard from "@/components/Form/FormCard";
import FormDisplay from "@/components/Form/FormDisplay";
import { visitInputs } from "@/components/Form/utilities";
import { UrlDataProvider } from "@/components/providers/UrlDataProvider";
import { IconDefinition } from "font-awesome-6";
import { withPrefix } from "@/utils/redirect";

import { submitData } from "./services";

import GButton from "@/components/BaseComponents/GButton.vue";

export default {
    components: {
        FormCard,
        FormDisplay,
        UrlDataProvider,
        GButton,
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
            type: IconDefinition,
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
        trimInputs: {
            type: Boolean,
            default: false,
        },
    },
    data() {
        return {
            messageText: null,
            messageVariant: null,
            formData: {},
            replaceParams: null,
            submitLoading: false,
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
            window.location = withPrefix(this.cancelRedirect);
        },
        async onSubmit() {
            try {
                this.submitLoading = true;

                const formData = { ...this.formData };

                if (this.trimInputs) {
                    // Trim string values in form data
                    Object.keys(formData).forEach((key) => {
                        if (typeof formData[key] === "string") {
                            formData[key] = formData[key].trim();
                        }
                    });
                }

                const response = await submitData(this.url, formData);
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
                    window.location = withPrefix(`${this.redirect}?${urlParams.toString()}`);
                } else {
                    const replaceParams = {};
                    visitInputs(response.inputs, (input, name) => {
                        replaceParams[name] = input.value;
                    });
                    this.replaceParams = replaceParams;
                    this.showMessage(response.message);
                }
            } catch (error) {
                this.onError(error);
            } finally {
                this.submitLoading = false;
            }
        },
        onError(error) {
            this.showMessage(error || `Failed to load resource ${this.url}.`, "danger");
        },
        showMessage(message, variant = "success") {
            this.messageText = message;
            this.messageVariant = variant;
            document.querySelector("#center").scrollTop = 0;
        },
    },
};
</script>
