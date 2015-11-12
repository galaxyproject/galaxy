define([
    'jquery',
], function (jQuery){

"use strict";
// ============================================================================
//TODO: (the older version) unify with ui-modal (the newer version)
var $ = jQuery;

// Modal dialog boxes
var Modal = function( options ) {
    this.$overlay = options.overlay;
    this.$dialog = options.dialog;
    this.$header = this.$dialog.find( ".modal-header" );
    this.$body = this.$dialog.find( ".modal-body" );
    this.$footer = this.$dialog.find( ".modal-footer" );
    this.$backdrop = options.backdrop;
    // Close button
    this.$header.find( ".close" ).on( "click", $.proxy( this.hide, this ) );
};

$.extend( Modal.prototype, {
    setContent: function( options ) {
        this.$header.hide();
        // Title
        if ( options.title ) {
            this.$header.find( ".title" ).html( options.title );
            this.$header.show();
        }
        if ( options.closeButton ) {
            this.$header.find( ".close" ).show();
            this.$header.show();
        } else {
            this.$header.find( ".close" ).hide();
        }
        // Buttons
        this.$footer.hide();
        var $buttons = this.$footer.find( ".buttons" ).html( "" );
        if ( options.buttons ) {
            $.each( options.buttons, function( name, value ) {
                 $buttons.append( $( '<button></button> ' ).text( name ).click( value ) ).append( " " );
            });
            this.$footer.show();
        }
        var $extraButtons = this.$footer.find( ".extra_buttons" ).html( "" );
        if ( options.extra_buttons ) {
            $.each( options.extra_buttons, function( name, value ) {
                 $extraButtons.append( $( '<button></button>' ).text( name ).click( value ) ).append( " " );
            });
            this.$footer.show();
        }
        // Body
        var body = options.body;
        if ( body == "progress" ) {
            body = $("<div class='progress progress-striped active'><div class='progress-bar' style='width: 100%'></div></div>");
        }
        this.$body.html( body );
    },
    show: function( options, callback ) {
        if ( ! this.$dialog.is( ":visible" ) ) {
            if ( options.backdrop) {
                this.$backdrop.addClass( "in" );
            } else {
                this.$backdrop.removeClass( "in" );
            }
            this.$overlay.show();
            this.$dialog.show();
            this.$overlay.addClass("in");
            // Fix min-width so that modal cannot shrink considerably if new content is loaded.
            this.$body.css( "min-width", this.$body.width() );
            // Set max-height so that modal does not exceed window size and is in middle of page.
            // TODO: this could perhaps be handled better using CSS.
            this.$body.css( "max-height",
                            $(window).height() -
                            this.$footer.outerHeight() -
                            this.$header.outerHeight() -
                            parseInt( this.$dialog.css( "padding-top" ), 10 ) -
                            parseInt( this.$dialog.css( "padding-bottom" ), 10 )
                            );
        }
        // Callback on init
        if ( callback ) {
            callback();
        }
    },
    hide: function() {
        var modal = this;
        modal.$dialog.fadeOut( function() {
           modal.$overlay.hide();
           modal.$backdrop.removeClass( "in" );
           modal.$body.children().remove();
           // Clear min-width to allow for modal to take size of new body.
           modal.$body.css( "min-width", undefined );
       });
   }
});

var modal;

$(function(){
   modal = new Modal( { overlay: $("#top-modal"), dialog: $("#top-modal-dialog"), backdrop: $("#top-modal-backdrop") } );
});

// Backward compatibility
function hide_modal() {
    modal.hide();
}

function show_modal( title, body, buttons, extra_buttons, init_fn ) {
    modal.setContent( { title: title, body: body, buttons: buttons, extra_buttons: extra_buttons } );
    modal.show( { backdrop: true }, init_fn );
}

function show_message( title, body, buttons, extra_buttons, init_fn ) {
    modal.setContent( { title: title, body: body, buttons: buttons, extra_buttons: extra_buttons } );
    modal.show( { backdrop: false }, init_fn  );
}

function show_in_overlay( options ) {
    var width = options.width || '600';
    var height = options.height || '400';
    var scroll = options.scroll || 'auto';
    $("#overlay-background").bind( "click.overlay", function() {
        hide_modal();
        $("#overlay-background").unbind( "click.overlay" );
    });
    modal.setContent({
        closeButton: true,
        title: "&nbsp;",
        body: $(
            "<div style='margin: -5px;'><iframe style='margin: 0; padding: 0;' src='" + options.url +
            "' width='" + width +
            "' height='" + height +
            "' scrolling='" + scroll +
            "' frameborder='0'></iframe></div>"
        )
    });
    modal.show( { backdrop: true } );
}


// ============================================================================
    return {
        Modal : Modal,
        hide_modal : hide_modal,
        show_modal : show_modal,
        show_message : show_message,
        show_in_overlay : show_in_overlay,
    };
});
