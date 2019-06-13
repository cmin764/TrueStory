function load_articles() {
    var article_list = $("section#articleList");

    // Set an animation while loading.
    var load_btn = $("button#loadMoreReady").detach();
    $("button#loadMoreBusy").removeClass("d-none");

    // Fetch more articles through a GET request to the same page.
    var home_url = window.location.href;
    var cursor_input = $("input#queryCursor");
    $.get({
        url: home_url,
        data: {
            queryCursor: cursor_input.val()
        }
    }).done(function (recv_data) {
        // Get articles pair template first.
        var pair_tpl = article_list.find("div").first();
        // Display the newly received articles.
        var bp = recv_data["bias_pairs"];

        for (idx = 0; idx < bp.length; ++idx) {
            var update_map = {
                "left": bp[idx][0],
                "right": bp[idx][1]
            }
            var articles_pair = pair_tpl.clone();
            for (var pos in update_map) {
                var article = articles_pair.find("div.article-" + pos);
                var data = update_map[pos];

                article.find("a.article-usafe").attr("href", data["usafe"]);
                article.find("img.card-img").attr("src", data["image"]);
                article.find("h5.card-title").text(data["title"]);
                var summary = (
                    data["summary"] ? data["summary"] : data["content"]
                );
                article.find("p.article-summary").text(summary);
                article.find("span.article-source").text(data["source_name"]);
                article.find("small.article-published").text(data["published"]);
                article.find("span.article-authors").text(data["authors"]);
                article.find("cite").text(data["link"]);
            }

            article_list.append(articles_pair);
        }

        // Set the next cursor for future retrieval.
        var new_cursor = recv_data["new_cursor"];
        cursor_input.val(new_cursor);
    }).always(function () {
        // Revert back to the "Load more" button.
        $("button#loadMoreBusy").addClass("d-none");
        var to_put;
        var load_group = $("div#loadGroup");
        if (cursor_input.val()) {
            /* Put again the loading button, because we've got more data to
               load next. */
            to_put = load_btn;
        } else {
            /* Show "All Caught" message. */
            to_put = $("#loadMoreEmpty").detach();
            to_put.removeClass("d-none");
            load_group.removeClass("col-2");
            load_group.addClass("col-3 text-center");
        }
        load_group.prepend(to_put);
    });
}


function scroll_top() {
    $(window).scroll(function () {
        if ($(this).scrollTop()) {
            $("#toTop").fadeIn();
        } else {
            $("#toTop").fadeOut();
        }
    });

    $("#toTop").click(function () {
        $("html, body").animate({scrollTop: 0}, 200);
    });
}


function check_load_more() {
    if (! $("input#queryCursor").val()) {
        /* We've depleted all the queried articles from the beginning. */
        $("button#loadMoreReady").remove();
        var to_put = $("#loadMoreEmpty").detach();
        to_put.removeClass("d-none");

        var load_group = $("div#loadGroup");
        load_group.removeClass("col-2");
        load_group.addClass("col-3 text-center");

        /* Maybe we've searched for something and we've got no results at all.
        */
        var searched = Boolean($("input#querySearch").val());
        var results = Boolean($("section#articleList").find("div").length);
        if (searched && !results) {
            to_put.find("span#emptyText").text("No Articles Found");
        }

        load_group.prepend(to_put);
    }
}


to_load.push(scroll_top, check_load_more);
