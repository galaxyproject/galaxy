<!-- https://schema.org/Organization -->
<template>
    <b-form @submit="onSave" @reset="onReset">
        <div v-for="attribute in displayedAttributes" :key="attribute.key" role="group" class="form-group">
            <label :for="attribute.key">{{ attribute.label }}</label>
            <font-awesome-icon
                v-b-tooltip.hover
                title="Hide Attribute"
                icon="eye-slash"
                @click="onHide(attribute.key)" />
            <b-form-input
                :id="attribute.key"
                v-model="currentValues[attribute.key]"
                :placeholder="'Enter ' + attribute.placeholder + '.'"
                :type="attribute.type">
            </b-form-input>
        </div>
        <div role="group" class="form-group">
            <b-form-select v-model="addAttribute" :options="addAttributes" size="sm"></b-form-select>
        </div>
        <b-button type="submit" variant="primary">Save</b-button>
        <b-button type="reset" variant="danger">Cancel</b-button>
    </b-form>
</template>

<script>
const ATTRIBUTES_INFO = [
    { key: "name", label: "Name", placeholder: "name" },
    { key: "url", label: "URL", placeholder: "URL", type: "url" },
    { key: "identifier", label: "Identifier", placeholder: "identifier" },
    { key: "image", label: "Image URL", placeholder: "image URL", type: "url" },
    { key: "address", label: "Address", placeholder: "address" },
    { key: "email", label: "Email", placeholder: "email", type: "email" },
    { key: "telephone", label: "Telephone", placeholder: "telephone", type: "tel" },
    { key: "faxNumber", label: "Fax Number", placeholder: "fax number", type: "tel" },
    { key: "alternateName", label: "Alternate Name", placeholder: "alternate name" },
];
const ATTRIBUTES = ATTRIBUTES_INFO.map((a) => a.key);

import ThingFormMixin from "./ThingFormMixin";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faEyeSlash, faLink } from "@fortawesome/free-solid-svg-icons";

library.add(faEyeSlash, faLink);

export default {
    components: {
        FontAwesomeIcon,
    },
    mixins: [ThingFormMixin],
    props: {
        organization: {
            type: Object,
        },
    },
    data() {
        const currentValues = {};
        const show = {};
        for (const attribute of ATTRIBUTES) {
            const showAttribute = attribute in this.organization;
            if (showAttribute) {
                let value = this.organization[attribute];
                if (attribute == "email") {
                    if (value.indexOf("mailto:") == 0) {
                        value = value.slice("mailto:".length);
                    }
                }
                currentValues[attribute] = value;
            }
            show[attribute] = showAttribute;
        }
        return {
            attributeInfo: ATTRIBUTES_INFO,
            show: show,
            currentValues: currentValues,
            addAttribute: null,
            schemaOrgClass: "Organization",
        };
    },
};
</script>
