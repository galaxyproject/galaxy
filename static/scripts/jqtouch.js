// David Kaneda, jQuery jQTouch extensions

(function($) {
    
    var currentPage = null;
    var currentDialog = null;
    var currentHash = location.hash;
    var hashPrefix = "#";
    var currentWidth = 0;
    var pageHistory = [];
    var pageHistoryInfo = [];
    var newPageCount = 0;
    var checkTimer;

    $.fn.jQTouch = function(options)
    {
        var defaults = {
            fullScreen: true,
            slideInSelector: 'ul li a',
            backSelector: '.back',
            flipSelector: '.flip',
            slideUpSelector: '.slideup',
            statusBar: 'default', // other options: black-translucent, black
            icon: null,
            iconIsGlossy: false,
            fixedViewport: true
        };
        
        var settings = $.extend({}, defaults, options);
        var head = $('head');

        if (settings.backSelector)
        {
            $(settings.backSelector).live('click',function(){
                    history.back();
                    return false;
            });
        }

        if (settings.icon)
        {
            var precomposed = (settings.iconIsGlossy) ? '' : '-precomposed';
            head.append('<link rel="apple-touch-icon' + precomposed + '" href="' + settings.icon + '" />');
        }
        
        if (settings.fixedViewport)
        {
            head.append('<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=0;"/>');
        }
        
        if (settings.fullScreen)
        {
            head.append('<meta name="apple-mobile-web-app-capable" content="yes" />');
            
            if (settings.statusBar)
            {
                head.append('<meta name="apple-mobile-web-app-status-bar-style" content="' + settings.statusBar + '" />');
            }
        }
        
        var liveSelectors = [];
        
        if (settings.slideInSelector) liveSelectors.push(settings.slideInSelector);
        if (settings.flipSelector) liveSelectors.push(settings.flipSelector);
        if (settings.slideUpSelector) liveSelectors.push(settings.slideUpSelector);

        // Selector settings
        if (liveSelectors.length > 0)
        {
            $(liveSelectors.join(', ')).live('click',function(){
                
                var jelem = $(this);
                var hash = jelem.attr('hash');
                var transition = 'slideInOut';

                if ($(this).is(settings.flipSelector)) transition = 'flip';
                if ($(this).is(settings.slideUpSelector)) transition = 'slideUp';

                if ( hash && hash != '#')
                {
                    jelem.attr('selected', 'true');
                    $.fn.jQTouch.showPage($(hash), transition);
                    setTimeout($.fn.unselect, 350, $(this));
                }
                else if ( jelem.attr('href') != '#' )
                {
                    jelem.attr('selected', 'progress');

                    try {
                        $.fn.jQTouch.showPageByHref($(this).attr('href'), null, null, null, transition, function(){ setTimeout($.fn.unselect, 350, jelem);
                         });
                    }
                    catch(err)
                    {
                        console.log(err);
                    }
                }
                return false;
            });
            
            // Initialize
            
            $(function(){
                var page = $.fn.jQTouch.getSelectedPage();
                if (page) $.fn.jQTouch.showPage(page);

                // setTimeout($.fn.jQTouch.checkOrientandLocation, 0);
                $.fn.jQTouch.startCheck();
            })

        }
    }
    
    $.fn.ianimate = function(css, speed, fn) {
        
      // TODO: Autoconvert top,left to translate();
      //  ease | linear | ease-in | ease-out | ease-in-out | cubic-bezier(x1, y1, x2, y2)

      if(speed === 0) { // differentiate 0 from null
          this.css(css)
          window.setTimeout(fn, 0)
      } else {
          var s = []
          for(var i in css) 
          s.push(i)
          this.css({ webkitTransitionProperty: s.join(", "), webkitTransitionDuration: speed + "ms", webkitTransitionTimingFunction: 'ease-in-out' });

          window.setTimeout(function(x,y) {
              x.css(y)
              },0, this, css)
              window.setTimeout(fn, speed)
          }
          return this;
      }
    
    $.fn.jQTouch.checkOrientAndLocation = function()
    {
        if (window.innerWidth != currentWidth)
        {   
            currentWidth = window.innerWidth;
            currentHeight = window.innerHeight;
            var orient = currentWidth < currentHeight ? "profile" : "landscape";
            document.body.setAttribute("orient", orient);
            setTimeout(scrollTo, 100, 0, 1);
        }
        
        if (location.hash != currentHash)
            $.fn.jQTouch.showPageById(location.hash);
    }

    $.fn.jQTouch.getSelectedPage = function()
    {
        return $('body > *[selected!=false]').slice(0,1);
    }
    
    $.fn.jQTouch.showPage = function( page, transition, backwards )
    {
        if (page)
        {
            if (currentDialog)
            {
                currentDialog.attr('selected', null);
                currentDialog = null;
            }

            var fromPage = currentPage;
            currentPage = page;

            if (fromPage)
                $.fn.jQTouch.animatePages(fromPage, page, transition, backwards);
            else
                $.fn.jQTouch.updatePage(page, fromPage, transition);
        }
    }

    $.fn.jQTouch.showPageById = function( hash )
    {
        var page = $(hash);
        
        if (page)
        {
            var transition;
            var currentIndex = pageHistory.indexOf(currentHash);
            var index = pageHistory.indexOf(hash);
            var backwards = index != -1;

            if (backwards) {
                transition = pageHistoryInfo[currentIndex].transition;
                
                pageHistory.splice(index, pageHistory.length);
                pageHistoryInfo.splice(index, pageHistoryInfo.length);                
            }
            
            $.fn.jQTouch.showPage(page, transition, backwards);
        }
    }
    
    $.fn.jQTouch.insertPages = function( nodes, transition )
    {
        var targetPage;
        
        nodes.each(function(index, node){
            
            if (!$(this).attr('id'))
                $(this).attr('id', (++newPageCount));
                
            $(this).appendTo($('body'));
            
            if ( $(this).attr('selected') == 'true' || ( !targetPage && !$(this).hasClass('btn')) )
                targetPage = $(this);
        });
        
        if (targetPage) $.fn.jQTouch.showPage(targetPage, transition);
        
    }

    $.fn.jQTouch.showPageByHref = function(href, data, method, replace, transition, cb)
    {
        $.ajax({
            url: href,
            data: data,
            type: method || "GET",
            success: function (data, textStatus)
            {
                $('a[selected="progress"]').attr('selected', 'true');
                
                if (replace) $(replace).replaceWith(data);
                else
                {
                    $.fn.jQTouch.insertPages( $(data) );
                }
                
                if (cb) cb(true);
            },
            error: function (data)
            {
                if (cb) cb(false);
            }
        });

    }
    
    $.fn.jQTouch.submitForm = function()
    {
        $.fn.jQTouch.showPageByHref($(this).attr('action') || "POST", $(this).serialize(), $(this).attr('method'));
        return false;
    }
    
    $.fn.showForm = function ()
    {
        return this.each(function(){
            $(this).submit($.fn.jQTouch.submitForm);
        });
    }
    
    $.fn.jQTouch.animatePages = function(fromPage, toPage, transition, backwards)
    {
        clearInterval(checkTimer);
        
        if (transition == 'flip'){
            toPage.flip({backwards: backwards});
            fromPage.flip({backwards: backwards});
        }
        else if (transition == 'slideUp')
        {
            if (backwards)
            {
                toPage.attr('selected', true);
                fromPage.slideUpDown({backwards: backwards});
            }
            else
            {
                toPage.slideUpDown({backwards: backwards});
            }
            
        }
        else
        {
            toPage.slideInOut({backwards: backwards});
            fromPage.slideInOut({backwards: backwards});
        }
        
        setTimeout(function(){
            fromPage.attr('selected', 'false');
            $.fn.jQTouch.updatePage(toPage, fromPage, transition);
            $.fn.jQTouch.startCheck();
        }, 500);
    }
    
    $.fn.jQTouch.startCheck = function()
    {
        checkTimer = setInterval($.fn.jQTouch.checkOrientAndLocation, 350);
    }
    
    $.fn.jQTouch.updatePage = function(page, fromPage, transition)
    {
        if (page)
        {
            if (!page.attr('id'))
                page.attr('id', (++newPageCount));

            location.replace(hashPrefix + page.attr('id'));
            currentHash = location.hash;

            pageHistory.push(currentHash);
            pageHistoryInfo.push({page: page, transition: transition});
            
            if (page.attr('localName') == "form" && !page.attr('target'))
            {
                page.showForm();
            }
        }
    }
    
    $.fn.unselect = function(obj)
    {
        obj.attr('selected', false);
    }

    $.preloadImages = function( imgs )
    {
        for (var i = imgs.length - 1; i >= 0; i--){
            (new Image()).src = imgs[i];
        };
    }
    
    $.fn.flip = function(options)
    {
        this.each(function(){
            var defaults = {
                direction : 'toggle',
                backwards: false
            };

            var settings = $.extend({}, defaults, options);

            var dir = ((settings.direction == 'toggle' && $(this).attr('selected') == 'true') || settings.direction == 'out') ? 1 : -1;
            
            if (dir == -1) $(this).attr('selected', 'true');
            
            $(this).parent().css({webkitPerspective: '2000'});
            
            $(this).css({
                '-webkit-backface-visibility': 'hidden',
                '-webkit-transform': 'rotateY(' + ((dir == 1) ? '0' : (!settings.backwards ? '-' : '') + '180') + 'deg)'
            }).ianimate({'-webkit-transform': 'rotateY(' + ((dir == 1) ? (settings.backwards ? '-' : '') + '180' : '0') + 'deg)'}, 350);
        })
    }
    
    $.fn.slideInOut = function(options)
    {
        var defaults = {
            direction : 'toggle',
            backwards: false
        };

        var settings = $.extend({}, defaults, options);
        
        this.each(function(){

            var dir = ((settings.direction == 'toggle' && $(this).attr('selected') == 'true') || settings.direction == 'out') ? 1 : -1;                
            // Animate in
            if (dir == -1){

                $(this).attr('selected', 'true')
                    .css({'-webkit-transform': 'translateX(' + (settings.backwards ? -1 : 1) * currentWidth + 'px)'})
                    .ianimate({'-webkit-transform': 'translateX(0px)'}, 350)
                        .find('h1, .button')
                        .css('opacity', 0)
                        .ianimate({'opacity': 1}, 100);
            }
            // Animate out
            else
            {
                $(this)
                    .ianimate(
                        {'-webkit-transform': 'translateX(' + ((settings.backwards ? 1 : -1) * dir * currentWidth) + 'px)'}, 350)
                    .find('h1, .button')
                        .ianimate( {'opacity': 0}, 100);
            }

        })
    }
    
    $.fn.slideUpDown = function(options)
    {
        var defaults = {
            direction : 'toggle',
            backwards: false
        };

        var settings = $.extend({}, defaults, options);
        
        this.each(function(){

            var dir = ((settings.direction == 'toggle' && $(this).attr('selected') == 'true') || settings.direction == 'out') ? 1 : -1;                
            // Animate in
            if (dir == -1){

                $(this).attr('selected', 'true')
                    .css({'-webkit-transform': 'translateY(' + (settings.backwards ? -1 : 1) * currentHeight + 'px)'})
                    .ianimate({'-webkit-transform': 'translateY(0px)'}, 350)
                        .find('h1, .button')
                        .css('opacity', 0)
                        .ianimate({'opacity': 1}, 100);
            }
            // Animate out
            else
            {
                $(this)
                    .ianimate(
                        {'-webkit-transform': 'translateY(' + currentHeight + 'px)'}, 350)
                    .find('h1, .button')
                        .ianimate( {'opacity': 0}, 100);
            }

        })
    }
    
})(jQuery);