$(window).load(function() {
    carousel_upd_all();
});

$(document).ready(function() {
    $(".alert-warning").addClass("hidden");
});

// -----------------------------------------------------------------------------

// Prepare carousel

var carousel = $("#carousel").carousel();

carousel.swipeleft(function() {  
    $(this).carousel("next");
});

carousel.swiperight(function() {  
    $(this).carousel("prev");
});

if (!carousel.data("wrap"))
    carousel.find(".carousel-control.left").addClass("disabled");

// -----------------------------------------------------------------------------

$(".page-header a").click(function(e) {
    $(this).toggleClass("active");
});

$("#vote-submit").tooltip({
    trigger: "manual",
    container: "body",
    placement: function() {
        switch ($("#vote-submit").parent().css("text-align")) {
            case "center": return "top";
            case "right": return "left";
            case "left": return "right";
            default: return "auto";
        }
    },
});

// -----------------------------------------------------------------------------

function ajax_error_ui_handler(jqXHR) {
    
    // Determine proper error state
    
    var state;
    
    if (jqXHR.status == 0)
        state = State.CONNECTION_ERROR;
    else if (jqXHR.hasOwnProperty("responseJSON") && jqXHR.responseJSON.hasOwnProperty("error"))
        state = jqXHR.responseJSON.error;
    else
        state = State.SERVER_ERROR;
    
    // Disable all options
    
    disable_voter_ui();
    
    // Display an alert with the the error message
    
    var alert_danger = $(".alert-danger");
    
    alert_danger.find("span[data-state='" + state + "']").removeClass("hidden");
    alert_danger.find("span:not([data-state='" + state + "'])").addClass("hidden");
    alert_danger.removeClass("hidden");
    
    // Scroll to the alert element
    
    $(".modal").each(function(e) {
        $(this).modal("hide");
    });
    
    $("html, body").animate({
        scrollTop: $("main").offset().top
    }, 400);
}

function disable_voter_ui() {
    
    var carousel = $("#carousel");
    var submit_btn = $("#vote-submit");
    var options = carousel.find("button.active");
    
    carousel.addClass("disabled");
    carousel.find("button").prop("disabled", true);
    
    options.attr("aria-pressed", false);
    options.find(".glyphicon").addClass("hidden");
    
    submit_btn.prop("disabled", true);
}

// -----------------------------------------------------------------------------

$(".option").click(function(e) {
    
    var option = $(this);
    var index = option.data("index");
    var selected = !option.hasClass("active");
    
    option.toggleClass("active");
    option.attr("aria-pressed", selected);
    option.find(".glyphicon").toggleClass("hidden", !selected);
    
    var question = option.closest(".question");
    var checked_queue = question.data("checked-queue");
    
    if (selected) {
        
        var choices = question.data("choices");
        var options = question.find(".option.active").not(this).length;
        
        if (options >= choices) {
            
            var last_index = checked_queue.shift();
            var last_selected = question.find(".option[data-index='" + last_index + "']");
            
            last_selected.removeClass("active");
            last_selected.attr("aria-pressed", false);
            last_selected.find(".glyphicon").addClass("hidden");
        }
        
        if (typeof checked_queue === "undefined") {
            
            checked_queue = new Array();
            question.data("checked-queue", checked_queue);
        }
        
        checked_queue.push(index);
    
    } else {
        
        var pos = checked_queue.indexOf(index);
        checked_queue.splice(pos, 1);
    }
});

// -----------------------------------------------------------------------------

$("#security-code-input").on("input", function(e) {
    
    var input = $(this);
    var value = input.val();
    
    var btn_ok = $("#security-code-ok");
    
    var form_group = input.closest(".form-group");
    var form_control = input.siblings(".form-control-feedback");
    
    var maxlen = input.prop("maxLength");
    
    // reset input if necessary
    
    if (value.length != maxlen) {
        
        security_code_state("reset");
        return;
    }
    
    // please wait spinner
            
    security_code_state("spin");
    
    // compute security code's hash
    
    var salt = input.data("salt");
    var iterations = input.data("iterations");
    
    try {
        value = sjcl.codec.base32crockford.normalize(value);
    }
    catch (err) {
        security_code_state("error");
        return;
    }
    
    var hash = sjcl.misc.pbkdf2(value, salt, iterations);
    hash = sjcl.codec.base32crockford.fromBits(hash);
    
    // request security code's verification
    
    $.ajax({
        type: "POST",
        data: {
            csrfmiddlewaretoken: csrfmiddlewaretoken,
            jsonfield: JSON.stringify({command: 'verify-security-code', hash: hash}),
        },
        success: function(data, textStatus, jqXHR) {
            
            // parse the security code
            
            security_code = sjcl.codec.base32crockford.toBits(value);
            var bits, perm = sjcl.bn.fromBits(security_code);
            
            // verify that data has the required number elements
            
            var questions = $(".question");
            
            if (questions.length != data.length)
                ajax_error_ui_handler(jqXHR);
            
            // iterate over questions
            
            for (var i = 0, ilen = data.length; i < ilen; i++) {
                
                var q_index = data[i][0];
                var q_votecodes = transpose(data[i][1]);
                
                // verify that data has the required number elements
                
                var question = questions.filter("[data-index='" + q_index + "']");
                
                if (question.length != 1)
                    ajax_error_ui_handler(jqXHR);
                
                // build the permutation index
                
                bits = perm.add(q_index).toBits();
                bits = sjcl.hash.sha256.hash(bits);
                var p_index = sjcl.bn.fromBits(bits);
                
                // restore votecodes' order
                
                var o_index_list = q_votecodes[0];
                var votecode_list = permute_ori(q_votecodes[1], p_index);
                
                // iterate over options
                
                for (var j = 0, jlen = o_index_list.length; j < jlen; j++) {
                    
                    // verify that data has the required number elements
                    
                    var option = question.find(".option[data-index='" + o_index_list[j] + "']");
                    
                    if (option.length != 1)
                        ajax_error_ui_handler(jqXHR);
                    
                    // assign the votecode to the option
                    
                    option.data("votecode", votecode_list[j]);
                }
            }
            
            security_code_state("success");
        },
        error: function(jqXHR, textStatus, errorThrown) {
            
            // forbidden or server error
            
            if (jqXHR.status == 403)
                security_code_state("error");
            else
                ajax_error_ui_handler(jqXHR);
        },
    });
});

function security_code_state(state) {
    
    var input = $("#security-code-input");
    var btn_ok = $("#security-code-ok");
    
    var form_group = input.closest(".form-group");
    var form_control = input.siblings(".form-control-feedback");
    
    form_group.removeClass("has-feedback has-success has-error");
    form_control.removeClass("glyphicon-ok glyphicon-remove glyphicon-refresh glyphicon-spin hidden");
    
    if (state == "success") {
        
        form_group.addClass("has-feedback has-success");
        form_control.addClass("glyphicon-ok");
        
        btn_ok.prop("disabled", false);
        input.prop("disabled", true);
        
        input.css("text-indent", "30px");
        btn_ok.focus();
        
    } else if (state == "error") {
        
        form_group.addClass("has-feedback has-error");
        form_control.addClass("glyphicon-remove");
        
        btn_ok.prop("disabled", true);
        input.prop("disabled", false);
        
        input.css("text-indent", "30px");
        input.focus();
        
    } else if (state == "spin") {
        
        form_group.addClass("has-feedback");
        form_control.addClass("glyphicon-refresh glyphicon-spin");
        
        btn_ok.prop("disabled", true);
        input.prop("disabled", true);
        
        input.css("text-indent", "30px");
        
    } else if (state == "reset")  {
        
        form_control.addClass("hidden");
        
        btn_ok.prop("disabled", true);
        input.prop("disabled", false);
        
        input.css("text-indent", "0px");
    }
}

$("#security-code-cancel").click(function(e) {
    
});

// -----------------------------------------------------------------------------

$("#vote-submit").click(function(e) {
    
    var questions = $(".question");
    
    // Check if the user has filled in all questions
    
    var filled_questions = 0;
    
    questions.each(function(index) {
        
        if ($(this).find(".option.active").length > 0) 
            filled_questions += 1;
    });
    
    if (filled_questions < questions.length) {
        
        // Not all questions have been filled in. Animate carousel's control
        // buttons to attract the user's attention and popup a tooltip.
        
        var controls = $(".carousel-control");
        controls.addClass("transform");
        
        window.setTimeout(function() {
            controls.removeClass("transform");
        }, 1500);
        
        $(this).tooltip("show");
        return;
    }
    
    // Now, fill in the confirm-modal with the user's selections
    
    function votecode_calc(question, option) {
        
        // short votecode version: just return the short votecode
        
        var votecode = option.data("votecode");
        if (vc_type == VcType.SHORT) return [votecode];
        
        // long votecode version: check if option already has a long votecode
        // (e.g.: the user may have clicked cancel before), if not, generate it
        
        var l_votecode = option.data("l_votecode");
        
        if (typeof l_votecode === "undefined") {
            
            var q_index = parseInt(question.data("index"));
            var msg_extra = (q_index * max_options) + votecode;
            
            var hmac = new sjcl.misc.hmac(security_code, sjcl.hash.sha256);
            hmac.update(sjcl.bn.fromBits(credential).add(msg_extra).toBits());
            
            l_votecode = sjcl.codec.base32crockford.fromBits(hmac.digest());
            l_votecode = l_votecode.slice(-votecode_len);
            
            option.data("l_votecode", l_votecode);
        }
        
        return [sjcl.codec.base32crockford.hyphen(l_votecode, 4)];
    }
    
    prep_modal_with_q(votecode_calc, "#confirm-modal");
});

$("#vote-submit").focusout(function(e) {
    $(this).tooltip("hide");
});

$("#vote-confirm").click(function(e) {
    
    $(this).siblings().addBack().prop("disabled", true);
    
    // Prepare vote data for the server. 'vote_obj' is an object of questions.
    // Each key is the question's index and each value is the list of votecodes.
    
    var vote_obj = {};
    
    $(".question").each(function(index) {
        
        var vc_list = new Array();
        var q_index = String($(this).data("index"));
        
        $(this).find(".option.active").each(function(index) {
            
            var votecode = (vc_type == VcType.SHORT) ?
                parseInt($(this).data("votecode")) :
                String($(this).data("l_votecode"));
            
            vc_list.push(votecode);
        });
        
        vote_obj[q_index] = vc_list;
    });
    
    // Now, send the votecodes to the server
    
    $.ajax({
        type: "POST",
        data: {
            csrfmiddlewaretoken: csrfmiddlewaretoken,
            jsonfield: JSON.stringify({command: 'vote', vote_obj: vote_obj}),
        },
        success: function(data, textStatus, jqXHR) {
            
            // Fill in the receipt-modal with the received receipts
            
            function receipt_calc(question, option) {
                
                var q_index = String(question.data("index"));
                
                var votecode = (vc_type == VcType.SHORT) ?
                    parseInt(option.data("votecode")) :
                    String(option.data("l_votecode"));
                
                var receipt = data[q_index].shift();
                
                if (vc_type == VcType.LONG)
                    votecode = sjcl.codec.base32crockford.hyphen(votecode, 4);
                
                return [votecode, receipt];
            }
            
            disable_voter_ui();
            prep_modal_with_q(receipt_calc, "#receipt-modal", "#confirm-modal");
        },
        error: function(jqXHR, textStatus, errorThrown) {
            
            ajax_error_ui_handler(jqXHR);
        },
    });
});

function prep_modal_with_q(callback, modal, old_modal) {
    
    var questions = $(".question");
    
    var modal = $(modal);
    var old_modal = (typeof old_modal !== "undefined") ? $(old_modal) : null;
    
    var base_panel = modal.find(".panel.hidden");
    modal.find(".panel:not(.hidden)").remove();
    
    questions.each(function(index) {
        
        var question = $(this);
        var panel = base_panel.clone();
        
        panel.removeClass("hidden");
        panel.insertBefore(base_panel);
        
        var table = panel.find("table > tbody");
        var heading = panel.find(".panel-heading");
        
        var index = question.data("index");
        var title = question.find(".title").text();
        
        heading.append(((questions.length > 1) ? (" " + (index + 1)) : ("")) + ": " + title);
        
        question.find(".option.active").each(function(index) {
            
            var row = "<td>" + $(this).text() + "</td>";
            var columns = callback(question, $(this));
            
            for (var i = 0, len = columns.length; i < len; i++)
                row += "<td>" + columns[i] + "</td>";
            
            table.append("<tr>" + row + "</tr>");
        });
    });
    
    if (old_modal) {
        
        old_modal.one("hidden.bs.modal", function(e) { modal.modal("show"); });
        old_modal.modal("hide");
        
    } else modal.modal("show");
}

$("#receipt-modal [data-dismiss='modal']").click(function(e) {
    
    $("#receipt-modal").modal("hide");
    $(".alert-success").removeClass("hidden");
    
    $("html, body").animate({
        scrollTop: $("main").offset().top
    }, 400);
});

// -----------------------------------------------------------------------------

$("#carousel").on("slide.bs.carousel", function(e) {
    
    var carousel = $(this);
    var item = $(e.relatedTarget);
    
    // Update controls for the new item
    
    var active = item.hasClass("active");
    
    item.addClass("active");
    carousel_upd_controls(item);
    
    if (!active);
        item.removeClass("active");
    
    // Animate the carousel
    
    carousel.find(".carousel-inner").animate({height: item.outerHeight()}, 500);
    
    // Enable/disable controls if on the first/last item
    
    if (!carousel.data("wrap")) {
        
        var control_left = carousel.find(".carousel-control.left");
        var control_right = carousel.find(".carousel-control.right");
        
        if(e.direction == "right" && $(e.relatedTarget).is(":nth-child(1)")) {
            control_left.addClass("disabled");
        } else if (e.direction == "left" && !$(e.relatedTarget).is(":nth-child(1)")) {
            control_left.removeClass("disabled");   
        }
        
        if (e.direction == "left" && $(e.relatedTarget).is(":nth-last-child(1)")) {
            control_right.addClass("disabled");
        } else if (e.direction == "right" && !$(e.relatedTarget).is(":nth-last-child(1)")) {
            control_right.removeClass("disabled");      
        }
    }
});

function carousel_upd_header(item) {
    
    var carousel = $("#carousel");
    var item = item || carousel.find(".item.active");
    
    // Calculate title span's width, needed by the flexbox for centering
    
    var h3 = item.find(".page-header > h3");
    var span = h3.children("span");
    
    h3.css("display", "inline");
    span.css("width", "");
    
    var width = span.width();
    
    h3.css("display", "");
    span.css("width", width);
}

function carousel_upd_controls(item) {
    
    var carousel = $("#carousel");
    var item = item || carousel.find(".item.active");
    var header = item.find(".page-header");
    
    carousel.find(".carousel-inner").css("height", "auto");
    
    var controls = carousel.find(".carousel-control");
    var min_width_768px = (parseInt($("#media-query-test").css("min-width")) >= 768);
    
    var width = min_width_768px ? item.css("padding-left") : (item.outerWidth() - header.width()) / 2;
    var height = min_width_768px ? "100%" : header.outerHeight() + parseInt(header.css("margin-top"));
    
    controls.css({"width": width, "height": height});
    controls.find(".glyphicon").css("top", "50%");
}

function carousel_upd_all() {
    
    $("#carousel .item").each(function(index) {
        
        var item = $(this);
        var active = item.hasClass("active");
        
        item.addClass("active");
        
        carousel_upd_header(item);
        
        if (!active)
            item.removeClass("active");
    });
    
    carousel_upd_controls();
}

$(window).resize(debounce(carousel_upd_all));

// -----------------------------------------------------------------------------

function transpose(a) {

    // Calculate the width and height of the Array
    var w = a.length ? a.length : 0,
        h = a[0] instanceof Array ? a[0].length : 0;

    // In case it is a zero matrix, no transpose routine needed.
    if(h === 0 || w === 0) { return []; }
    
    var i, j, t = [];

    // Loop through every item in the outer array (height)
    for(i=0; i<h; i++) {

        // Insert a new row (array)
        t[i] = [];

        // Loop through every item per item in outer array (width)
        for(j=0; j<w; j++) {

            // Save transposed data.
            t[i][j] = a[j][i];
        }
    }

    return t;
};
