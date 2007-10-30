/**
 * Takes all matched elements and centers them, absolutely,
 * within the context of their parent element. Great for
 * doing slideshows.
 *
 * @example $("div img").center();
 * @name center
 * @type jQuery
 * @cat Plugins/Center
 */
jQuery.fn.center = function(f) {
	return this.each(function(){
		var p = this.parentNode;
		if ( jQuery.css(p,"position") == 'static' )
			p.style.position = 'relative';

		var s = this.style;
		s.position = 'absolute';
		if(!f || f == "horizontal") {
			if(((parseInt(jQuery.css(p,"width")) - parseInt(jQuery.css(this,"width")))/2) > 0)
				s.left = ((parseInt(jQuery.css(p,"width")) - parseInt(jQuery.css(this,"width")))/2) + "px";
			else
				s.left = "0";
		}
		if(!f || f == "vertical") {
			if(((parseInt(jQuery.css(p,"height")) - parseInt(jQuery.css(this,"height")))/2) > 0)
			{
				s.top = ((parseInt(jQuery.css(p,"height")) - parseInt(jQuery.css(this,"height")))/2) + "px";
			} else {
				if(p.nodeName.toLowerCase() == "body") {

				if (window.innerHeight)
    				var clientHeight = window.innerHeight;
  			 	else if(document.body && document.body.offsetHeight)
    				var clientHeight = document.body.offsetHeight;

					s.top = ((clientHeight - parseInt(jQuery.css(this,"height")))/2) + "px";
				} else {
					s.top = "0";
				}
			}
		}
	});
};
