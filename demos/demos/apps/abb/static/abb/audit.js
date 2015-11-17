$("#audit-button").click(function(e) {
    
    var audit_panel = $("#audit-panel");
    
    var input = $(this).closest(".input-group").find("input");
    var b_serial = input.val();
    
    if (!b_serial) {
        input.closest(".panel-input").removeClass("success error").addClass("warning");
        input.focus();
        return;
    }
    
    // Prepare the export url
    
    var b_url = e_url + "ballots/" + b_serial + "/";
    var b_query = "?ballot=parts&part=index,security_code,questions&question=" +
        "index,options&option=index," + (long_votecodes ? "l_" : "") + "votecode,voted";
    
    // Request the data from the server
    
    $.ajax({
        type: "GET",
        url: b_url + b_query,
        success: function(ballot, textStatus, jqXHR) {
            
            var panel_group1 = $(), panel_group2 = $();
            
            // Iterate over ballot's parts
            
            for (var p = 0, plen = ballot.parts.length; p < plen; p++) {
                
                var part = ballot.parts[p];
                var part2 = ballot.parts[1-p];
                
                var p_url = b_url + "parts/" + part.index + "/";
                
                var tabpane = $("#part-" + part.index.toLowerCase() + ".tab-pane");
                var panels = tabpane.find(".panel.hidden").clone(true).appendTo(tabpane);
                
                panel_group1 = panel_group1.add(panels);
                panel_group2 = panel_group2.add(tabpane.find(".panel:not(.hidden)"));
                
                // If a part has a security code, then the other part has been used to vote
                
                var p_vote = part.security_code ? part2.index : (part2.security_code ? part.index : "");
                
                if (p_vote == part.index)
                    panels.find("table").addClass("vote-col");
                else if (p_vote == part2.index)
                    panels.find("table").addClass("text-col");
                
                // Decode the security code
                
                var perm_bits, perm_index;
                var perm = part.security_code ? sjcl.bn.fromBits(sjcl.codec.base32cf.toBits(part.security_code)) : "";
                
                // Iterate over part's questions
                
                for (var q = 0, qlen = part.questions.length; q < qlen; q++) {
                    
                    var question = part.questions[q];
                    var q_url = p_url + "questions/" + question.index + "/";
                    
                    var table_rows = panels.eq(q).find("table > tbody > tr");
                    
                    if (!long_votecodes)
                        var vc_chars = ((question.options.length - 1) + "").length;
                    
                    // If the security code is available, restore options' correct order
                    
                    if (perm) {
                        
                        perm_bits = perm.add(question.index).toBits();
                        perm_bits = sjcl.hash.sha256.hash(perm_bits);
                        perm_index = sjcl.bn.fromBits(perm_bits);
                        
                        question.options = permute_ori(question.options, perm_index);
                    }
                    
                    // Iterate over question's options
                    
                    for (var o = 0, olen = question.options.length; o < olen; o++) {
                        
                        var option = question.options[o];
                        var o_url = q_url + "options/" + option.index + "/";
                        
                        var tr = table_rows.eq(o);
                        var col_votecode_span = tr.find(".votecode > span");
                        
                        // Populate votecode column
                        
                        var votecode = !long_votecodes ? 
                            zfill(option.votecode, vc_chars) : 
                            option.l_votecode ? sjcl.codec.base32cf.hyphen(option.l_votecode, 4) : "";
                        
                        if (votecode) {
                            col_votecode_span.removeClass();
                            col_votecode_span.text(votecode);
                            col_votecode_span.prop("aria-hidden", false);
                        }
                        
                        // Populate option column (with text or vote)
                        
                        var col_option = tr.find(".option");
                        var col_option_span = col_option.children("span");
                        
                        if (p_vote == part.index) {
                            col_option.prop("disabled", true);
                            col_option.toggleClass("hidden", !option.voted);
                        }
                        else if (p_vote == part2.index) {
                            col_option_span.removeClass();
                            col_option_span.prop("aria-hidden", false);
                            col_option_span.text(col_option.data("content"));
                            col_option.popover({container: "#part-" + part.index.toLowerCase() + " .panel-table .table", placement: "top", trigger: "click"});
                            col_option.on("show.bs.popover hide.bs.popover focusout", option_popover_handler);
                        }
                        else {
                            col_option.addClass("hidden");
                        }
                        
                        // Setup JSON modal's urls and click events
                        
                        tr.find(".com").data("url", o_url + "?option=com");
                        tr.find(".zk1").data("url", o_url + "?option=zk1");
                        tr.find(".zk2").data("url", o_url + "?option=zk2");
                        
                        tr.find(".votecode").data("url", o_url + "?option=receipt_full,"
                            + (!long_votecodes ? "votecode" : "l_votecode,l_votecode_hash"));
                        
                        /*tr.find(".votecode").data("url", !long_votecodes ? o_url + "?option=receipt_full,votecode" :
                            [o_url + "?option=receipt_full,l_votecode,l_votecode_hash", p_url + "?part=l_votecode_iterations,l_votecode_salt"]);*/
                        
                        tr.find(".com,.zk1,.zk2,.votecode").click(json_modal_click_handler);
                    }
                }
            }
            
            input.closest(".panel-input").removeClass("error warning");//.addClass("success");
            
            // Animate audit panel
            
            audit_panel.fadeOut({
                complete: function() {
                    panel_group2.remove();
                    panel_group1.removeClass("hidden");
                    audit_panel.find(".nav-tabs a[href='#part-a']").tab('show');
                },
            });
            
            audit_panel.fadeIn();
        },
        error: function(jqXHR, textStatus, errorThrown) {
            
            audit_panel.fadeOut();
            input.closest(".panel-input").removeClass("success warning").addClass("error");
            input.focus();
        }
    });
});

// -----------------------------------------------------------------------------

function option_popover_handler(e) {
    
    var button = $(e.target);
    var event = e.type + (e.namespace? "." + e.namespace : "");
    
    switch(event) {
        
        case "show.bs.popover":
            button.addClass("active");
            break;
        case "hide.bs.popover":
            button.removeClass("active");
            break;
        case "focusout":
            if (button.hasClass("active")) button.click();
            break;
    }
}

function json_modal_click_handler(e) {
    
    var modal = $("#json-modal");
    var mbody = modal.find(".modal-body");
    
    // Special case: if the same data is requested in a consecutive row, there
    // is no need to download them again. Just popup the modal dialog.
    
    var url = $(this).data("url");
    var cached_url = mbody.data("url");
    
    if (url == cached_url) {
        modal.modal("show");
        return;
    }
    
    // Otherwise, save the url (to check the special case later) and continue
    
    mbody.data("url", url);
    
    // Set modal title
    
    var votecode_btn = $(e.target);
    var col = votecode_btn.closest("td").index();
    var title = votecode_btn.closest("table").find("thead > tr > th:eq(" + col + ")").text();
    
    modal.find(".modal-title").text(title);
    
    // Disable the save button
    
    var save_btn = modal.find(".modal-footer button:not([data-dismiss='modal'])");
    save_btn.prop("disabled", true);
    
    // Start the spinner
    
    var spinner = mbody.children(".spinner");
    var spinner_d = spinner.data("spinner").spin();
    
    spinner.siblings().addClass("hidden");
    spinner.removeClass("hidden").prepend(spinner_d.el);
    
    // Popup the modal
    
    modal.modal("show");
    
    // Request the data from the server. Data 'url' can be a string or an array
    // of strings, whose returned objects will be merged.
    
    var data_f = {};
    var url_l = url instanceof Array ? url.slice() : new Array(url + "");
    
    var ajax_options = {
        type: "GET",
        success: function(data, textStatus, jqXHR) {
            
            // Merge returned data to the global object
            
            for (var attr in data) {
                data_f[attr] = data[attr];
            }
            
            // Continue if there are more links
            
            if (url_l.length > 0) {
                ajax_next_url();
                return;
            }
            
            // Add the data to the modal's body
            
            var pre = mbody.children("pre");
            
            pre.html(JSON.sortify(data_f, undefined, '    '));
            hljs.highlightBlock(pre.get(0));
            
            // Hide the spinner and enable the save button
            
            pre.removeClass("hidden");
            pre.siblings().addClass("hidden");
            
            save_btn.prop("disabled", false);
        },
        error: function(jqXHR, textStatus, errorThrown) {
            
            // Show an error message
            
            var error = mbody.children(".error");
            
            error.removeClass("hidden");
            error.siblings().addClass("hidden");
            
            modal.removeData("url");
        },
        complete: function(jqXHR, textStatus) {
            
            // Stop the spinner if and only if all urls have been consumed
            
            if (url_l.length == 0) {
                spinner.stop();
                mbody.removeData("xhr");
            }
        },
    };
    
    // Function to consume the next url
    
    var ajax_next_url = function() {
        
        ajax_options.url = url_l.pop();
        var xhr = $.ajax(ajax_options);
        mbody.data("xhr", xhr);
    }
    
    ajax_next_url();
}

$("#json-modal").on("hide.bs.modal", function(e) {
    
    var mbody = $(this).find(".modal-body");
    
    // Reset scrollbars
    
    var pre = mbody.children("pre");
    
    pre.scrollTop(0);
    pre.scrollLeft(0);
    
    // Abort any running ajax requests
    
    var xhr = mbody.data("xhr");
    
    if (xhr)
        xhr.abort();
});

$("#json-modal").on("hidden.bs.modal", function(e) {
    
    // Stop the spinner if it is still running
    
    var spinner = $(this).find(".modal-body > .spinner").data("spinner");
    
    if (spinner)
        spinner.stop();
});

$("#json-modal .modal-footer button:not([data-dismiss='modal'])").click(function(e) {
    
    // Offer the user to save the modal's json data. On some platforms the
    // 'download' attribute might not be supported and those users would not
    // get the correct filename and extension.
    
    var data = $("#json-modal .modal-body pre").text();
    var link = document.createElement("a");
    
    link.target = "_blank";
    link.download = "option.json";
    
    link.href = "data:application/octet-stream" +
        (typeof btoa !== "undefined" ? ";base64," + btoa(data) : "," + encodeURIComponent(data));
    
    link.click();
});

// -----------------------------------------------------------------------------

$("#audit-input").on("input change remove", function(e) {
    
    var input = $(this);
    
    input.closest(".panel-input").removeClass("success error warning");
    input.focus();
});

$("#audit-input").keypress(function(e) {
    
    if (e.which == 13) {
        $(this).closest(".input-group").find("button").click();
    }
});

// -----------------------------------------------------------------------------

$(".panel-input *").focusin(function(e) {
    $(this).closest(".panel-input").addClass("focus");
});

$(".panel-input *").focusout(function(e) {
    $(this).closest(".panel-input").removeClass("focus");
});

// -----------------------------------------------------------------------------

// Initialize spinners

var spinners = $(".spinner");
var spinner_opts = jQuery.extend(true, {}, def_spinner_opts);

spinner_opts.scale = 0.25;
spinner_opts.top = "25%";

$(".spinner").each(function(index) {
    var spinner = new Spinner(spinner_opts);
    $(this).data("spinner", spinner);
});

