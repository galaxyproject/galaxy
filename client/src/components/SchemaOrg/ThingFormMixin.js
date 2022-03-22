// As silly as ThingFormMixin sounds - they are literally http://schema.org/Thing objects.
export default {
    computed: {
        addAttributes() {
            const options = [{ value: null, text: "Add attribute" }];
            for (const attribute of this.attributeInfo) {
                if (!this.show[attribute.key]) {
                    options.push({ value: attribute.key, text: "- " + attribute.placeholder });
                }
            }
            return options;
        },
        displayedAttributes() {
            return this.attributeInfo.filter((a) => this.show[a.key]);
        },
    },
    watch: {
        addAttribute() {
            if (this.addAttribute) {
                this.show[this.addAttribute] = true;
            }
            this.$nextTick(() => {
                this.addAttribute = null;
            });
        },
    },
    methods: {
        onReset(evt) {
            evt.preventDefault();
            this.$emit("onReset");
        },
        onHide(attributeKey) {
            this.show[attributeKey] = false;
        },
        onSave(evt) {
            evt.preventDefault();
            const newThing = {};
            newThing.class = this.schemaOrgClass;
            for (const attributeInfo of this.attributeInfo) {
                const attribute = attributeInfo.key;
                if (this.show[attribute]) {
                    let value = this.currentValues[attribute];
                    if (attribute == "email") {
                        if (value.indexOf("mailto:") !== 0) {
                            value = "mailto:" + value;
                        }
                    }
                    newThing[attribute] = value;
                }
            }
            this.$emit("onSave", newThing);
        },
    },
};
