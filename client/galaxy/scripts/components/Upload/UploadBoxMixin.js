import _l from "utils/localization";
import $ from "jquery";
import Select2 from "components/Select2";
import UploadExtension from "mvc/upload/upload-extension";
import UploadModel from "mvc/upload/upload-model";
import UploadWrapper from "./UploadWrapper";

export default {
    components: {
        UploadWrapper,
        Select2
    },
    props: {
        app: {
            type: Object,
            required: true
        }
    },
    methods: {
        initExtensionInfo() {
            $(this.$refs.footerExtensionInfo)
                .on("click", e => {
                    new UploadExtension({
                        $el: $(e.target),
                        title: this.select_extension.text(),
                        extension: this.select_extension.value(),
                        list: this.list_extensions,
                        placement: "top"
                    });
                })
                .on("mousedown", e => {
                    e.preventDefault();
                });
        },
        initCollection() {
            this.collection = new UploadModel.Collection();
        },
        initAppProperties() {
            this.listExtensions = this.app.listExtensions;
            this.listGenomes = this.app.listGenomes;
            this.ftpUploadSite = this.app.currentFtp();
        },
        initFtpPopover() {
            // add ftp file viewer
            this.ftp = new Popover({
                title: _l("FTP files"),
                container: this.btnFtp.$el
            });
        },
    }
};
