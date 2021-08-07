<template>
    <UrlDataProvider :url="url" v-slot="{ result, loading }" @error="onError">
        <div v-if="!loading">
            <b-alert v-if="result.message" :variant="resultMessageVariant" show>
                {{ result.message }}
            </b-alert>
            <b-alert v-if="messageText" :variant="messageVariant" show>
                {{ messageText }}
            </b-alert>
            <FormCard :title="result.title" :icon="result.icon">
                <template v-slot:body>
                    <FormDisplay :inputs="result.inputs" @onChange="onChange" />
                </template>
            </FormCard>
            <div class="mt-2">
                <b-button
                    variant="primary"
                    class="mr-1"
                    v-b-tooltip.hover
                    :title="result.submit_tooltip"
                    @click="onSubmit(result)"
                >
                    <span :class="submitIcon(result)" />{{ submitTitle(result) | l }}
                </b-button>
                <b-button
                    v-if="result.cancel_redirect"
                    v-b-tooltip.hover
                    :title="result.cancel_tooltip"
                    @click="onCancel(result)"
                >
                    <span :class="cancelIcon(result)" />{{ cancelTitle(result) | l }}
                </b-button>
            </div>
        </div>
    </UrlDataProvider>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import { UrlDataProvider } from "components/providers/UrlDataProvider";
import FormCard from "components/Form/FormCard";
import FormDisplay from "components/Form/FormDisplay";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faSave, faTimes } from "@fortawesome/free-solid-svg-icons";

library.add(faSave, faTimes);

export default {
    props: {
        url: {
            type: String,
            required: true,
        },
        redirect: {
            type: String,
            required: false,
        },
    },
    components: {
        FontAwesomeIcon,
        FormCard,
        FormDisplay,
        UrlDataProvider,
    },
    data() {
        return {
            messageText: null,
            messageVariant: null,
            formData: {},
        };
    },
    methods: {
        resultMessageVariant(options) {
            return result.status || "warning";
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
        onSubmit(options) {
            /*
            var self = this;
        $.ajax({
            url: getAppRoot() + self.url,
            data: JSON.stringify(form.data.create()),
            type: "PUT",
            contentType: "application/json",
        })
            .done((response) => {
                var params = {};
                if (response.id) {
                    params.id = response.id;
                } else {
                    params = {
                        message: response.message,
                        status: "success",
                        persistent: false,
                    };
                }
                if (self.redirect) {
                    window.location = `${getAppRoot()}${self.redirect}?${$.param(params)}`;
                } else {
                    form.data.matchModel(response, (input, input_id) => {
                        form.field_list[input_id].value(input.value);
                    });
                    self._showMessage(form, response.message);
                }
            })
            .fail((response) => {
                self._showMessage(form, {
                    message: response.responseJSON.err_msg,
                    status: "danger",
                    persistent: false,
                });
            });*/
        },
        onError(error) {
            this.messageText = `Failed to load resource ${this.url}.`;
            this.messageVariant = "danger";
        },
    },
};
</script>
