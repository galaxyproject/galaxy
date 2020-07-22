$(document).ready(function() {
	var GTNView = Backbone.View.extend({

		parentElement: $('.full-content'),

		initialize: function () {
			this.active_filter = "all";
			this.render();
			this.registerEvents();
			this.watchAndMutate();
		},

		watchAndMutate: function() {
			var self = this;
			$('#gtn-embed').on('load', function() {
				//new_url = document.getElementById("gtn-embed").contentWindow.location.href;
				var gtn_tools = $("#gtn-embed").contents().find("span[data-tool]");
				// Buttonify
				gtn_tools.addClass("btn btn-primary");

				gtn_tools.click(function(e){
					var target = e.target;

					// Sometimes we get the i or the strong, not the parent.
					if(e.target.tagName.toLowerCase() !== "span"){
						target = e.target.parentElement;
					}

					tool_id = $(target).data('tool')
					tool_version = $(target).data('version')

					if(tool_id === 'upload1' || tool_id === 'upload'){
						Galaxy.upload.show()
					} else {
						Galaxy.router.push(`/?tool_id=${tool_id}&version=${tool_version}`)
					}
					self.removeOverlay();
				})
			});
		},

		/** Render the overlay html */
		render: function() {
			this.parentElement.prepend( this._template() );
		},

		/** Register events for the overlay */
		registerEvents: function() {
			var self = this;

			self.parentElement.find( 'ul #gtn a' ).on( 'click', function( e ) {
				e.preventDefault();
				e.stopPropagation();
				if ( $( '.gtn-screen-overlay' ).is( ':visible' ) ){
					self.removeOverlay();
				}
				else {
					self.showOverlay();
				}
			});

			// Remove the overlay on escape button click
			self.parentElement.on( 'keydown', function( e ) {
				// Check for escape button - "27"
				if ( e.which === 27 || e.keyCode === 27 ) {
					self.removeOverlay();
				}
			});

			$("#gtn-header").click(function(){
				self.removeOverlay();
			})
		},

		/** Show overlay */
		showOverlay: function() {
			var $el_gtn_textbox = $( '.txtbx-gtn-data' );
			$( '.gtn-screen-overlay' ).show();
			$( '.gtn-screen' ).show();

		},

		/** Remove the gtn overlay */
		removeOverlay: function() {
			$( '.gtn-screen-overlay' ).hide();
			$( '.gtn-screen' ).hide();

		},

		/** Template for gtn overlay */
		_template: function() {
			return `
				<div id="gtn_screen_overlay" class="gtn-screen-overlay"></div>
				<div id="gtn_screen" class="gtn-screen">
					<div class="gtn-header">
						<iframe id="gtn-embed" src="/training-material/topics/visualisation/tutorials/circos/tutorial.html?theme=rainbow" width="80%" height="80%"></iframe>
					</div>
				</div>
		   `;

		},
	});

	gtn_view = new GTNView();

});
