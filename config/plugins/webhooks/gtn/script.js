$(document).ready(function() {
	function showOverlay() {
		$(".gtn-screen-overlay").show();
		$(".gtn-screen").show();
	}

	function removeOverlay() {
		$(".gtn-screen-overlay").hide();
		$(".gtn-screen").hide();
	}

	function addIframe(proxied){
		var url, message;
		if(proxied){
			url = '/training-material/';
			message = ''
		}
		else {
			url = 'https://training.galaxyproject.org/training-material/';
			message = '<span><a href="https://docs.galaxyproject.org/en/master/admin/special_topics/gtn.html">Click to run</a> unavailable.</span>'
		}

		parentElement.prepend(`
			<div id="gtn_screen_overlay" class="gtn-screen-overlay"></div>
			<div id="gtn_screen" class="gtn-screen">
				<div class="gtn-header">
					<iframe id="gtn-embed" src="${url}" width="80%" height="80%"></iframe>
					${message}
				</div>
			</div>
	   `);

		// Clicking outside of GTN closes it
		$("#gtn_screen").click(function() {
			self.removeOverlay();
		});

		// Depends on the iframe being present
	$("#gtn-embed").on("load", function() {
		//new_url = document.getElementById("gtn-embed").contentWindow.location.href;
		var gtn_tools = $("#gtn-embed")
			.contents()
			.find("span[data-tool]");
		// Buttonify
		gtn_tools.addClass("btn btn-primary");

		gtn_tools.click(function(e) {
			var target = e.target;

			// Sometimes we get the i or the strong, not the parent.
			if (e.target.tagName.toLowerCase() !== "span") {
				target = e.target.parentElement;
			}

			tool_id = $(target).data("tool");
			tool_version = $(target).data("version");

			if (tool_id === "upload1" || tool_id === "upload") {
				Galaxy.upload.show();
			} else {
				Galaxy.router.push(`/?tool_id=${tool_id}&version=${tool_version}`);
			}
			self.removeOverlay();
		});
	});

	}

	var self = this;
	var parentElement = $(".full-content");
	self.showOverlay = showOverlay;
	self.removeOverlay = removeOverlay;

	// Test for the precense of /training-material/. If that is available we
	// can opt in the fancy click-to-run features. Otherwise we fallback to
	// displaying the real GTN.
	var jqxhr = $.get( "/training-material/", function() {
		// proxy is available
		addIframe(true)
	})
	.fail(function() {
		addIframe(false)
	})


	parentElement.find("ul #gtn a").on("click", function(e) {
		e.preventDefault();
		e.stopPropagation();
		if ($(".gtn-screen-overlay").is(":visible")) {
			self.removeOverlay();
		} else {
			self.showOverlay();
		}
	});

	// Remove the overlay on escape button click
	parentElement.on("keydown", function(e) {
		// Check for escape button - "27"
		if (e.which === 27 || e.keyCode === 27) {
			self.removeOverlay();
		}
	});

});
