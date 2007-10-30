(function($) {
	
	$.fx.drop = function(type, set, speed, callback) {

		this.each(function() {

			if(!set.direction) set.direction = "left"; //Default direction
			var s = $.fx.findSides($(this)), dir = { left: s[0], right: s[0], up: s[1], down: s[1] };
			var cur = $(this); $.fx.relativize(cur);

			if(type == "show") {
				var animation = {  }, after = {};
				var prefix = { left: (s[0] == 'left' ? '+=' : '-='), right: (s[0] == 'left' ? '-=' : '+='), up: (s[1] == 'top' ? '+=' : '-='), down: (s[1] == 'top' ? '-=' : '+=')};

				animation[dir[set.direction]] = prefix[set.direction]+200;
				cur.show().css(dir[set.direction], parseInt(cur.css(dir[set.direction])) + (prefix[set.direction] == "+=" ? -200 : 200));
			} else {
				var animation = {}, after = { display: 'none' };
				var prefix = { left: (s[0] == 'left' ? '-=' : '+='), right: (s[0] == 'left' ? '+=' : '-='), up: (s[1] == 'top' ? '-=' : '+='), down: (s[1] == 'top' ? '+=' : '-=')};
				
				animation[dir[set.direction]] = prefix[set.direction]+200;
				after[dir[set.direction]] = $(this).css(dir[set.direction]);
			}

			cur.animate(animation, speed, set.easing, function() { //Animate
				cur.css(after);
				if(callback) callback.apply(this, arguments);
			});		
	
		});
		
	}
	
})(jQuery);