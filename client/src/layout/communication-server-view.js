/** Real-time Communication feature **/
import $ from "jquery";
import Backbone from "backbone";
import _ from "underscore";
import _l from "utils/localization";
import Modal from "mvc/ui/ui-modal";
import { getGalaxyInstance } from "app";

export const CommunicationServerView = Backbone.View.extend({
    initialize: function () {
        this.modal = null;
    },

    /** makes bootstrap modal and iframe inside it */
    makeModalIframe: function (e) {
        const Galaxy = getGalaxyInstance();
        // make modal
        const host = Galaxy.config.communication_server_host;

        const port = Galaxy.config.communication_server_port;
        const username = _.escape(Galaxy.user.attributes.username);

        const persistent_communication_rooms = _.escape(Galaxy.config.persistent_communication_rooms);

        const query_string = `?username=${username}&persistent_communication_rooms=${persistent_communication_rooms}`;

        const src = `${host}:${port}${query_string}`;
        let $el_chat_modal_header = null;
        let $el_chat_modal_body = null;

        const iframe_template = `<iframe class="h-100 w-100" src="${src}"> </iframe>`;

        const header_template =
            '<i class="fa fa-comment" aria-hidden="true" title="Communicate with other users"></i>' +
            '<i class="fa fa-expand expand-compress-modal" aria-hidden="true" title="Maximize"></i>' +
            '<i class="fa fa-times close-modal" aria-hidden="true" title="Close"></i>';

        const frame_height = 350;
        const frame_width = 600;
        const class_names = "ui-modal chat-modal";

        // deletes the chat modal if already present and create one
        if ($(".chat-modal").length > 0) {
            $(".chat-modal").remove();
        }
        // creates a modal
        CommunicationServerView.modal = new Modal.View({
            body: iframe_template,
            height: frame_height,
            width: frame_width,
            closing_events: true,
            title_separator: false,
            cls: class_names,
        });

        // shows modal
        CommunicationServerView.modal.show();
        $el_chat_modal_header = $(".chat-modal .modal-header");
        $el_chat_modal_body = $(".chat-modal .modal-body");
        // adjusts the css of bootstrap modal for chat
        $el_chat_modal_header.addClass("modal-header-body");
        $el_chat_modal_body.addClass("modal-header-body");
        $el_chat_modal_header.find("h4").remove();
        $el_chat_modal_header.removeAttr("min-height padding border");
        $el_chat_modal_header.append(header_template);
        // click event of the close button for chat
        $(".close-modal").click((e) => {
            $(".chat-modal").css("display", "none");
        });
        // click event of expand and compress icon
        $(".expand-compress-modal").click((e) => {
            if ($(".expand-compress-modal").hasClass("fa-expand")) {
                $(".chat-modal .modal-dialog").width("1000px");
                $(".chat-modal .modal-body").height("575px");
                $(".expand-compress-modal").removeClass("fa-expand").addClass("fa-compress");
                $(".expand-compress-modal").attr("title", "Minimize");
                $(".expand-compress-modal").css("margin-left", "96.2%");
            } else {
                $(".chat-modal .modal-dialog").width(`${frame_width}px`);
                $(".chat-modal .modal-body").height(`${frame_height}px`);
                $(".expand-compress-modal").removeClass("fa-compress").addClass("fa-expand");
                $(".expand-compress-modal").attr("title", "Maximize");
                $(".expand-compress-modal").css("margin-left", "93.2%");
            }
        });
        return this;
    },

    /**renders the chat icon as a nav item*/
    render: function () {
        return {
            id: "show-chat-online",
            icon: "fa-comment-o",
            tooltip: _l("Chat online"),
            visible: false,
            onclick: this.makeModalIframe,
        };
    },
});
