<%doc>
    This file defines methods for displaying information about pagination
</%doc>

<%def name="get_page_url( sort_id, order, *args, **kwargs )">
        <a href="${h.url_for( controller=args[0], action=args[1], sort_id=sort_id, order=order, **kwargs )}">${kwargs.get("page")}</a>
</%def>

<%!
    def get_raw_url(sort_id, order, *args, **kwargs):
        return h.url_for( controller=args[0], action=args[1], sort_id=sort_id, order=order, **kwargs )
%>

<%def name="get_pages( sort_id, order, page_specs, *args, **kwargs )">
    ## Creates the page buttons
    ${get_page_script()}
    ${get_page_css()}

    <div id="page_selector">
        <div id="back_button">&#x219e;</div>
        %for x in range(-2,3):
            <% 
               page = int(page_specs.page) + x
               pages_found = int(page_specs.pages_found)
            %>
            %if page > 0:
                %if x == 0:
                    <div id="curr_button">${page}</div>
                %elif page < page_specs.page + pages_found:
                    <%
                       entries = page_specs.entries
                       offset = page_specs.entries * (page - 1)
                    %>
                    %if x == -2 and page > 1:
                        <div class="miss_pages">...</div>
                    %endif
                    <div class="page_button">${get_page_url( sort_id, order, *args, page=page, offset=offset, entries=entries )}</div>
                    %if x == 2 and pages_found == 4:
                        <div class="miss_pages">...</div>
                    %endif
                %endif
            %endif
        %endfor
        <div id="next_button">&#x21a0;</div>
    </div>
</%def>

<%def name="get_entry_selector(controller, action, entries, sort_id, order)">
    <div id="entry_form" >
        <form method="post" controller=${controller} action=${action}>
            <input type="hidden" value=${sort_id} name="sort_id">
            <input type="hidden" value=${order} name="order">
            Max items:
            <input id="entries_edit"
                   type="text"
                   name="entries"
                   value="${entries}">
            </input>
            <button id="entry_submit">Go</button>
        </form>
    </div>
</%def>

<%def name="get_page_css()">
    <%doc>
        Page Styling
    </%doc>
    <style>
        #back_button, #next_button, #curr_button, .miss_pages, .page_button {
            position: relative;
            float: left;
            height: 24px;
            width: 23px;
            margin: 0 -1px 0 0;
            padding-top: 2.5px;
            border: 1px solid #bfbfbf;
            z-index: 0;
        }
        
        #curr_button {
            background: #ebd9b2;
            border: 1px solid #5f6990;
            z-index: 1;
        }
        
        #back_button {
            cursor: pointer;
            border-top-left-radius: 3px;
            border-bottom-left-radius: 3px;
        }
        
        #next_button {
            cursor: pointer;
            border-top-right-radius: 3px;
            border-bottom-right-radius: 3px;
        }
        
        #page_selector {
            cursor: default;
            position: relative;
            text-align: center;
        }
        
        .page_button > a {
            text-decoration: none;
            padding: 8px;
            margin: -8px;
            height: 100%;
            width: 100%;
        }
        
        #formHeader > tbody > tr {
            vertical-align: middle;
        }
    </style>
    
    <%doc>
        Entry Styling
    </%doc>
    <style>
        
        #entries_edit {
            position: relative;
            padding: 0;
            width: 36px;
            height: 20px;
            text-align: center;
            border: 1px solid black;
            border-radius: 3px;
            z-index: 6;
        }
    
        #entry_submit {
            cursor: default;
            position: relative;
            display: inline-block;
            border: 1px solid black;
            padding: 0;
            width: 22px;
            height: 22px;
            border-radius: 11px;
            background-color: #ebd9b2;
            text-align: center;
            opacity: 0.0;
            z-index: 0;
        }
    </style>
</%def>

<%def name="get_page_script()">
    <script>
        $(document).ready( function(e) {
            var drop_down = false;
            
            //Close the dropdown in the event of focusout() from entries edit
            $("#entries_edit").focusout( function(e) {
                var speed = 50;
                
                $("#entry_submit").css("cursor", "default");
                $("#entry_submit").fadeTo(speed, 0.0);
                $(".st4").animate({top: "-=18px"}, {duration: speed, queue: false, complete: function() {
                    $(".st3").animate({top: "-=18px"}, {duration: speed, queue: false, complete: function() {
                        $(".st2").animate({top: "-=18px"}, {duration: speed, queue: false, complete: function() {
                            $(".st1").animate({top: "-=18px"}, {duration: speed, queue: false, complete: function() {
                                $(".st1").remove()
                            }});
                        }});
                    }});
                }});
                
                drop_down = false;
            });
            
            //Make sure the elements stay correctly positioned
            $("#formHeader").css("margin-left", $(".colored").css("margin-left"));
            $("#formHeader").css("width", $(".colored").css("width"));
            $(window).resize( function(e) {
                $("#formHeader").css("margin-left", $(".colored").css("margin-left"));
                $("#formHeader").css("width", $(".colored").css("width"));
                
                //Remove drop down for entry amount selection
                $(".st1").remove();
                $("#entry_submit").css("cursor", "default");
                $("#entry_submit").css("opacity", "0.0");
                $("#entry_submit").blur();
                
                drop_down = false;
            });
            
            //If there are pages to go back to, go back
            if( $("#curr_button").html() == 1) {
                $("#back_button").css( "cursor", "default" );
                $("#back_button").css( "color", "grey" );
            }
            $("#back_button").click( function(e) {
                if( $("#curr_button").html() != 1) {
                    window.open( $(".page_button:first").children().attr("href"), "_self" );
                }
            });
            
            //If there is a next page, go to the next page
            if( ${int(page_specs.pages_found)} == 1 ) {
                $("#next_button").css( "cursor", "default" );
                $("#next_button").css( "color", "grey" );
            }
            $("#next_button").click( function(e) {
                if( ${int(page_specs.pages_found)} > 1 ) {
                    window.open( $(".page_button:last").children().attr("href"), "_self" );
                }
            });
            
            //Select amount of entries per page
            $("#entry_form").on( "mousedown", ".st1", function(e) {
                e.preventDefault();
                $("#entries_edit").val( $(this).html() );
            });
            
            $("#entry_form").on("mouseenter", ".st1", function(e) {
                    $(this).css({
                        "border-color": "black",
                        "background-color": "#ebd9b2",
                    })
            });
            
            $("#entry_form").on("mouseleave", ".st1", function(e) {
                $(this).css({
                    "border-color": "grey",
                    "background-color": "white",
                })
            });
            
            $("#entries_edit").click( function(e) {
                if(!drop_down) {
                    //Initialize items
                    $("#entries_edit").parent().append("<div class=\"st1\"\">10</div>");
                    $("#entries_edit").parent().append("<div class=\"st1 st2\">25</div>");
                    $("#entries_edit").parent().append("<div class=\"st1 st2 st3\">50</div>");
                    $("#entries_edit").parent().append("<div class=\"st1 st2 st3 st4\">100</div>");
                    
                    $("#entry_submit").css("cursor", "pointer");
                    
                    var top_pos = $("#entries_edit").offset().top;
                    var left_pos = $("#entries_edit").offset().left;
                    $(".st1").css({
                        "cursor": "pointer",
                        "position": "absolute",
                        "text-align": "center",
                        "border": "1px solid grey",
                        "background-color": "white",
                        "margin-left": "3px",
                        "top": top_pos,
                        "left": left_pos,
                        "width": "30px",
                        "z-index": "4",
                    });
                    $(".st1").css({
                        "top": $("#entries_edit").offset().top,
                    });
                    $(".st2").css({"z-index": "3"})
                    $(".st3").css({"z-index": "2"})
                    $(".st4").css({
                        "z-index": "1",
                        "border-bottom-left-radius": "3px",
                        "border-bottom-right-radius": "3px",
                    });
                
                    //Anitmate items
                    var speed = 50;
                    $("#entry_submit").fadeTo(speed, 1.0);
                    $(".st1").animate({top: "+=18px"}, speed);
                    $(".st2").animate({top: "+=18px"}, speed);
                    $(".st3").animate({top: "+=18px"}, speed);
                    $(".st4").animate({top: "+=18px"}, speed);
                }
                
                drop_down = true;
            });
        });
    </script>
</%def>
