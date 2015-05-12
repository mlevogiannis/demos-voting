# File: pdf.py

from os import path
from io import BytesIO
from math import ceil
from urllib.parse import urljoin
from subprocess import check_output

from qrcode import QRCode, constants
from django.utils.translation import ugettext, ungettext

from reportlab.lib import colors, enums, pagesizes
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFont, stringWidth
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, \
	Paragraph, Image, Spacer, PageBreak

from demos_utils.settings import *
from demos_utils.base32cf import _symbols


class BallotCreator:
	"""Creates PDF ballots"""
	
	@staticmethod
	def _load_ttf_family(ttf_family, ttf_style_list):
		"""Loads a TrueType font family
		
		Registers the given TrueType font family's styles for use with
		reportlab. Uses system's fc-list utility to get font paths.
		
		Arguments:
			ttf_family: The font family (string)
			ttf_style_list: A sequence of font styles (strings)
		
		Returns:
			A dict mapping ttf_style_list values to the corresponding registered
			font names.
		"""
		
		ttf_dict = {}
		
		for ttf_style in ttf_style_list:
			
			ttf_name = ttf_family + '-' + ttf_style
			ttf_name = "".join(ttf_name.split())
			
			cmd = ["fc-list", "-f", "%{file}",
				":style={0}:family={1}".format(ttf_style, ttf_family)]
			ttf_path = check_output(cmd, universal_newlines=True)
			
			registerFont(TTFont(ttf_name, ttf_path))
			ttf_dict[ttf_style] = ttf_name
		
		return ttf_dict
	
	@staticmethod
	def _image_aspect_ratio(filename):
		"""Calculates an image's aspect ratio
		
		Arguments:
			filename: The image's path (string)
		
		Returns:
			A float.
		"""
		
		img = ImageReader(filename)
		w, h = img.getSize()
		return h / w
	
	@staticmethod
	def _trunc_ellipsis(text, font_name, font_size, width):
		"""Truncates a string in order to fit in the specified width. Adds
		ellipsis at its end.
		
		Arguments:
			text: The text to be truncated (string)
			font_name: The font to be used (string)
			font_size: The font size to be used (string)
			width: The target width (float)
		
		Returns:
			A string.
		"""
		
		while stringWidth(text, font_name, font_size) > width:
			text = text[:-4] + "..."
		
		return text
	
	@staticmethod
	def _split_line(text, font_name, font_size, width_list):
		"""Splits 'text' in lines of 'width'. Returns the list of lines.
		
		Arguments:
			text: The text to be split (string)
			font_name: The font to be used (string)
			font_size: The font size to be used (integer)
			width_list: The width for each line (float). The last value is
				re-used for any remaining lines.
		
		Returns:
			A list of strings.
		"""
		
		line = ""
		line_list = []
		width = width_list[0]
		
		for c in text:
			
			if stringWidth(line + c, font_name, font_size) > width:
				line_list.append(line)
				line = c
				width = width_list[len(line_list)] \
					if len(line_list) < len(width_list) else width_list[-1]
			else:
				line += c
		
		line_list.append(line)
		return line_list
	
	def _url_prepare(self, text, url):
		
		line_width = self.page_width - self.cell_padding
		text_width = stringWidth(text + 2*" ", self.font_bold, self.font_md)
		
		url_lines = self._split_line(url, self.font_regular, self.font_md,
			[line_width-text_width, line_width-self.url_indent])
			
		paragraph = "<font name='" + self.font_bold + "'>" + text + \
			"</font>" + 2*"&nbsp;" + "\n".join(url_lines)
		
		return paragraph
	
	# Configuration
	
	pagesize = pagesizes.A4
	
	h_margin = 36
	w_margin = 36
	
	font_sm = 9
	font_md = 12
	font_lg = 14
	
	spacer = 7.5
	cell_padding = 12
	
	page_width, page_height = pagesize
	page_width -= w_margin * 2
	page_height -= h_margin * 2
	
	img_size = page_width // 4.5
	font_size_side_id = int(img_size)
	
	url_indent = page_width // 20
	table_top_gap = page_width // 15
	table_opt_gap = page_width // 50
	
	# TrueType fonts
	
	font_dict = _load_ttf_family.__func__('Liberation Sans', ['Regular','Bold'])
	
	font_regular = font_dict['Regular']
	font_bold = font_dict['Bold']
	
	# DemosVoting logo
	
	logo_path = path.join(path.dirname(path.abspath(__file__)),
		"resources/LOGO_BLACK_2_LOW.png")
	
	logo_img = Image(logo_path, width=img_size,
		height=((img_size) * _image_aspect_ratio.__func__(logo_path)))
	
	# TableStyle definitions (main)
	
	table_opt_style = TableStyle([
		('FONT',          ( 0, 0), (-1,-1), font_regular),
		('FONTSIZE',      ( 0, 0), (-1,-1), font_sm),
		('ALIGN',         ( 0, 0), (-1,-1), 'CENTER'),
		('INNERGRID',     ( 0, 0), (-1,-1), 0.25, colors.black),
		('LINEABOVE',     ( 0, 0), (-1, 0), 0.25, colors.black),
		('LINEBELOW',     ( 0,-1), (-1,-1), 0.25, colors.black),
		('LINEAFTER',     (-1, 0), (-1,-1), 2, colors.black),
		('LINEBEFORE',    ( 0, 0), ( 0,-1), 2, colors.black),
	])
	
	table_opt_extra1_style = TableStyle([
		('FONT',          ( 0, 0), (-1, 0), font_bold),
		('BOX',           ( 0, 0), (-1, 0), 1, colors.black),
		('LINEABOVE',     ( 0, 0), (-1, 0), 2, colors.black),
	])
	
	table_opt_extra2_style = TableStyle([
		('LINEBELOW',     ( 0,-1), (-1,-1), 2, colors.black),
	])
	
	table_que_style = TableStyle([
		('FONT',          ( 0, 0), ( 0,-1), font_bold),
		('FONT',          ( 1, 0), ( 1,-1), font_regular),
		('FONTSIZE',      ( 0, 0), (-1,-1), font_md),
		('ALIGN',         ( 0, 0), (-1,-1), 'LEFT'),
		('ALIGN',         ( 0, 0), (-1,-1), 'LEFT'),
		('BOTTOMPADDING', ( 0, 0), (-1,-1), spacer),
	])
	
	table_main_style = TableStyle([
		('VALIGN',        ( 0, 0), (-1,-1), 'MIDDLE'),
		('ALIGN',         ( 0, 0), (-1,-1), 'CENTER'),
		('TOPPADDING',    ( 0, 0), (-1, 0), spacer),
		('BOTTOMPADDING', ( 0, 0), (-1, 0), spacer),
	])
	
	table_main_extra_style = TableStyle([
		('SPAN',          ( 0, 0), (-1, 0)),
	])
	
	# TableStyle definitions (header)
	
	table_top_style = TableStyle([
		('FONT',          ( 0, 0), (-1,-1), font_bold),
		('FONTSIZE',      ( 0, 0), (-1,-1), font_lg),
		('ALIGN',         ( 0, 0), ( 0,-1), 'LEFT'),
		('ALIGN',         ( 1, 0), ( 1,-1), 'CENTER'),
		('ALIGN',         ( 3, 0), ( 3,-1), 'CENTER'),
		('ALIGN',         ( 4, 0), ( 4,-1), 'RIGHT'),
	])
	
	table_header_style = TableStyle([
		('VALIGN',        ( 0, 0), (-1,-1), 'MIDDLE'),
		('ALIGN',         ( 0, 0), (-1,-1), 'CENTER'),
		('BOTTOMPADDING', ( 0,-1), (-1,-1), spacer),
	])
	
	# TableStyle definitions (footer)
	
	table_url_style = TableStyle([
		('ALIGN',         ( 0, 0), (-1,-1), 'LEFT'),
	])
	
	table_img_style = TableStyle([
		('ALIGN',         ( 0, 0), ( 0,-1), 'LEFT'),
		('VALIGN',        ( 0, 0), ( 0,-1), 'MIDDLE'),
		('ALIGN',         ( 1, 0), ( 1,-1), 'CENTER'),
		('VALIGN',        ( 1, 0), ( 1,-1), 'MIDDLE'),
		('ALIGN',         ( 2, 0), ( 2,-1), 'RIGHT'),
		('VALIGN',        ( 2, 0), ( 2,-1), 'BOTTOM'),
		('FONT',          ( 2, 0), ( 2,-1), font_bold),
		('FONTSIZE',      ( 2, 0), ( 2,-1), font_size_side_id),
	])
	
	table_hlp_style = TableStyle([
		('ALIGN',         ( 0, 0), (-1,-1), 'CENTER'),
	])
	
	table_footer_style = TableStyle([
		('ALIGN',         ( 0, 0), (-1,-1), 'CENTER'),
		('VALIGN',        ( 0, 0), (-1,-1), 'MIDDLE'),
		('TOPPADDING',    ( 0, 0), (-1, 0), spacer),
		('TOPPADDING',    ( 0, 1), (-1, 1), -1.5),
		('BOTTOMPADDING', ( 0, 2), (-1, 2), -1.5),
	])
	
	# ParagraphStyle definitions
	
	paragraph_url_style = ParagraphStyle(
		name='url_style',
		fontSize=font_md,
		fontName=font_regular,
		alignment=enums.TA_LEFT,
		firstLineIndent=-url_indent,
		leftIndent=url_indent,
		leading=16,
	)
	
	paragraph_hlp_style = ParagraphStyle(
		name='hlp_style',
		fontSize=font_md,
		fontName=font_regular,
		alignment=enums.TA_CENTER,
	)
	
	def __init__(self, election_id, question_list):
		"""Inits BallotCreator and prepares common ballot data.
		
		Arguments:
			election_id: The election's id (string)
			question_list: A sequence of 3-tuples, each defining a question
				1) Question (string)
				2) Two_columns (boolean)
				3) List of options (sequence of strings)
		"""
		
		# Translatable text
		
		self.serial_text = ugettext("Serial number") + ":"
		self.security_text = ugettext("Security code") + ":"
		self.opt_text = ugettext("Option")
		self.vc_text = ugettext("Votecode")
		self.rec_text = ugettext("Receipt")
		self.abb_text = ugettext("Audit and Results") + ":"
		self.vbb_text = ugettext("Digital Ballot Box") + ":"
		self.ballot_text = ugettext("Ballot")
		
		self.question_text = ugettext("Question") + \
			(" %(question_id)s:" if len(question_list) > 1 else ":")
		
		self.help_text = ungettext(
			"Please use one of the two sides to vote and the other one to " \
				"audit your vote (%(0)s or %(1)s)",
			"Please use one of the sides to vote and the rest to audit your " \
				"vote",
			len(SIDE_ID_LIST) - 1
		) % {str(i): side_id for i, side_id in enumerate(SIDE_ID_LIST)}
		
		# Calculate table widths
		
		self.top_text_width = max([stringWidth(self.serial_text,
			self.font_bold, self.font_lg), stringWidth(self.security_text,
			self.font_bold, self.font_lg)]) + self.cell_padding
		
		self.top_value_width = (self.page_width -
			(2 * self.top_text_width + self.table_top_gap))/2
		
		self.vc_width = max([stringWidth(self.vc_text,
			self.font_bold, self.font_sm), max([stringWidth(c,
			self.font_regular, self.font_sm) for c in "0123456789"]) *
			len(str(OPTIONS_MAX-1))]) + self.cell_padding
		
		self.rec_width = max([stringWidth(self.rec_text,
			self.font_bold, self.font_sm), max([stringWidth(c,
			self.font_regular, self.font_sm) for c in _symbols]) *
			RECEIPT_LEN]) + self.cell_padding
		
		# Calculate table heights
		
		table = Table(data=[[""]], style=self.table_opt_style)
		self.row_height = int(table.wrap(0,0)[1])
		
		table = Table(data=[["",""]], style=self.table_que_style)
		self.que_height = int(table.wrap(0,0)[1])
		
		# Prepare common question data
		
		self.config_q_list = []
		self.election_id = election_id
		
		for question_id, (question, two_columns, option_list) \
			in enumerate(question_list, start=1):
			
			vc_chars = len(str(len(option_list)-1))
			
			vc_width  = self.vc_width
			rec_width = self.rec_width
			
			# Calculate option column width
			
			opt_width = self.cell_padding + max([stringWidth(self.opt_text,
				self.font_bold, self.font_sm)] + [stringWidth(option,
				self.font_regular, self.font_sm) for option in option_list])
			
			# Measure whitespace
			
			empty = self.page_width - (opt_width + vc_width + rec_width)
			
			if two_columns:
				empty -= (self.page_width + self.table_opt_gap) / 2
			
			# Share whitespace between options, votecodes and receipts
			
			if(empty > 0):
				
				opt_width += empty / 3
				vc_width  += empty / 3
				rec_width += empty / 3
			
			# Truncate long options to fit in the table
			
			elif(empty < 0):
				
				opt_width += empty
				
				for i in range(len(option_list)):
					option_list[i] = BallotCreator._trunc_ellipsis(
						option_list[i], self.font_regular, self.font_sm,
						opt_width - self.cell_padding)
			
			# Question title table
			
			question_text = self.question_text % {'question_id': question_id}
			
			que_text_width = stringWidth(question_text, self.font_bold,
				self.font_md) + self.cell_padding
			
			que_value_width = self.page_width - que_text_width
			
			text = BallotCreator._trunc_ellipsis(question, self.font_regular,
				self.font_md, que_value_width - self.cell_padding)
			
			table_que = Table(data=[[question_text, text]], colWidths=\
				[que_text_width, que_value_width], style=self.table_que_style
			)
			
			# Pack everything in the config list
			
			self.config_q_list.append((option_list, opt_width, \
				vc_width, rec_width, vc_chars, table_que, two_columns))
	
	def gen_ballot(self, ballot_id, permindex_s_list, voteurl_s_list,
		vcrec_s_list):
		"""Generates a new PDF ballot
		
		Arguments:
			ballot_id: The ballot's serial number (integer)
			permindex_s_list: A seq of permindexes (strings), one for every side
			voteurl_s_list: A sequence of voteurls (strings), one for every side
			vcrec_s_list: A sequence of vcrec_q_lists, one for every side. Each
				vcrec_q_list is sequence of votecode-receipt 2-tuples.
		
		Returns:
			A BytesIO object containing the PDF document
		"""
		
		# Initialize PDF object, using a BytesIO object as its file
		
		pdf_buffer = BytesIO()
		
		doc = SimpleDocTemplate(pdf_buffer, pagesize=self.pagesize,
			topMargin=self.h_margin, bottomMargin=self.h_margin,
			leftMargin=self.w_margin, rightMargin=self.w_margin,
			title="{0} {1}".format(self.ballot_text, str(ballot_id)),
			author="DemosVoting")
		
		# Prepare common side elements
		
		table_s_list = []
		
		for side_id, permindex, voteurl \
			in zip(SIDE_ID_LIST, permindex_s_list, voteurl_s_list):
			
			abb_url = urljoin(URL['abb'], "{0}".format(self.election_id))
			vbb_url = urljoin(URL['vbb'], "{0}/{1}".format(self.election_id,
				voteurl))
			
			# Generate QRCode
			
			qr = QRCode(error_correction=constants.ERROR_CORRECT_M)
			qr.add_data(vbb_url)
			qr.make(fit=True)
			qr_img = qr.make_image()
			
			qr_buf = BytesIO()
			qr_img.save(qr_buf, 'PNG')
			qr_buf.seek(0)
			
			qr_img = Image(qr_buf, width=self.img_size, height=self.img_size)
			
			# Create top, abb, vbb, img and hlp tables
			
			table_top = Table([[self.serial_text, str(ballot_id),
				"", self.security_text, str(permindex)]],
				colWidths=[self.top_text_width, self.top_value_width,
				self.table_top_gap, self.top_text_width,
				self.top_value_width], style=self.table_top_style
			)
			
			text = self._url_prepare(self.abb_text, abb_url)
			table_abb = Table([[Paragraph(text, self.paragraph_url_style)]],
				colWidths=[self.page_width], style=self.table_url_style
			)
			
			text = self._url_prepare(self.vbb_text, vbb_url)
			table_vbb = Table([[Paragraph(text, self.paragraph_url_style)]],
				colWidths=[self.page_width], style=self.table_url_style
			)
			
			table_img = Table([["", "", side_id], [qr_img, self.logo_img, ""]],
				style=self.table_img_style, colWidths=[self.page_width/3,
				self.page_width/3, self.page_width/3], rowHeights=[0, None]
			)
			
			table_hlp = Table(data=[[Paragraph(self.help_text,
				self.paragraph_hlp_style)]], colWidths=[self.page_width],
				style=self.table_hlp_style
			)
			
			# Create header and footer wrapper tables
			
			table_hdr = Table(data=[[table_top]], colWidths=\
				[self.page_width], style=self.table_header_style
			)
			
			table_ftr = Table(data=[[table_abb], [table_vbb], [table_img],
				[table_hlp]], colWidths=[self.page_width],
				style=self.table_footer_style
			)
			
			table_s_list.append((table_hdr, table_ftr))
		
		# Iterate over all sides and fill element_list
		
		element_list = []
		
		for (table_hdr, table_ftr), vcrec_q_list \
			in zip(table_s_list, vcrec_s_list):
			
			# Calculate available height for options
			
			_avail_height = self.page_height - (self.cell_padding + \
				table_hdr.wrap(0,0)[1] + table_ftr.wrap(0,0)[1])
			
			avail_height = _avail_height
			
			# Add page header
			
			element_list.append(table_hdr)
			
			# Iterate over side's questions
			
			for vcrec_list, (opt_list, opt_width, vc_width, rec_width, vc_chars,
				table_que, two_columns) in zip(vcrec_q_list,self.config_q_list):
				
				vc_list, rec_list = zip(*vcrec_list)
				
				col_widths = [opt_width, vc_width, rec_width]
				title = [[self.opt_text, self.vc_text, self.rec_text]]
				
				vc_list = [str(vc).zfill(vc_chars) for vc in vc_list]
				data_list = list(zip(opt_list, vc_list, rec_list))
				
				data_len = len(data_list)
				
				# Loop until all options have been inserted
				
				row = 0
				while row < data_len:
					
					incl_hdr = (row == 0)
					
					# Calculate the number of rows that can fit in this page
					
					inner_avail_height = avail_height - self.cell_padding - \
						self.spacer - (self.que_height if incl_hdr else 0)
					
					avail_rows = int(inner_avail_height // self.row_height)
					
					# Check if a new table with at least one option can fit
					
					if avail_rows < 2:
						
						element_list.append(Spacer(1, avail_height))
						element_list.append(table_ftr)
						element_list.append(PageBreak())
						element_list.append(table_hdr)
						
						avail_height = _avail_height
						continue
					
					# Prepare single-column option table
					
					if not two_columns:
						
						opt_rows = min(avail_rows-1, data_len-row)
						incl_ftr = (row + opt_rows == data_len)
						
						frst = row
						last = frst + opt_rows
						
						opt_data = data_list[frst: last] if not incl_hdr \
							else title + data_list[frst: last]
						
						table_opt = Table(opt_data, colWidths=col_widths,
							style=self.table_opt_style)
						
						if incl_hdr:
							table_opt.setStyle(self.table_opt_extra1_style)
						
						if incl_ftr:
							table_opt.setStyle(self.table_opt_extra2_style)
						
						table_data = [[table_opt]] if not incl_hdr \
							else [[table_que], [table_opt]]
						
						table_widths = [table_opt.minWidth()]
					
					# Prepare double-column option table
					
					else:
						
						opt_rows = min(2*(avail_rows-1), data_len-row)
						incl_ftr = (row + opt_rows == data_len)
						
						frst = row // 2
						last = 2*frst+opt_rows - (2*frst+opt_rows)//2
						
						t = ceil(data_len/2)
						
						opt_data1 = data_list[frst: last] if not incl_hdr \
							else title + data_list[frst: last]
						
						opt_data2 = data_list[t+frst: t+last] if not incl_hdr \
							else title + data_list[t+frst: t+last]
						
						if len(opt_data2) < len(opt_data1):
							opt_data2.append(["", "", ""])
						
						table_opt1 = Table(opt_data1, colWidths=col_widths,
							style=self.table_opt_style)
						
						table_opt2 = Table(opt_data2, colWidths=col_widths,
							style=self.table_opt_style)
						
						if incl_hdr:
							table_opt1.setStyle(self.table_opt_extra1_style)
							table_opt2.setStyle(self.table_opt_extra1_style)
						
						if incl_ftr:
							table_opt1.setStyle(self.table_opt_extra2_style)
							table_opt2.setStyle(self.table_opt_extra2_style)
						
						table_data = \
							[[table_opt1,"",table_opt2]] if not incl_hdr else\
							[[table_que, "", ""], [table_opt1, "", table_opt2]]
						
						table_widths = [table_opt1.minWidth(),
							self.table_opt_gap, table_opt2.minWidth()]
					
					# Add option table
					
					table_wrapper = Table(data=table_data,
						colWidths=table_widths, style=self.table_main_style)
					
					if incl_hdr:
						table_wrapper.setStyle(self.table_main_extra_style)
					
					element_list.append(table_wrapper)
					
					avail_height -= table_wrapper.wrap(0,0)[1]
					row += opt_rows
			
			# Add page footer
			
			element_list.append(Spacer(1, avail_height))
			element_list.append(table_ftr)
			element_list.append(PageBreak())
		
		# Build the PDF file
		
		doc.build(element_list)
		return pdf_buffer

