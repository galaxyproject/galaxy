/** This class contains all button views. */
define(['utils/utils'], function( Utils ) {
    /** This renders the default button which is used e.g. at the bottom of the upload modal. */
    var ButtonDefault = Backbone.View.extend({
        initialize: function( options ) {
            this.model = options && options.model || new Backbone.Model({
                id          : Utils.uid(),
                title       : '',
                floating    : 'right',
                icon        : '',
                cls         : 'ui-button btn btn-default',
                wait        : false,
                wait_text   : 'Sending...',
                wait_cls    : 'btn btn-info',
                disabled    : false
            }).set( options );
            this.setElement( $( '<button/>' ).attr( 'type', 'button' )
                                             .append( this.$icon  = $( '<i/>' ) )
                                             .append( '&nbsp;' )
                                             .append( this.$title = $( '<span/>' ) ) );
            this.listenTo( this.model, 'change', this.render, this );
            this.render();
        },

        render: function() {
            var self = this;
            var options = this.model.attributes;
            this.$el.removeClass()
                    .addClass( options.cls )
                    .addClass( options.disabled && 'disabled' )
                    .attr( 'id', options.id )
                    .prop( 'disabled', options.disabled )
                    .css( 'float', options.floating )
                    .off( 'click' ).on( 'click' , function() {
                        $( '.tooltip' ).hide();
                        options.onclick && !self.disabled && options.onclick();
                    })
                    .tooltip( { title: options.tooltip, placement: 'bottom' } );
            this.$icon.removeClass().addClass( 'icon fa' ).addClass( options.icon );
            this.$title.removeClass().addClass( 'title' ).html( options.title );
            if ( options.wait ) {
                this.$el.removeClass( options.cls ).addClass( options.wait_cls ).prop( 'disabled', true );
                this.$icon.removeClass( options.icon ).addClass( 'fa-spinner fa-spin' );
                this.$title.html( options.wait_text );
            }
        },

        /** Disable button */
        disable: function() {
            this.model.set( 'disabled', true );
        },

        /** Enable button */
        enable: function() {
            this.model.set( 'disabled', false );
        },

        /** Show spinner to indicate that the button is not ready to be clicked */
        wait: function() {
            this.model.set( 'wait', true );
        },

        /** Hide spinner to indicate that the button is ready to be clicked */
        unwait: function() {
            this.model.set( 'wait', false );
        }
    });

    /** This button allows the right-click/open-in-new-tab feature, its used e.g. for panel buttons. */
    var ButtonLink = ButtonDefault.extend({
        initialize: function( options ) {
            this.model = options && options.model || new Backbone.Model({
                id          : Utils.uid(),
                title       : '',
                icon        : '',
                cls         : ''
            }).set( options );
            this.setElement( $( '<a/>' ).append( this.$icon  = $( '<span/>' ) ) );
            this.listenTo( this.model, 'change', this.render, this );
            this.render();
        },

        render: function() {
            var options = this.model.attributes;
            this.$el.removeClass()
                    .addClass( options.cls )
                    .attr( { id         : options.id,
                             href       : options.href || 'javascript:void(0)',
                             title      : options.title,
                             target     : options.target || '_top',
                             disabled   : options.disabled } );
            this.$icon.removeClass().addClass( options.icon );
        }
    });

    /** The check button is used in the tool form and allows to distinguish between multiple states e.g. all, partially and nothing selected. */
    var ButtonCheck = Backbone.View.extend({
        initialize: function( options ) {
            this.model = options && options.model || new Backbone.Model({
                id          : Utils.uid(),
                title       : 'Select/Unselect all',
                icons       : [ 'fa-square-o', 'fa-minus-square-o', 'fa-check-square-o' ],
                value       : 0,
                onchange    : function(){}
            }).set( options );
            this.setElement( $( '<div/>' ).append( this.$icon   = $( '<span/>' ) )
                                          .append( this.$title  = $( '<span/>' ) ) );
            this.listenTo( this.model, 'change', this.render, this );
            this.render();
        },

        render: function( options ) {
            var self = this;
            var options = this.model.attributes;
            this.$el.addClass( 'ui-button-check' )
                    .off( 'click' ).on('click', function() {
                        self.model.set( 'value', ( self.model.get( 'value' ) === 0 && 2 ) || 0 );
                        options.onclick && options.onclick();
                    });
            this.$title.html( options.title );
            this.$icon.removeClass()
                      .addClass( 'icon fa' )
                      .addClass( options.icons[ options.value ] );
        },

        /* Sets a new value and/or returns the value.
        * @param{Integer}   new_val - Set a new value 0=unchecked, 1=partial and 2=checked.
        * OR:
        * @param{Integer}   new_val - Number of selected options.
        * @param{Integer}   total   - Total number of available options.
        */
        value: function ( new_val, total ) {
            if ( new_val !== undefined ) {
                if ( total && new_val !== 0 ) {
                    new_val = ( new_val !== total ) && 1 || 2;
                }
                this.model.set( 'value', new_val );
                this.model.get( 'onchange' )( this.model.get( 'value' ) );
            }
            return this.model.get( 'value' );
        }
    });

    /** This renders a differently styled, more compact button version.
        TODO: Consolidate with icon-button.js and/or button-default.js.
    */
    var ButtonIcon = Backbone.View.extend({
        initialize : function( options ) {
            // get options
            this.options = Utils.merge( options, {
                id          : Utils.uid(),
                title       : '',
                floating    : 'right',
                cls         : 'ui-button-icon',
                icon        : '',
                tooltip     : '',
                onclick     : null
            });

            // create new element
            this.setElement( this._template( this.options ) );

            // link button element
            this.$button = this.$el.find( '.button' );

            // add event
            var self = this;
            $(this.el).on('click', function() {
                // hide all tooltips
                $( '.tooltip' ).hide();

                // execute onclick callback
                if ( options.onclick && !self.disabled ) {
                    options.onclick();
                }
            });

            // add tooltip
            this.$button.tooltip( { title: options.tooltip, placement: 'bottom' } );
        },

        // disable
        disable: function() {
            this.$button.addClass( 'disabled' );
            this.disabled = true;
        },

        // enable
        enable: function() {
            this.$button.removeClass( 'disabled' );
            this.disabled = false;
        },

        // change icon
        setIcon: function(icon_cls) {
            this.$('i').removeClass( this.options.icon ).addClass( icon_cls );
            this.options.icon = icon_cls;
        },

        // template
        _template: function( options ) {
            // width
            var width = '';
            if ( options.title ) {
                width = 'width: auto;';
            }

            // string
            var str =   '<div id="' + options.id + '" style="float: ' + options.floating + '; ' + width + '" class="' + options.cls + '">' +
                            '<div class="button">';
            if (options.title) {
                str +=          '<i class="icon fa ' + options.icon + '"/>&nbsp;' +
                                '<span class="title">' + options.title + '</span>';
            } else {
                str +=          '<i class="icon fa ' + options.icon + '"/>';
            }
            str +=          '</div>' +
                        '</div>';
            return str;
        }
    });

    /** This class creates a button with dropdown menu. It extends the functionality of the Ui.ButtonIcon class.
        TODO: Consolidate class, use common base class
    */
    var ButtonMenu = Backbone.View.extend({
        // optional sub menu
        $menu: null,

        // initialize
        initialize: function ( options ) {
            // get options
            this.options = Utils.merge( options, {
                // same as Ui.ButtonIcon
                id              : '',
                title           : '',
                floating        : 'right',
                pull            : 'right',
                icon            : null,
                onclick         : null,
                cls             : 'ui-button-icon ui-button-menu',
                tooltip         : '',
                
                // additional options
                target          : '',
                href            : '',
                onunload        : null,
                visible         : true,
                tag             : ''
            } );

            // add template for tab
            this.setElement( $( this._template( this.options ) ) );

            // find root
            var $root = $( this.el ).find( '.root' );

            // link head
            var self = this;
            $root.on( 'click', function( e ) {
                // hide all tooltips
                $( '.tooltip' ).hide();

                // prevent default
                e.preventDefault();

                // add click event
                if( self.options.onclick ) {
                    self.options.onclick();
                }
            });

            // visiblity
            if ( !this.options.visible )
                this.hide();

            // add tooltip
            $root.tooltip( { title: options.tooltip, placement: 'bottom' } );
        },

        // show
        show: function() {
            $( this.el ).show();
        },

        // hide
        hide: function() {
            $( this.el ).hide();
        },

        // add menu item
        addMenu: function ( options ) {
            // menu option defaults
            var menuOptions = {
                title       : '',
                target      : '',
                href        : '',
                onclick     : null,
                divider     : false,
                icon        : null,
                cls         : 'button-menu btn-group'
            }

            // get options
            menuOptions = Utils.merge( options, menuOptions );

            // check if submenu element is available
            if ( !this.$menu ) {
                // insert submenu element into root
                $( this.el ).append( this._templateMenu() );

                // update element link
                this.$menu = $( this.el ).find( '.menu' );
            }

            // create
            var $item = $( this._templateMenuItem( menuOptions ) );

            // add events
            $item.on( 'click', function( e ) {
                if( menuOptions.onclick ) {
                    e.preventDefault();
                    menuOptions.onclick();
                }
            });

            // append menu
            this.$menu.append( $item );

            // append divider
            if ( menuOptions.divider ) {
                this.$menu.append( $( this._templateDivider() ) );
            }
        },

        // fill template header
        _templateMenuItem: function ( options ) {
            var tmpl =  '<li>' +
                            '<a class="dropdown-item" href="' + options.href + '" target="' + options.target + '" ';
            if ( options.download ) {
                tmpl +=         'download="' + options.download + '"';
            }
            tmpl +=         '>';
            if ( options.icon ) {
                tmpl +=         '<i class="fa ' + options.icon + '"/>';
            }
            tmpl +=             ' ' + options.title +
                            '</a>' +
                        '</li>';
            return tmpl;
        },

        // fill template header
        _templateMenu: function () {
            return '<ul class="menu dropdown-menu pull-' + this.options.pull + '" role="menu"/>';
        },

        _templateDivider: function() {
            return '<li class="divider"/>';
        },

        // element
        _template: function(options) {
            // TODO: width/margin should be set in css
            var width = '';
            var margin = '';
            if ( options.title ) {
                width = 'width: auto;';
            } else {
                margin = 'margin: 0px;';
            }
            var str =   '<div id="' + options.id + '" style="float: ' + options.floating + '; ' + width + '" class="dropdown ' + options.cls + '">' +
                            '<div class="root button dropdown-toggle" data-toggle="dropdown" style="' + margin + '">' +
                                '<i class="icon fa ' + options.icon + '"/>';
            if ( options.title ) {
                str +=          '&nbsp;<span class="title">' + options.title + '</span>';
            }
            str +=          '</div>' +
                        '</div>';
            return str;
        }
    });

    return {
        ButtonDefault   : ButtonDefault,
        ButtonLink      : ButtonLink,
        ButtonIcon      : ButtonIcon,
        ButtonCheck     : ButtonCheck,
        ButtonMenu      : ButtonMenu
    }
});
