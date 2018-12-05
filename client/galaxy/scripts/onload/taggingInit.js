/**
 * Scripts transplanted from tagging_common.mako, should be packaged
 * with whatever tagging component we end up using
 */

import $ from "jquery";
import { show_in_overlay } from "layout/modal";
import { getConfig } from "onload/config";

export const taggingInit = (galaxy, config) => {
    console.log("Horrible tagging initialization", config);

    // Set links to Galaxy screencasts to open in overlay.
    $(this)
        .find("a[href^='http://screencast.g2.bx.psu.edu/']")
        .each(function() {
            $(this).click(function() {
                var href = $(this).attr("href");
                show_in_overlay({
                    url: href,
                    width: 640,
                    height: 480,
                    scroll: "no"
                });
                return false;
            });
        });

    // Init user item rating.
    $(".user_rating_star").rating({
        callback: function(rating, link) {
            let { ratingUrl, ratingId } = config.tags;

            let ajaxOptions = Object.assign(
                {},
                {
                    type: "GET",
                    url: ratingUrl,
                    data: { ratingId, rating },
                    dataType: "json",
                    error: function() {
                        alert("Rating submission failed");
                    },
                    success: function(community_data) {
                        $("#rating_feedback").show();
                        $("#num_ratings").text(Math.round(community_data[1] * 10) / 10);
                        $("#ave_rating").text(community_data[0]);
                        $(".community_rating_star").rating("readOnly", false);
                        $(".community_rating_star").rating("select", map_rating_to_num_stars(community_data[0]) - 1);
                        $(".community_rating_star").rating("readOnly", true);
                    }
                }
            );

            $.ajax(ajaxOptions);
        },
        required: true // Hide cancel button.
    });
};

// Map item rating to number of stars to show.
// TODO: Math.round?
function map_rating_to_num_stars(rating) {
    if (rating <= 0) return 0;
    else if (rating > 0 && rating <= 1.5) return 1;
    else if (rating > 1.5 && rating <= 2.5) return 2;
    else if (rating > 2.5 && rating <= 3.5) return 3;
    else if (rating > 3.5 && rating <= 4.5) return 4;
    else if (rating > 4.5) return 5;
}

// Handle click on community tag
// Gets assigned globally, but apparently is configured by python server, needs a config
// variable (tagLink) and it needs to be overridable by a python template

export function community_tag_click(tag_name, tag_value = "") {
    getConfig().then(config => {
        let href = `${config.tags.communityLinkPrefix}?f-tags=${tag_name}:${tag_value}`;
        window.location = href;
    });
}
