<script>
import jQuery from "jquery";
import { getGalaxyInstance } from "app";
import UI_MODAL from "mvc/ui/ui-modal";
import _l from "utils/localization";
import _ from "underscore";
export default {
    methods: {
        /** An interface for building collections.*/
        collectionCreatorModalSetup: function (options) {
            const deferred = jQuery.Deferred();
            const Galaxy = getGalaxyInstance();
            const modal = Galaxy.modal || new UI_MODAL.View();
            const creatorOptions = _.defaults(options || {}, {
                oncancel: function () {
                    modal.hide();
                    this.$destroy();
                },
                oncreate: function (creator, response) {
                    modal.hide();
                    deferred.resolve(response);
                },
            });
            const showEl = function (el) {
                modal.show({
                    title: options.title || _l("Create a collection"),
                    body: el,
                    width: "85%",
                    height: "100%",
                    xlarge: true,
                    closing_events: true,
                });
            };
            return { deferred, creatorOptions, showEl };
        },
    },
};
</script>

<style></style>
