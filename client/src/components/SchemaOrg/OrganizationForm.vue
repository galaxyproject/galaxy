<!-- https://schema.org/Organization -->
<template>
    <b-form @submit="onSave" @reset="onReset">
        <div v-for="attribute in displayedAttributes" :key="attribute.key" role="group" class="form-group">
            <label :for="attribute.key">{{ attribute.label }}</label>
            <span v-b-tooltip.hover title="隐藏属性"
                ><FontAwesomeIcon icon="eye-slash" @click="onHide(attribute.key)"
            /></span>
            <b-form-input
                :id="attribute.key"
                v-model="currentValues[attribute.key]"
                :placeholder="'输入' + attribute.placeholder + '。'"
                :type="attribute.type">
            </b-form-input>
        </div>
        <div role="group" class="form-group">
            <b-form-select v-model="addAttribute" :options="addAttributes" size="sm"></b-form-select>
        </div>
        <b-button type="submit" variant="primary">保存</b-button>
        <b-button type="reset" variant="danger">取消</b-button>
    </b-form>
</template>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faEyeSlash, faLink } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import ThingFormMixin from "./ThingFormMixin";

const ATTRIBUTES_INFO = [
    { key: "name", label: "名称", placeholder: "名称" },
    { key: "url", label: "网址", placeholder: "网址", type: "url" },
    { key: "identifier", label: "标识符", placeholder: "标识符" },
    { key: "image", label: "图片网址", placeholder: "图片网址", type: "url" },
    { key: "address", label: "地址", placeholder: "地址" },
    { key: "email", label: "电子邮箱", placeholder: "电子邮箱", type: "email" },
    { key: "telephone", label: "电话", placeholder: "电话", type: "tel" },
    { key: "faxNumber", label: "传真号码", placeholder: "传真号码", type: "tel" },
    { key: "alternateName", label: "备用名称", placeholder: "备用名称" },
];
const ATTRIBUTES = ATTRIBUTES_INFO.map((a) => a.key);

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
