$(document).ready(function() {
	updateProgress();
});

function updateProgress() {
	
	$.ajax({
		type: "POST",
		data: {
			csrfmiddlewaretoken: csrfmiddlewaretoken
		},
		success: function(data, textStatus, jqXHR) {
			
			$(".alert-warning").addClass("hidden");
			
			// Update RUNNING state
			
			if (data.state == state_list.RUNNING) {
				
				if (data.not_started)
					data.state -= 0.1;
				else if (data.ended)
					data.state += 0.1;
			}
			
			var items = $(".list-group > .list-group-item");
			var state_item = items.filter("[data-state='" + data.state + "']")
			
			// Clean-up glyphicon classes
			
			items.children(":not(.glyphicon)").addClass("hidden");
			
			items.children(".glyphicon").removeClass(function(index, className) {
				return (className.match(/glyphicon-\S+/g) || []).join(" ");
			});
			
			// Handle error case
			
			if (data.state == state_list.ERROR) {
				$(".alert-danger").removeClass("hidden");
				return;
			}
			
			// Set the appropriate glyphicon classes
			
			var glyphicon = state_item.children(".glyphicon");
			
			var glyphicon_lt = items.filter(function() { return $(this).data("state") < data.state }).children(".glyphicon");
			var glyphicon_gt = items.filter(function() { return $(this).data("state") > data.state }).children(".glyphicon");
			
			glyphicon_lt.removeClass("hidden").addClass("glyphicon-ok");
			glyphicon_gt.addClass("hidden");
			
			glyphicon.removeClass("hidden").addClass("glyphicon-option-horizontal");
			
			// Show a progress bar if ballots are being generated
			
			if (data.state == state_list.WORKING && typeof data.current !== "undefined") {
				
				var progress = state_item.children(".progress");
				var progress_bar = progress.children(".progress-bar");
				
				var value = Math.round((data.current / data.total) * 99) + 1;
				var value_css = (value + 1) + "%";
				
				glyphicon.addClass("hidden");
				progress.removeClass("hidden");
				
				progress_bar.css("width", value_css).attr("aria-valuenow", value);
				progress_bar.children("span").text(value_css);
			}
			
			var timeout;
			
			if (data.state == state_list.WORKING)
				timeout = 500;
			else if (data.state < state_list.WORKING)
				timeout = 5000;
			else if (data.state > state_list.WORKING)
				timeout = 15000;
			
			window.setTimeout(updateProgress, timeout);
		},
		error: function(jqXHR, textStatus, errorThrown) {
			
			$(".alert-warning").removeClass("hidden");
			window.setTimeout(updateProgress, 5000);
		}
	});
}

$(".panel-heading a").click(function(e) {
	$(this).toggleClass("active");
});

