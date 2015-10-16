// Datetimepickers -------------------------------------------------------------

var datetime_now = moment().seconds(0);
var datetime_format = "ddd, D MMM YYYY, HH:mm";

$(".date").each(function(index, element) {
	
	// Set datetimepickers' current, default and minimum date/time
	
	var datetime_picker = $(element);
	var datetime_iso8601 = datetime_picker.siblings(".datetime-iso8601-input").val();
	var datetime_local = moment(datetime_iso8601);
	
	datetime_picker.datetimepicker({
		sideBySide: false,
		minDate: datetime_now.clone().startOf("day"),
		format: datetime_format,
	});
	
	var minutes = (Math.ceil(datetime_now.minute() / 5) * 5) + 5 * index;
	var datetime_default = datetime_now.clone().minutes(minutes);
	
	datetime_picker.data("DateTimePicker").defaultDate(datetime_default);
	
	datetime_local = datetime_local.isValid() ? datetime_local.format(datetime_format) : "";
	datetime_picker.children("input").val(datetime_local);
});

function update_datetime_iso8601() {
	
	// Convert datetimepickers' input to ISO8601 format
	
	$(".date").each(function(index, element) {
		
		var datetime_picker = $(element);
		var datetime_local = datetime_picker.children("input").val();
		var datetime_iso8601 = datetime_local ? moment(datetime_local, datetime_format).format() : "";
		
		datetime_picker.siblings(".datetime-iso8601-input").val(datetime_iso8601);
	});
}

$("form").submit(update_datetime_iso8601);

$(".date [data-toggle='tooltip']").click(function(e) {
	$(this).tooltip("hide");
});

// Question sortable -----------------------------------------------------------

$("#question-table tbody").sortable({
	start: function(event, ui) {
		$(ui.item).find("[data-toggle='tooltip']").tooltip("hide");
	},
	update: function(event, ui) {
		update_question_table();
	},
	helper: function(event, element) {
		
		var helper = element.clone();
		var originals = element.children();
		
		helper.children().each(function(index) {
			
			if (!$(this).hasClass("active success warning danger info")) {
				$(this).addClass("active");
			}
			
			$(this).width(originals.eq(index).width());
		});
		
		return helper;
	},
	placeholder: "question-sortable-placeholder",
});

// Question control buttons ----------------------------------------------------

$("#question-add").click(function(e) {
	
	// Clone base question (identified by __prefix__)
	
	var question = $(".question[data-index='__prefix__']").clone(true);
	var question_entry = $(".question-entry[data-index='__prefix__']").clone(true);
	
	$(this).tooltip("hide");
	question_entry.find("[data-toggle='tooltip']").removeData("bs.tooltip");
	
	question.appendTo("form");
	question_entry.insertBefore(".question-entry:last");
	
	question.removeData("question-data");
	
	// Update question table and option list
	
	update_question_table();
	update_option_list(question);
	register_option_sortable(question);
	
	show_question(question);
});

$(".question-remove").click(function(e) {
	
	var question_entry = $(this).closest(".question-entry");
	var index = question_entry.attr("data-index");
	var question = $(".question[data-index='" + index + "']");
	
	$(this).tooltip("destroy");
	
	// Remove question and its table entry
	
	question_entry.remove();
	update_question_table();
	
	question.remove();
});

$(".question-entry").click(function(e) {
	
	var question_entry = $(this);
	var index = question_entry.attr("data-index");
	var question = $(".question[data-index='" + index + "']");
	
	// Make a copy of the question for later restoration
	
	question.find(".option-list").sortable("destroy");
	
	var question_data = question.clone(true);
	
	register_option_sortable(question);
	register_option_sortable(question_data);
	
	question.find("select").each(function(index, element) {
		
		var value = $(this).val();
		
		if (value !== null) {
			question_data.find("select").eq(index).val(value);
		}
	});
	
	question.data("question-data", question_data);
	show_question(question);
});

$(".question-save").click(function(e) {
	
	var question = $(this).closest("#question-modal").find(".question");
	var index = question.attr("data-index");
	var question_entry = $(".question-entry[data-index='" + index + "']");
	
	// Update question's table entry
	
	var value = question.find("input:first").val();
	
	question_entry.removeClass("hidden");
	question_entry.children("td:first").text(value);
	
	if (question.find(".form-group.has-error").length == 0) {
		
		question_entry.removeClass("danger");
		
		if (question_entry.siblings(".danger").length == 0) {
			question_entry.closest(".group-wrapper").find(".alert").alert("close");
		}
	}
	
	question.removeData("question-data");
	hide_question(question);
});

$(".question-cancel").click(function(e) {
	
	var question = $(this).closest("#question-modal").find(".question");
	var index = question.attr("data-index");
	var question_entry = $(".question-entry[data-index='" + index + "']");
	
	var question_data = question.data("question-data");
	
	// Delete or restore question
	
	if (typeof question_data === "undefined") {
		
		hide_question(question, function() {
			question_entry.find(".question-remove").trigger("click");
		});
		
	} else {
		
		question.removeData("question-data");
		
		hide_question(question, function() {
			question.replaceWith(question_data);
		});
	}
});

// Question show/hide functions ------------------------------------------------

function show_question(question) {
	
	var question_modal = $("#question-modal");
	
	question.appendTo(question_modal.find(".modal-body"));
	question.removeClass("hidden");
	
	var modal_title = question_modal.find(".modal-title");
	var title = modal_title.data((typeof question.data("question-data") === "undefined") ? "add-title" : "edit-title");
	
	modal_title.text(title);
	question_modal.modal("show");
}

function hide_question(question, complete_f) {
	
	var question_modal = $("#question-modal");
	
	question_modal.one("hidden.bs.modal", function() {
		
		question.addClass("hidden");
		question_modal.find(".modal-body > .question").appendTo("form");
		
		if (typeof complete_f !== "undefined") {
			complete_f();
		}
	});
	
	question_modal.modal("hide");
}

// Question order update -------------------------------------------------------

function update_question_table() {
	
	// Create a map of the questions to be updated
	
	var question_table = $(".question-entry:not(:last)").map(function() {
		
		var question_entry = $(this);
		
		var new_index = question_entry.index();
		var old_index = question_entry.attr("data-index");
		
		// If the index has not changed, ignore the question
		
		if (old_index == new_index)
			return null;
		
		// Otherwise, mark the question for update
		
		var dict = {
			
			"question": $("form .question[data-index='" + old_index + "']"),
			"question_entry": question_entry,
		    "new_index": new_index,
		};
		
		return dict;
	});
	
	// Update each question of the question table
	
	question_table.each(function() {
		
		var question = this["question"];
		var question_entry = this["question_entry"];
		var new_index = this["new_index"];
		
		// Update the question's indexes
		
		question.attr("data-index", new_index);
		question_entry.attr("data-index", new_index);
		
		// Function to replace 'old_index' or '__prefix__' with 'new_index'
		
		function replace_f(field, field_attr, field_index) {
			
			field.attr(field_attr, function(index, attr) {
				
				// Updates question's index or option's prefix
				
				var re = /(question-|option)(?:__prefix__|\d+)/;
				return attr.replace(re, "$1" + field_index);
			});
		}
		
		// Update 'id', 'name' and 'for' attributes
		
		question.find("input, select, label").each(function(e) {
			
			if (typeof $(this).attr("id") !== "undefined") {
				replace_f($(this), "id", new_index);
			}
			
			if (typeof $(this).attr("name") !== "undefined") {
				replace_f($(this), "name", new_index);
			}
			
			if (typeof $(this).attr("for") !== "undefined") {
				replace_f($(this), "for", new_index);
			}
		});
		
		// Update table's first column
		
		question_entry.children("th").text(new_index + 1);
	});
	
	// Update TOTAL_FORMS value and add-button's state
	
	var maximum = management_form_max("question");
	var questions = $(".question-entry:not(:last)").length;
	
	management_form_total("question", questions);
	$("#question-add").prop("disabled", !(questions < maximum));
}

// Option sortable -------------------------------------------------------------

function register_option_sortable(question) {
	
	question.find(".option-list").sortable({
		start: function(event, ui) {
			$(ui.item).find("[data-toggle='tooltip']").tooltip("destroy");
		},
		stop: function(event, ui) {
			$(ui.item).find("[data-toggle='tooltip']").tooltip();
		},
		update: function(event, ui) {
			update_option_list($(ui.item).closest(".question"));
		},
		placeholder: "option-sortable-placeholder",
	});
}

// Option control buttons ------------------------------------------------------

$(".option-add").click(function(e) {
	
	var question = $(this).closest(".question");
	var option_prefix = "option" + question.attr("data-index");
	
	// Check if a new option can be added
	
	var option_max = management_form_max(option_prefix);
	var option_total = management_form_total(option_prefix);
	
	if (option_total >= option_max)
		return;
	
	// Clone the last option
	
	var new_option = question.find(".option:last").clone("true");
	new_option.find("[data-toggle='tooltip']").removeData("bs.tooltip");
	
	new_option.appendTo(question.find(".option-list"));
	
	new_option.find("input").val("");
	new_option.find(".form-group").removeClass("has-error");
	
	// Update option_list
	
	update_option_list(question);
	
	// Scroll the page
	
	$("#question-modal").scrollTop($("#question-modal").scrollTop() + new_option.height() + 15); 
});

$(".option-remove").click(function(e) {
	
	var option = $(this).closest(".option");
	var question = $(this).closest(".question");
	
	var option_prefix = "option" + question.attr("data-index");
	
	// Check if the option can be removed
	
	var option_min = management_form_min(option_prefix);
	var option_total = management_form_total(option_prefix);
	
	if (option_total <= option_min)
		return;
	
	$(this).tooltip("destroy");
	option.remove();
	
	// Update option_list
	
	update_option_list(question);
});

// Option order update -------------------------------------------------------

function update_option_list(question) {
	
	var option_list = question.find(".option");
	var option_prefix = "option" + question.attr("data-index");
	
	// Update each option in the option list
	
	option_list.each(function() {
		
		var option = $(this);
		var new_index = option.index();
		
		// Function to replace 'old_index' with 'new_index'
		
		function replace_f(field, field_attr, field_index) {
			
			field.attr(field_attr, function(index, attr) {
				
				// Update option's index
				
				var re = /(option(?:__prefix__|\d+)-)\d+/;
				return attr.replace(re, "$1" + field_index);
			});
		}
		
		// Update 'id', 'name' and 'for' attributes
		
		option.find("input").each(function(i, e) {
			replace_f($(this), "id", new_index);
			replace_f($(this), "name", new_index);
		});
		
		option.find("label").each(function(i, e) {
			replace_f($(this), "for", new_index);
		});
		
		// Update labels
		
		var labels = option.find("label").add(option.find("input").prev());
		
		labels.each(function(i, e) {
			$(this).text($(this).text().replace(/\d+/, new_index + 1));
		});
	});
	
	// Update TOTAL_FORMS value and add-button's state
	
	var options = option_list.length;
	var maximum = management_form_max(option_prefix);
	
	management_form_total(option_prefix, options);
	question.find(".option-add").prop("disabled", !(options < maximum));
	
	// Update multiple choice input's value
	
	var input = question.find(".input-group-spinner > input");
	var val = input.val();
	
	input.prop("max", options);
	input.val(val < options ? val : options);
	input.trigger("change");
	
	// Handle modal height change (if any)
	
	var question_modal = $("#question-modal");
	
	if (question_modal.length > 0) {
		question_modal.modal("handleUpdate");
	}
}

/*function update_multiple_choice_select(question) {
	
	var option_prefix = "option" + question.attr("data-index");
	var option_total = management_form_total(option_prefix);
	
	var select_input = question.find(".multiple-choice-select");
	var select_options = select_input.find("option:not(:first)");
	
	var value = parseInt(select_input.val());
	
	if (select_options.length < option_total) {
		
		var i = parseInt(select_input.find("option:last").val()) + 1;
		if (isNaN(i)) {i = 1; select_options.remove();}
		
		for (; i <= option_total; i++)
			select_input.append($("<option>", {value: i, text : i}));
		
	} else if (select_options.length > option_total) {
		
		select_input.find("option:gt(" + option_total + ")").remove();
		
		if (!isNaN(value))
			select_input.val(value < option_total ? value : option_total);
	}
}*/

// ManagementForm functions ----------------------------------------------------

function management_form_total(prefix, value) {
	
	// Return or update ManagementForm's TOTAL_FORMS value
	
	var total_forms = $("#id_" + prefix + "-TOTAL_FORMS");
	
	if (typeof value !== "undefined")
		total_forms.val(value);
	
	return parseInt(total_forms.val());
}

function management_form_min(prefix) {
	
	// Return ManagementForm's MIN_NUM_FORMS value
	
	return parseInt($("#id_" + prefix + "-MIN_NUM_FORMS").val());
}

function management_form_max(prefix) {
	
	// Return ManagementForm's MAX_NUM_FORMS value
	
	return parseInt($("#id_" + prefix + "-MAX_NUM_FORMS").val());
}

// Ballot preview --------------------------------------------------------------

$(":input, .date").on("remove change update dp.change dp.update", function(e) {
	$("form").data("has-changed", true);
});

$("#question-add, .question-remove").click(function(e) {
	$("form").data("has-changed", true);
});

$("#ballot-preview").click(function(e) {
	
	var form = $("form");
	var modal = $("#pdf-modal");
	
	var mbody = modal.find(".modal-body");
	var mfooter = modal.find(".modal-footer");
	var mdialog = modal.find(".modal-dialog");
	var mcontent = modal.find(".modal-content");
	
	if (typeof form.data("has-changed") !== "undefined" && !form.data("has-changed")) {
		modal.modal("show");
		return;
	}
	
	mdialog.removeClass("modal-lg modal-pdf");
	mfooter.children(".pdf-open").prop("disabled", true);
	
	var spinner = mcontent.data("spinner");
	
	if (!spinner) {
		
		var spinner_opts = def_spinner_opts;
		
		spinner_opts.scale = 0.25;
		spinner_opts.top = "25%";

		spinner = new Spinner(spinner_opts);
		mcontent.data("spinner", spinner);
	}
	
	spinner = spinner.spin();
	
	mbody.children(".pdf-spinner").removeClass("hidden").prepend(spinner.el);
	mbody.children(":not(.pdf-spinner)").addClass("hidden");
	
	modal.modal("show");
	
	update_datetime_iso8601();
	
	var xhr = $.ajax({
		type: "POST",
		data: form.serialize(),
		success: function(data, textStatus, jqXHR) {
			
			var state;
			
			try { state = (typeof navigator.mimeTypes["application/pdf"] !== "undefined"); }
			catch(e) { state = true; }
			
			mdialog.toggleClass("modal-lg modal-pdf", state);
			
			var object = mbody.find("object");
			var link = object.find("a");
			
			var data_uri = "data:application/pdf;base64," + escape(data);
			
			object.attr("data", data_uri);
			link.attr("href", data_uri);
			
			form.data("has-changed", false);
			
			mbody.children(".pdf-object").removeClass("hidden");
			mbody.children(":not(.pdf-object)").addClass("hidden");
			
			mfooter.children(".pdf-open").prop("disabled", !state);
		},
		error: function(jqXHR, textStatus, errorThrown) {
			
			if (jqXHR.status == 422) {
				
				var form_with_errors = $(jqXHR.responseText).find("form");
				
				mbody.children(".pdf-form-error").removeClass("hidden");
				mbody.children(":not(.pdf-form-error)").addClass("hidden");
				
				var selector1 = "#election .form-group";
				
				form.find(selector1).each(function(index, element) {
					
					var old_group = $(element);
					var new_group = form_with_errors.find(selector1).eq(index);
					
					var state = new_group.hasClass("has-error");
					old_group.toggleClass("has-error", state);
				});
				
				var selector2 = "#election, #question-table";
				
				form.find(selector2).each(function(index, element) {
					
					var old_wrapper = $(element);
					var new_wrapper = form_with_errors.find(selector2).eq(index);
					
					old_wrapper.find(".alert-wrapper").each(function(index, element) {
						
						var old_alert = $(element);
						var new_alert = new_wrapper.find(".alert-wrapper").eq(index);
						
						old_alert.replaceWith(new_alert);
					});
				});
				
				var selector3 = ".question-entry:not(:last)";
				
				form.find(selector3).each(function(index, element) {
					
					var old_entry = $(element);
					var new_entry = form_with_errors.find(selector3).eq(index);
					
					var state = new_entry.hasClass("danger");
					old_entry.toggleClass("danger", state);
					
					var old_index = old_entry.attr("data-index");
					var old_question = form.find(".question[data-index='" + old_index + "']");
					
					var new_index = new_entry.attr("data-index");
					var new_question = form_with_errors.find(".question[data-index='" + new_index + "']");
					
					old_question.find(".group-wrapper").each(function(index, element) {
						
						var old_wrapper = $(element);
						var new_wrapper = new_question.find(".group-wrapper").eq(index);
						
						old_wrapper.find(".alert-wrapper").each(function(index, element) {
							
							var old_alert = $(element);
							var new_alert = new_wrapper.find(".alert-wrapper").eq(index);
							
							old_alert.replaceWith(new_alert);
						});
						
						old_wrapper.find(".form-group").each(function(index, element) {
							
							var old_group = $(element);
							var new_group = new_wrapper.find(".form-group").eq(index);
							
							var state = new_group.hasClass("has-error");
							old_group.toggleClass("has-error", state);
						});
					});
				});
				
			} else {
				
				mbody.children(".pdf-error").removeClass("hidden");
				mbody.children(":not(.pdf-error)").addClass("hidden");
			}
		},
		complete: function(jqXHR, textStatus) {
			
			spinner.stop();
			mcontent.removeData("xhr spinner");
		},
	});
	
	mcontent.data("xhr", xhr);
});

$("#pdf-modal .pdf-open").click(function(e) {
	
	var data_uri = $("#pdf-modal .modal-body object").attr("data");
	window.open(data_uri, '_blank');
});

$("#pdf-modal").on("hidden.bs.modal", function(e) {
	
	var mcontent = $(this).closest(".modal-content");
	
	var xhr = mcontent.data("xhr");
	var spinner = mcontent.data("spinner");
	
	if (xhr)
		xhr.abort();
	
	if (spinner)
		spinner.stop();
});

// Input-group with checkbox/spinner -------------------------------------------

$(".input-group-checkbox > .input-group-btn > .btn").click(function(e) {
	
	var button = $(this);
	
	if (!button.hasClass("active")) {
		
		button.toggleClass("active");
		button.siblings("button").toggleClass("active");
		
		var checkbox = button.parent().siblings("input[type='checkbox']");
		checkbox.prop("checked", !checkbox.prop("checked"));
	}
});

$(".input-group-spinner > .input-group-btn > .btn").click(function(e) {
	
	var button = $(this);
	var input = button.parent().siblings("input");
	
	var val = parseInt(input.val());
	var minval = parseInt(input.prop("min")) || 0;
	
	input.val((val + (button.is(":first-child") ? 1 : -1)) || minval);
	input.trigger("change");
});

// -----------------------------------------------------------------------------

$("form .form-group").find(":input, .date").on("remove change update dp.change dp.update", function(e) {
	
	var form_group = $(this).closest(".form-group");
	var group_wrapper = form_group.closest(".group-wrapper");
	
	form_group.removeClass("has-error");
	
	if (group_wrapper.find(".form-group.has-error").length == 0) {
		group_wrapper.find(".alert").alert("close");
	}
	
	$("[data-toggle='tooltip']").tooltip("hide");
});

$("form .alert").on("close.bs.alert", function () {
	var height = $(this).height();
	$(this).data("height", height);
});

$("form .alert").on("closed.bs.alert", function () {
	var height = $(this).data("height");
	$("body").scrollTop($("body").scrollTop() - height);
});

// -----------------------------------------------------------------------------

// Update question events

update_question_table();

$("form").find(".question").each(function(index, element) {
	var question = $(element);
	update_option_list(question);
	register_option_sortable(question);
});

// Enable tolltips

$("body").tooltip({
	selector: "[data-toggle='tooltip']",
});

