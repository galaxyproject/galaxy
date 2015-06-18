<%def name="get_page_url( sort_id, order, *args, **kwargs )">
        <a href="${h.url_for( controller=args[0], action=args[1], sort_id=sort_id, order=order, **kwargs )}">${kwargs.get("page")}</a>
</%def>

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
    </div><br/><br/>
</%def>

<%def name="get_page_css()">
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
            vertical-align: bottom;
        }
    </style>
</%def>

<%def name="get_page_script()">
    <script>
        $(document).ready( function(e) {
            $("#formHeader").css("margin-left", $(".colored").css("margin-left"))
            $("#formHeader").css("width", $(".colored").css("width"))

            $(window).resize( function(e) {
                $("#formHeader").css("margin-left", $(".colored").css("margin-left"))
                $("#formHeader").css("width", $(".colored").css("width"))
            })
            
            if( $("#curr_button").html() == 1) {
                $("#back_button").css( "cursor", "default" )
                $("#back_button").css( "color", "grey" )
            }
            $("#back_button").click( function(e) {
                if( $("#curr_button").html() != 1) {
                    window.open( $(".page_button:first").children().attr("href"), "_self" );
                }
            })
            
            if( ${int(page_specs.pages_found)} == 1 ) {
                $("#next_button").css( "cursor", "default" )
                $("#next_button").css( "color", "grey" )
            }
            $("#next_button").click( function(e) {
                if( ${int(page_specs.pages_found)} != 1 ) {
                    window.open( $(".page_button:last").children().attr("href"), "_self" );
                }
            })
        })
    </script>
</%def>
