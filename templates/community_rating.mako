<%
    label = "ratings"
    if num_ratings == 1:
        label = "rating"
%>
<div>
    <input name="star1-${item_id}" type="radio" class="community_rating_star star" disabled="disabled" value="1"
    %if ave_item_rating > 0 and ave_item_rating <= 1.5:
        checked="checked"
    %endif
    
    />
    <input name="star1-${item_id}" type="radio" class="community_rating_star star" disabled="disabled" value="2"
    %if ave_item_rating > 1.5 and ave_item_rating <= 2.5:
        checked="checked"
    %endif
    />
    <input name="star1-${item_id}" type="radio" class="community_rating_star star" disabled="disabled" value="3"
    %if ave_item_rating > 2.5 and ave_item_rating <= 3.5:
        checked="checked"
    %endif
    />
    <input name="star1-${item_id}" type="radio" class="community_rating_star star" disabled="disabled" value="4"
    %if ave_item_rating > 3.5 and ave_item_rating <= 4.5:
        checked="checked"
    %endif
    />
    <input name="star1-${item_id}" type="radio" class="community_rating_star star" disabled="disabled" value="5"
    %if ave_item_rating > 4.5:
        checked="checked"
    %endif
    />
</div>
