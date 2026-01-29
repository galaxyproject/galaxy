// As silly as ThingViewerMixin sounds - they are literally http://schema.org/Thing objects.

export default {
    computed: {
        explicitMetaAttributes() {
            return this.items.filter((i) => this.implicitMicrodataProperties.indexOf(i.attribute) == -1);
        },
        items() {
            const items = [];
            for (const key in this.thing) {
                if (key == "class") {
                    continue;
                }
                items.push({ attribute: key, value: this.thing[key] });
            }
            return items;
        },
        email() {
            let email = this.thing.email;
            if (email && email.indexOf("mailto:") == 0) {
                email = email.slice("mailto:".length);
            }
            return email;
        },
        url() {
            return this.thing.url;
        },
    },
};
