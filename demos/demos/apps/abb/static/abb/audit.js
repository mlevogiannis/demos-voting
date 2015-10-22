$("#audit-button").click(function(e) {
    
    var audit_panel = $("#audit-panel");
    var input = $(this).closest(".input-group").find("input");
    
    var serial = input.val();
    
    if (!serial) {
        input.closest(".panel-input").removeClass("success error").addClass("warning");
        input.focus();
        return;
    }
    
    $.ajax({
        type: "POST",
        data: {
            serial: serial,
            csrfmiddlewaretoken: csrfmiddlewaretoken
        },
        success: function(data, textStatus, jqXHR) {
            
            var panel_group1 = $(), panel_group2 = $();
            
            var b_url = data.url;
            var b_vote = data.vote;
            var b_parts = data.parts;
            
            for (var p = 0, plen = b_parts.length; p < plen; p++) {
                
                var p_tag = b_parts[p][0];
                var p_questions = b_parts[p][1];
                var p_url = b_url + "parts/" + p_tag + "/";
                
                var tabpane = $("#part-" + p_tag.toLowerCase() + ".tab-pane");
                var panels = tabpane.find(".panel.hidden").clone(true).appendTo(tabpane);
                
                panel_group1 = panel_group1.add(panels);
                panel_group2 = panel_group2.add(tabpane.find(".panel:not(.hidden)"));
                
                if (b_vote != null && b_vote == p_tag)
                    panels.find("table").addClass("vote-col");
                else if (b_vote != null && b_vote != p_tag)
                    panels.find("table").addClass("option-col");
                
                for (var q = 0, qlen = p_questions.length; q < qlen; q++) {
                    
                    var q_index = p_questions[q][0];
                    var q_options = p_questions[q][1];
                    var q_url = p_url + "questions/" + q_index + "/";
                    
                    var trs = panels.eq(q_index).find("table > tbody > tr");
                    var vc_chars = ((q_options.length - 1) + "").length;
                    
                    for (var o = 0, olen = q_options.length; o < olen; o++) {
                        
                        var o_index = q_options[o][0];
                        var o_votecode = q_options[o][1];
                        var o_voted = q_options[o][2];
                        var o_url = q_url + "options/" + o_index + "/";
                        
                        var tr = trs.eq(o);
                        
                        tr.find(".votecode > span").text(zfill(o_votecode, vc_chars));
                        
                        if (b_vote != null) {
                            
                            var tr_voted = tr.find(".voted");
                            var tr_voted_span = tr_voted.children("span");
                            
                            if (b_vote != p_tag) {
                                
                                var text = tr.data("text");
                                
                                tr_voted_span.text(text);
                                tr_voted.tooltip({title: text, trigger: "manual"});
                                
                                tr_voted.removeClass("hidden");
                                tr_voted.hover(option_tooltip_in, option_tooltip_out);
                                
                            } else if (b_vote == p_tag && o_voted == true) {
                                
                                tr_voted.removeClass("hidden");
                                tr_voted_span.prop("aria-hidden", true);
                                tr_voted_span.addClass("glyphicon glyphicon-ok");
                            }
                        }
                        
                        var jsonfields = ['com', 'zk1', 'zk2'];
                        
                        for (var cls in jsonfields) {
                            
                            var button = tr.find("." + jsonfields[cls]);
                            
                            button.data("url", o_url + "?option=" + jsonfields[cls]);
                            button.click(json_viewer);
                        }
                    }
                }
            }
            
            input.closest(".panel-input").removeClass("error warning");//.addClass("success");
            
            // Update audit panel
            
            audit_panel.fadeOut({
                complete: function() {
                    panel_group2.find("voted").tooltip("destroy");
                    panel_group2.remove();
                    panel_group1.removeClass("hidden");
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

function option_tooltip_in(e) {
    
    var button = $(this);
    var span = button.children("span");
    
    if (button.width() < span.width()) {
        button.tooltip("show");
    }
}

function option_tooltip_out(e) {
    
    $(this).tooltip("hide");
}

function json_viewer(e) {
    
    var modal = $("#json-viewer");
    var mbody = modal.find(".modal-body");
    var mcontent = modal.find(".modal-content");
    
    // Check if we already have the requested data
    
    var url = $(this).data("url");
    var cached_url = modal.data("cached-url");
    
    if (url == cached_url) {
        modal.modal("show");
        return;
    }
    
    modal.data("cached-url", url);
    
    // Set modal title
    
    var button = $(e.target);
    var mtitle = modal.find(".modal-title");
    
    mtitle.text(button.closest("table").find("thead > tr > th:eq(" + button.closest("td").index() + ")").text());
    
    // Initialize loading spinner
    
    var spinner = mcontent.data("spinner");
    
    if (!spinner) {
        
        var spinner_opts = def_spinner_opts;
        
        spinner_opts.scale = 0.25;
        spinner_opts.top = "25%";

        spinner = new Spinner(spinner_opts);
        mcontent.data("spinner", spinner);
    }
    
    spinner = spinner.spin();
    
    mbody.children(":not(.spinner)").addClass("hidden");
    mbody.children(".spinner").removeClass("hidden").prepend(spinner.el);
    
    // Show the modal and request the dta from the server
    
    modal.find("a").addClass("disabled");
    modal.modal("show");
    
    var xhr = $.ajax({
        url: url,
        type: "GET",
        success: function(data, textStatus, jqXHR) {
            
            var json = JSON.stringify(data, undefined, '    ');
            
            // JSON syntax highlight
            // Source: http://stackoverflow.com/a/7220510
            
            json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            json = json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
                var cls = 'number';
                if (/^"/.test(match)) {
                    if (/:$/.test(match)) {
                        cls = 'key';
                    } else {
                        cls = 'string';
                    }
                } else if (/true|false/.test(match)) {
                    cls = 'boolean';
                } else if (/null/.test(match)) {
                    cls = 'null';
                }
                return '<span class="' + cls + '">' + match + '</span>';
            });
            
            modal.find("pre").html(json);
            modal.find("a").attr("href", url + "&file=true");
            
            mbody.children(":not(pre)").addClass("hidden");
            mbody.children("pre").removeClass("hidden");
            
            modal.find("a").removeClass("disabled");
        },
        error: function(jqXHR, textStatus, errorThrown) {
            
            mbody.children(":not(.error)").addClass("hidden");
            mbody.children(".error").removeClass("hidden");
        },
        complete: function(jqXHR, textStatus) {
            
            spinner.stop();
            mcontent.removeData("xhr spinner");
        },
    });
    
    mcontent.data("xhr", xhr);
}

$("#json-viewer").on("hidden.bs.modal", function(e) {
    
    var mcontent = $(this).closest(".modal-content");
    
    var xhr = mcontent.data("xhr");
    var spinner = mcontent.data("spinner");
    
    if (xhr)
        xhr.abort();
    
    if (spinner)
        spinner.stop();
});

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
