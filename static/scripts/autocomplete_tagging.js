/**
 * JQuery extension for tagging with autocomplete.
 * @author: Jeremy Goecks
 * @require: jquery.autocomplete plugin
 */
var ac_tag_area_id_gen = 1;

jQuery.fn.autocomplete_tagging = function(options) {

  //
  // Set up function defaults.
  //
  var defaults = 
  {
  get_toggle_link_text_fn: function(tags) 
  { 
    var text = "";
    var num_tags = array_length(tags);
    if (num_tags != 0)
	text = num_tags + (num_tags != 0 ? " Tags" : " Tag");
    else
	// No tags.
	text = "Add tags";
    return text;
  },
  tag_click_fn : function (tag) { },
  input_size: 20,
  in_form: false,
  tags : {},
  use_toggle_link: true,
  item_id: "",
  add_tag_img: "",
  add_tag_img_rollover: "",
  delete_tag_img: "",
  ajax_autocomplete_tag_url: "",
  ajax_retag_url: "",
  ajax_delete_tag_url: "",
  ajax_add_tag_url: ""
  };

  //
  // Extend object.
  //
  var settings = jQuery.extend(defaults, options);
  
  //
  // Create core elements: tag area and TODO.
  //
  
  // Tag area.
  var area_id = "tag-area-" + (ac_tag_area_id_gen)++;
  var tag_area = $("<div></div>").attr("id", area_id).addClass("tag-area");
  this.append(tag_area);
  
  //
  // Returns the number of keys (elements) in an array/dictionary.
  //
  var array_length = function(an_array)
  {
    if (an_array.length)
      return an_array.length;

    var count = 0;
    for (element in an_array)
      count++;
    return count;
  };
  
  //
  // Function to build toggle link.
  //
  var build_toggle_link = function()
  {
    var link_text = settings.get_toggle_link_text_fn(settings.tags);
    var toggle_link = $("<a href='/history/tags'>" + link_text + "</a>").addClass("toggle-link");
    // Link toggles the display state of the tag area.
    toggle_link.click( function() 
    { 
      // Take special actions depending on whether toggle is showing or hiding link.
      var showing_tag_area = (tag_area.css("display") == "none");
      var after_toggle_fn;
      if (showing_tag_area)
	{
	  after_toggle_fn = function() 
	    {
	      // If there are no tags, go right to editing mode by generating a 
	      // click on the area.
	      var num_tags = array_length(settings.tags);
	      if (num_tags == 0)
		tag_area.click();
	    };
	}
      else // Hiding area.
	{
	  after_toggle_fn = function() 
	    {
	      tag_area.blur();
	    };
	}
      tag_area.slideToggle("fast", after_toggle_fn);
      
      return false;
    });
    
    return toggle_link;
  };
  
  // Add toggle link.
  var toggle_link = build_toggle_link();
  if (settings.use_toggle_link)
    {
      this.prepend(toggle_link);
    }
    
  //
  // Function to build other elements.
  //

  //
  // Return a string that contains the contents of an associative array. This is
  // a debugging method.
  //
  var assoc_array_to_str = function(an_array)
  {
    // Convert associative array to simple array and then join array elements.
    var array_str_list = new Array();
    for (key in an_array)
      array_str_list[array_str_list.length] = key + "-->" + an_array[key];
    
    return "{" + array_str_list.join(",") + "}"
  };

  //  
  // Collapse tag name + value into a single string.
  //
  var build_tag_str = function(tag_name, tag_value)
  {
    return tag_name + ( (tag_value != "" && tag_value) ? ":" + tag_value : "");
  };
  
  //
  // Get tag name and value from a string.
  //
  var get_tag_name_and_value = function(tag_str)
  {
    return tag_str.split(":");
  };
  
  //
  // Add "add tag" button.
  //
  var build_add_tag_button = function(tag_input_field)
  {
    var add_tag_button = $("<img src='" + settings.add_tag_img + "' rollover='" + settings.add_tag_img_rollover + "'/>").addClass("add-tag-button");
   
    add_tag_button.click( function()
    {
      // Hide button.
      $(this).hide();
      
      // Clicking on button is the same as clicking on the tag area.
      tag_area.click();
      
      return false;
    });

    return add_tag_button;
  };

  //
  // Function that builds a tag button.
  //
  var build_tag_button = function(tag_str)
  {
    // Build "delete tag" image and handler.
    var delete_img = $("<img src='" + settings.delete_tag_img + "'/>").addClass("delete-tag-img");
    delete_img.mouseenter( function ()
    {
      $(this).attr("src", settings.delete_tag_img_rollover);
    });
    delete_img.mouseleave( function ()
    {
      $(this).attr("src", settings.delete_tag_img);
    });
    delete_img.click( function () 
    {
      // Tag button is image's parent.
      var tag_button = $(this).parent();
      
      // Get tag name, value.
      var tag_name_elt = tag_button.find(".tag-name").eq(0);
      var tag_str = tag_name_elt.text();
      var tag_name_and_value = get_tag_name_and_value(tag_str);
      var tag_name = tag_name_and_value[0];
      var tag_value = tag_name_and_value[1];

      var prev_button = tag_button.prev();
      tag_button.remove();

      // Remove tag from local list for consistency.
      delete settings.tags[tag_name];
      
      // Update toggle link text.
      var new_text = settings.get_toggle_link_text_fn(settings.tags);
      toggle_link.text(new_text);

      // Delete tag.
      $.ajax({
	url: settings.ajax_delete_tag_url,
	    data: { tag_name: tag_name },
	    error: function() 
	    { 
	      // Failed. Roll back changes and show alert.
	      settings.tags[tag_name] = tag_value;
	      if (prev_button.hasClass("tag-button"))
			prev_button.after(tag_button);
	      else
			tag_area.prepend(tag_button);
	      var new_text = settings.get_toggle_link_text_fn(settings.tags);
	      alert( "Remove tag failed" );
	
	      toggle_link.text(new_text);
		
	      // TODO: no idea why it's necessary to set this up again.
	      delete_img.mouseenter( function ()
	      {
		      $(this).attr("src", settings.delete_tag_img_rollover);
	      });
	      delete_img.mouseleave( function ()
	      {	
              $(this).attr("src", settings.delete_tag_img);
	      });
	    },
	    success: function() {}
      });

      return true;
    });

    // Build tag button.
    var tag_name_elt = $("<span>" + tag_str + "</span>").addClass("tag-name");
    tag_name_elt.click( function()
		       {
			  settings.tag_click_fn(tag_str);
			  return true;
		       });

    var tag_button = $("<span></span>").addClass("tag-button");
    tag_button.append(tag_name_elt);
    tag_button.append(delete_img);

    return tag_button;
  };

  //
  // Build input + autocompete for tag.
  //
  var build_tag_input = function(tag_text) 
  {
    // If element is in form, tag input is a textarea; otherwise element is a input type=text.
    var t;
    if (settings.in_form)
      t = $( "<textarea id='history-tag-input' rows='1' cols='" +
	    settings.input_size + "' value='" + tag_text + "'></textarea>" );
    else // element not in form.
      t = $( "<input id='history-tag-input' type='text' size='" +
	    settings.input_size + "' value='" + tag_text + "'></input>" );
    t.keyup( function( e ) 
    {
      if ( e.keyCode == 27 ) 
	{
	  // Escape key
	  $(this).trigger( "blur" );
	} else if (
		   ( e.keyCode == 13 ) || // Return Key
		   ( e.keyCode == 188 ) || // Comma
		   ( e.keyCode == 32 ) // Space
		   )
	{
	  //
	  // Check input.
	  //
	    
	  new_value = this.value;
	    
	  // Do nothing if return key was used to autocomplete.
	  if (return_key_pressed_for_autocomplete == true)
	    {
	      return_key_pressed_for_autocomplete = false;
	      return false;
	    }
	    
	  // Suppress space after a ":"
	  if ( new_value.indexOf(": ", new_value.length - 2) != -1)
	    {
	      this.value = new_value.substring(0, new_value.length-1);
	      return false;
	    }
	    	    
	  // Remove trigger keys from input.
	  if ( (e.keyCode == 188) || (e.keyCode == 32) )
	    new_value = new_value.substring( 0 , new_value.length - 1 );
	  
	  // Trim whitespace.
	  new_value = new_value.replace(/^\s+|\s+$/g,"");
	    
	  // Too short?
	  if (new_value.length < 3)
	    return false;
	    
	  //
	  // New tag OK - apply it.
	  //
	    
	  this.value = "";
	    
	  // Add button for tag after all other tag buttons.
	  var new_tag_button = build_tag_button(new_value);
	  var tag_buttons = tag_area.children(".tag-button");
	  if (tag_buttons.length != 0)
	    {
	      var last_tag_button = tag_buttons.slice(tag_buttons.length-1);
	      last_tag_button.after(new_tag_button);
	    }
	  else
	    tag_area.prepend(new_tag_button);

	  // Add tag to internal list.
	  var tag_name_and_value = new_value.split(":");
	  settings.tags[tag_name_and_value[0]] = tag_name_and_value[1];
	  
	  // Update toggle link text.
	  var new_text = settings.get_toggle_link_text_fn(settings.tags);
	  toggle_link.text(new_text);

	  // Commit tag to server.
	  var $this = $(this);
	  $.ajax({
	    url: settings.ajax_add_tag_url,
		data: { new_tag: new_value },
		error: function() 
		{
		  // Failed. Roll back changes and show alert.
		  new_tag_button.remove();
		  delete settings.tags[tag_name_and_value[0]];
		  var new_text = settings.get_toggle_link_text_fn(settings.tags);
		  toggle_link.text(new_text);
		  alert( "Add tag failed" );
		},
		success: function() 
		{
		  // Flush autocomplete cache because it's not out of date.
		  // TODO: in the future, we could remove the particular item
		  // that was chosen from the cache rather than flush it.
		  $this.flushCache();
		}
	  });
	 
	  return false;
	}
    });

    // Add autocomplete to input.
    var format_item_func = function(key, row_position, num_rows, value, search_term) {
      tag_name_and_value = value.split(":");
      return (tag_name_and_value.length == 1 ? tag_name_and_value[0] :tag_name_and_value[1]);
      //var array = new Array(key, value, row_position, num_rows,
      //search_term ); return "\"" + array.join("*") + "\"";
    }
    var autocomplete_options = 
    { selectFirst: false, formatItem : format_item_func, autoFill: false, highlight: false };
  
    t.autocomplete(settings.ajax_autocomplete_tag_url, autocomplete_options);
    
    t.addClass("tag-input");
    
    return t;
  };
  
  //
  // Build tag area.
  //

  // Add tag buttons for each current tag to the tag area.
  for (tag_name in settings.tags)
    {
      var tag_value = settings.tags[tag_name];
      var tag_str = build_tag_str(tag_name, tag_value);
      var tag_button = build_tag_button(tag_str, toggle_link, settings.tags);
      tag_area.append(tag_button);
    }
    
  // Add tag input field and "add tag" button.
  var tag_input_field = build_tag_input("");
  var add_tag_button = build_add_tag_button(tag_input_field);

  // When the tag area blurs, go to "view tag" mode.
  tag_area.blur( function(e) 
  {
    num_tags = array_length(settings.tags);
    if (num_tags != 0)
    {
      add_tag_button.show();
      tag_input_field.hide();
      tag_area.removeClass("active-tag-area");
    }
    else
    {
      // No tags, so do nothing to ensure that input is still visible.
    }
  });  
  
  tag_area.append(add_tag_button);
  tag_area.append(tag_input_field);
  tag_input_field.hide();
  
  // On click, enable user to add tags.
  tag_area.click( function(e) 
  {
    var is_active = $(this).hasClass("active-tag-area");

    // If a "delete image" object was pressed and area is inactive, do nothing.
    if ($(e.target).hasClass("delete-tag-img") && !is_active)
      return false;
    
    // If a "tag name" object was pressed and area is inactive, do nothing.
    if ($(e.target).hasClass("tag-name") && !is_active)
      return false;    

    // Hide add tag button, show tag_input field. Change background to show 
    // area is active.
    $(this).addClass("active-tag-area");
    add_tag_button.hide();
    tag_input_field.show();
    tag_input_field.focus();

    // Add handler to document that will call blur when the tag area is blurred;
    // a tag area is blurred when a user clicks on an element outside the area.
    var handle_document_click = function(e) 
      {
	var tag_area_id = tag_area.attr("id");
	// Blur the tag area if the element clicked on is not in the tag area.
	if ( 
	    ($(e.target).attr("id") != tag_area_id) &&
	    ($(e.target).parents().filter(tag_area_id).length == 0) 
	     )
	  {
	    tag_area.blur();
	    $(document).unbind("click", handle_document_click);
	  }    
      };
    // TODO: we should attach the click handler to all frames in order to capture
    // clicks outside the frame that this element is in.
    //window.parent.document.onclick = handle_document_click;
    //var temp = $(window.parent.document.body).contents().find("iframe").html();
    //alert(temp);
    //$(document).parent().click(handle_document_click);
    $(window).click(handle_document_click);
    
    return false;
  });
  
  // If using toggle link, hide the tag area. Otherwise, if there are no tags,
  // hide the "add tags" button and show the input field.
  if (settings.use_toggle_link)
    tag_area.hide();
  else 
    {
      var num_tags = array_length(settings.tags);
      if (num_tags == 0)
	{
	  add_tag_button.hide();
	  tag_input_field.show();
	}
    }
  
   
  return this.addClass("tag-element"); 
}
