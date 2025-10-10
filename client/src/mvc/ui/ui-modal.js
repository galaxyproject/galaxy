export class View {
    constructor(options = {}) {
        this.optionsDefault = {
            container: "body",
            title: "ui-modal",
            cls: "ui-modal",
            body: "",
            backdrop: true,
            height: null,
            width: null,
            xlarge: false,
            closing_events: false,
            closing_callback: null,
            title_separator: true
        };
        this.buttonList = {};
        this.options = Object.assign({}, this.optionsDefault, options);
        this.el = document.createElement("div");
        this.el.className = "ui-modal";
        document.querySelector(this.options.container).prepend(this.el);
        if (options) {
            this.render();
        }
    }
    show(options) {
        if (options) {
            this.options = Object.assign({}, this.optionsDefault, options);
            this.render();
        }
        if (!this.visible) {
            this.visible = true;
            this.el.style.display = "block";
            this.el.style.opacity = 0;
            requestAnimationFrame(() => {
                this.el.style.transition = "opacity 0.15s";
                this.el.style.opacity = 1;
            });
        }
        if (this.options.closing_events) {
            this._keyupHandler = (e) => {
                if (e.keyCode === 27) {
                    this.hide(true);
                }
            };
            document.addEventListener("keyup", this._keyupHandler);
            this.$backdrop.addEventListener("click", () => {
                this.hide(true);
            });
        }
        this.$header.querySelector(".title").focus();
    }
    hide(canceled) {
        this.visible = false;
        this.el.style.transition = "opacity 0.15s";
        this.el.style.opacity = 0;
        setTimeout(() => {
            this.el.style.display = "none";
        }, 150);
        if (this.options.closing_callback) {
            this.options.closing_callback(canceled);
        }
        if (this._keyupHandler) {
            document.removeEventListener("keyup", this._keyupHandler);
            this._keyupHandler = null;
        }
        if (this.$backdrop) {
            this.$backdrop.replaceWith(this.$backdrop.cloneNode(true));
        }
    }
    render() {
        this.el.innerHTML = this._template();
        this.$header = this.el.querySelector(".modal-header");
        this.$dialog = this.el.querySelector(".modal-dialog");
        if (this.options.extra_class) {
            this.$dialog.classList.add(this.options.extra_class);
        }
        this.$body = this.el.querySelector(".modal-body");
        this.$footer = this.el.querySelector(".modal-footer");
        this.$backdrop = this.el.querySelector(".modal-backdrop");
        this.$buttons = this.el.querySelector(".buttons");
        if (this.options.body === "progress") {
            const div = document.createElement("div");
            div.className = "progress progress-striped active";
            div.innerHTML = '<div class="progress-bar progress-bar-info" style="width:100%"></div>';
            this.options.body = div;
        }
        this.el.className = "modal " + this.options.cls;
        this.$header.querySelector(".title").innerHTML = this.options.title;
        if (typeof this.options.body === "string") {
            this.$body.innerHTML = this.options.body;
        } else {
            this.$body.innerHTML = "";
            this.$body.append(this.options.body);
        }
        this.$buttons.innerHTML = "";
        this.buttonList = {};
        if (this.options.buttons) {
            let counter = 0;
            for (const [name, callback] of Object.entries(this.options.buttons)) {
                const button = document.createElement("button");
                button.id = `button-${counter++}`;
                button.textContent = name;
                button.addEventListener("click", callback);
                this.$buttons.append(button);
                this.$buttons.append(document.createTextNode(" "));
                this.buttonList[name] = button;
            }
        } else {
            this.$footer.style.display = "none";
        }
        if (this.options.backdrop) {
            this.$backdrop.classList.add("in");
        } else {
            this.$backdrop.classList.remove("in");
        }
        if (!this.options.title_separator) {
            this.$header.classList.add("no-separator");
        } else {
            this.$header.classList.remove("no-separator");
        }
        this.$body.removeAttribute("style");
        if (this.options.height) {
            this.$body.style.height = this.options.height;
            this.$body.style.overflow = "hidden";
        } else {
            this.$body.style.maxHeight = window.innerHeight / 2 + "px";
        }
        if (this.options.width) {
            this.$dialog.style.width = this.options.width;
        }
        if (this.options.xlarge) {
            this.$dialog.style.maxWidth = "3000px";
        }
    }
    getButton(name) {
        return this.buttonList[name];
    }
    enableButton(name) {
        const btn = this.getButton(name);
        if (btn) {
            btn.disabled = false;
        }
    }
    disableButton(name) {
        const btn = this.getButton(name);
        if (btn) {
            btn.disabled = true;
        }
    }
    showButton(name) {
        const btn = this.getButton(name);
        if (btn) {
            btn.style.display = "";
        }
    }
    hideButton(name) {
        const btn = this.getButton(name);
        if (btn) {
            btn.style.display = "none";
        }
    }
    scrollTop() {
        return this.$body.scrollTop;
    }
    _template() {
        return (
            '<div class="modal-backdrop fade"></div>' +
            '<div class="modal-dialog">' +
            '<div class="modal-content">' +
            '<div class="modal-header">' +
            '<h4 class="title" tabindex="0"></h4>' +
            "</div>" +
            '<div class="modal-body"></div>' +
            '<div class="modal-footer">' +
            '<div class="buttons"></div>' +
            "</div>" +
            "</div>" +
            "</div>"
        );
    }
}
export default { View };
