# File: pdf.py

from __future__ import division

import math

from os import path
from io import BytesIO
from subprocess import check_output

try:
    from urllib.parse import urljoin, quote
except ImportError:
    from urllib import quote
    from urlparse import urljoin

from qrcode import QRCode, constants
from django.utils.translation import ugettext as _

from reportlab.lib import colors, enums, pagesizes
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFont, stringWidth
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, \
    Paragraph, Image, Spacer, PageBreak

from demos.common.utils import base32cf
from demos.common.utils.config import registry

config = registry.get_config('ea')


class BallotBuilder:
    """Generates PDF ballots"""
    
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
            
            if not ttf_path:
                raise EnvironmentError("Missing font for: %s-%s" % \
                    (ttf_family, ttf_style))
            
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
        return float(h) / float(w)
    
    @staticmethod
    def _ellipsize(text, font_name, font_size, width):
        """Truncates a string so that is fits in the specified width. Adds
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
        text_width = stringWidth(text + 2*" ", self.sans_bold, self.font_md)
        
        url_lines = self._split_line(url, self.sans_regular, self.font_md,
            [line_width-text_width, line_width-self.url_indent])
            
        paragraph = "<font name='" + self.sans_bold + "'>" + text + \
            "</font>" + 2*"&nbsp;" + "<link href='" + url + "'>" + \
            "\n".join(url_lines) + "</link>"
        
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
    font_size_index = int(img_size)
    
    url_indent = page_width // 20
    table_top_gap = page_width // 15
    table_opt_gap = page_width // 50
    
    long_vc_split = 4
    long_vc_hyphens = int(math.ceil(config.VOTECODE_LEN / long_vc_split)) - 1
    
    # TrueType fonts
    
    sans_font_dict = _load_ttf_family.__func__('Liberation Sans', \
        ['Regular', 'Bold'])
    
    mono_font_dict = _load_ttf_family.__func__('Liberation Mono', \
        ['Regular', 'Bold'])
    
    sans_regular = sans_font_dict['Regular']
    sans_bold = sans_font_dict['Bold']
    
    mono_regular = mono_font_dict['Regular']
    mono_bold = mono_font_dict['Bold']
    
    # DemosVoting logo
    
    logo_path = path.join(path.dirname(path.abspath(__file__)),
        "resources/LOGO_BLACK_2_LOW.png")
    
    logo_img = Image(logo_path, width=img_size,
        height=((img_size) * _image_aspect_ratio.__func__(logo_path)))
    
    # TableStyle definitions (main)
    
    table_opt_style = TableStyle([
        ('FONT',          ( 0, 0), ( 0,-1), sans_regular),
        ('FONT',          ( 1, 0), (-1,-1), mono_regular),
        ('FONTSIZE',      ( 0, 0), (-1,-1), font_sm),
        ('ALIGN',         ( 0, 0), (-1,-1), 'CENTER'),
        ('INNERGRID',     ( 0, 0), (-1,-1), 0.25, colors.black),
        ('LINEABOVE',     ( 0, 0), (-1, 0), 0.25, colors.black),
        ('LINEBELOW',     ( 0,-1), (-1,-1), 0.25, colors.black),
        ('LINEAFTER',     (-1, 0), (-1,-1), 2, colors.black),
        ('LINEBEFORE',    ( 0, 0), ( 0,-1), 2, colors.black),
    ])
    
    table_opt_extra1_style = TableStyle([
        ('FONT',          ( 0, 0), (-1, 0), sans_bold),
        ('BOX',           ( 0, 0), (-1, 0), 1, colors.black),
        ('LINEABOVE',     ( 0, 0), (-1, 0), 2, colors.black),
    ])
    
    table_opt_extra2_style = TableStyle([
        ('LINEBELOW',     ( 0,-1), (-1,-1), 2, colors.black),
    ])
    
    table_que_style = TableStyle([
        ('FONT',          ( 0, 0), ( 0,-1), sans_bold),
        ('FONT',          ( 1, 0), ( 1,-1), sans_regular),
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
        ('FONT',          ( 0, 0), (-1,-1), sans_bold),
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
        ('FONT',          ( 2, 0), ( 2,-1), sans_bold),
        ('FONTSIZE',      ( 2, 0), ( 2,-1), font_size_index),
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
        fontName=sans_regular,
        alignment=enums.TA_LEFT,
        firstLineIndent=-url_indent,
        leftIndent=url_indent,
        leading=16,
    )
    
    paragraph_hlp_style = ParagraphStyle(
        name='hlp_style',
        fontSize=font_md,
        fontName=sans_regular,
        alignment=enums.TA_CENTER,
    )
    
    def __init__(self, election_obj):
        """Inits BallotBuilder and prepares common ballot data."""
        
        self.election_id = election_obj['id']
        self.long_votecodes = election_obj['long_votecodes']
        
        # Translatable text
        
        self.serial_text = _("Serial number") + ":"
        self.security_text = _("Security code") + ":"
        self.opt_text = _("Option")
        self.vc_text = _("Vote-code")
        self.rec_text = _("Receipt")
        self.abb_text = _("Audit and Results") + ":"
        self.vbb_text = _("Digital Ballot Box") + ":"
        self.ballot_text = _("Ballot")
        
        self.question_text = _("Question") + (" %(index)s:"
            if len(election_obj['__list_Question__']) > 1 else ":")
        
        self.help_text = _( "Please use one of the two sides to vote and the " \
            "other one to audit your vote")
        
        # Votecode defaults
        
        if not self.long_votecodes:
            vc_charset = "0123456789"
            vc_maxchars = len(str(config.MAX_OPTIONS - 1))
        else:
            vc_charset = base32cf._chars + "-"
            vc_maxchars = config.VOTECODE_LEN + self.long_vc_hyphens
        
        # Calculate table widths
        
        self.top_text_width = max([stringWidth(self.serial_text,
            self.sans_bold, self.font_lg), stringWidth(self.security_text,
            self.sans_bold, self.font_lg)]) + self.cell_padding
        
        self.top_value_width = (self.page_width -
            (2 * self.top_text_width + self.table_top_gap)) / 2
        
        self.vc_width = max([stringWidth(self.vc_text, self.sans_bold,
            self.font_sm), max([stringWidth(c, self.mono_regular, self.font_sm)
            for c in vc_charset]) * vc_maxchars]) + self.cell_padding
        
        self.rec_width = max([stringWidth(self.rec_text, self.sans_bold,
            self.font_sm), max([stringWidth(c, self.mono_regular, self.font_sm)
            for c in base32cf._chars])*config.RECEIPT_LEN]) + self.cell_padding
        
        # Calculate table heights
        
        table = Table(data=[[""]], style=self.table_opt_style)
        self.row_height = int(table.wrap(self.page_width, self.page_height)[1])
        
        table = Table(data=[["",""]], style=self.table_que_style)
        self.que_height = int(table.wrap(self.page_width, self.page_height)[1])
        
        # Prepare common question data
        
        self.config_q_list = []
        
        for index, question_obj \
            in enumerate(election_obj['__list_Question__'], start=1):
            
            two_columns = question_obj['columns']
            
            option_list = [optionc_obj['text'] for optionc_obj \
                in question_obj['__list_OptionC__']]
            
            vc_chars = config.VOTECODE_LEN + self.long_vc_hyphens \
                if self.long_votecodes else len(str(len(option_list)-1))
            
            vc_width  = self.vc_width
            rec_width = self.rec_width
            
            # Calculate option column width
            
            opt_width = self.cell_padding + max([stringWidth(self.opt_text,
                self.sans_bold, self.font_sm)] + [stringWidth(option,
                self.sans_regular, self.font_sm) for option in option_list])
            
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
                    option_list[i] = self._ellipsize(option_list[i], self.\
                        sans_regular, self.font_sm, opt_width-self.cell_padding)
            
            # Question title table
            
            question_text = self.question_text % {'index': index}
            
            que_text_width = stringWidth(question_text, self.sans_bold,
                self.font_md) + self.cell_padding
            
            que_value_width = self.page_width - que_text_width
            
            text = self._ellipsize(question_obj['text'], self.sans_regular,
                self.font_md, que_value_width - self.cell_padding)
            
            table_que = Table(data=[[question_text, text]], colWidths=\
                [que_text_width, que_value_width], style=self.table_que_style
            )
            
            # Pack everything in the config list
            
            self.config_q_list.append((option_list, opt_width, vc_width,
                rec_width, vc_chars, table_que, two_columns))
    
    def pdfgen(self, ballot_obj):
        """Generates a new PDF ballot and returns it as a BytesIO object"""
        
        serial = ballot_obj['serial']
        
        # Initialize PDF object, using a BytesIO object as its file
        
        pdf_buffer = BytesIO()
        
        doc = SimpleDocTemplate(pdf_buffer, pagesize=self.pagesize,
            topMargin=self.h_margin, bottomMargin=self.h_margin,
            leftMargin=self.w_margin, rightMargin=self.w_margin,
            title="%s %s" % (self.ballot_text, serial),
            author="DemosVoting")
        
        # Prepare common part elements
        
        table_s_list = []
        
        for part_obj in ballot_obj['__list_Part__']:
            
            abb_url = urljoin(config.URL['abb'], \
                quote("%s/" % self.election_id))
            
            vbb_url = urljoin(config.URL['vbb'], quote("%s/%s/" \
                 % (self.election_id, part_obj['vote_token'])))
            
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
            
            table_top = Table([[self.serial_text, "%s" % serial,
                "", self.security_text, part_obj['security_code']]],
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
            
            table_img = Table([["", "", part_obj['index']], [qr_img,
                self.logo_img, ""]], style=self.table_img_style,
                colWidths=[self.page_width/3, self.page_width/3,
                self.page_width/3], rowHeights=[0, None]
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
            
        vc_type = 'votecode' if not self.long_votecodes else 'l_votecode'
        
        # Iterate over all parts and fill element_list
        
        element_list = []
        
        for (table_hdr, table_ftr), part_obj \
            in zip(table_s_list, ballot_obj['__list_Part__']):
            
            # Calculate available height for options
            
            _avail_height = self.page_height - (self.cell_padding + \
                table_hdr.wrap(self.page_width, self.page_height)[1] + \
                table_ftr.wrap(self.page_width, self.page_height)[1])
            
            avail_height = _avail_height
            
            # Add page header
            
            element_list.append(table_hdr)
            
            # Iterate over part's questions
            
            for question_obj, (opt_list, opt_width, vc_width,
                rec_width, vc_chars, table_que, two_columns) \
                in zip(part_obj['__list_Question__'], self.config_q_list):
                
                vc_list = [optionv_obj[vc_type] for optionv_obj
                    in question_obj['__list_OptionV__']]
                
                rec_list = [optionv_obj['receipt'] for optionv_obj
                    in question_obj['__list_OptionV__']]
                
                col_widths = [opt_width, vc_width, rec_width]
                title = [[self.opt_text, self.vc_text, self.rec_text]]
                
                if not self.long_votecodes:
                    vc_list = [str(vc).zfill(vc_chars) for vc in vc_list]
                else:
                    vc_list = [base32cf.hyphen(vc, self.long_vc_split) \
                        for vc in vc_list]
                
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
                        
                        optionv = data_list[frst: last]
                        
                        if incl_hdr:
                            optionv = title + optionv
                        
                        table_opt = Table(optionv, colWidths=col_widths,
                            style=self.table_opt_style)
                        
                        if incl_hdr:
                            table_opt.setStyle(self.table_opt_extra1_style)
                        
                        if incl_ftr:
                            table_opt.setStyle(self.table_opt_extra2_style)
                        
                        table_data = [[table_opt]]
                        
                        if incl_hdr:
                            table_data.insert(0, [table_que])
                        
                        table_widths = [table_opt.minWidth()]
                    
                    # Prepare double-column option table
                    
                    else:
                        
                        opt_rows = min(2*(avail_rows-1), data_len-row)
                        incl_ftr = (row + opt_rows == data_len)
                        
                        frst = row // 2
                        last = 2*frst+opt_rows - (2*frst+opt_rows)//2
                        
                        t = int(math.ceil(data_len/2))
                        
                        optionv1 = data_list[frst: last]
                        
                        if incl_hdr:
                            optionv1 = title + optionv1
                        
                        optionv2 = data_list[t+frst: t+last]
                        
                        if incl_hdr:
                            optionv2 = title + optionv2
                        
                        if len(optionv2) < len(optionv1):
                            optionv2.append(["", "", ""])
                        
                        table_opt1 = Table(optionv1, colWidths=col_widths,
                            style=self.table_opt_style)
                        
                        table_opt2 = Table(optionv2, colWidths=col_widths,
                            style=self.table_opt_style)
                        
                        if incl_hdr:
                            table_opt1.setStyle(self.table_opt_extra1_style)
                            table_opt2.setStyle(self.table_opt_extra1_style)
                        
                        if incl_ftr:
                            table_opt1.setStyle(self.table_opt_extra2_style)
                            table_opt2.setStyle(self.table_opt_extra2_style)
                        
                        table_data = [[table_opt1, "", table_opt2]]
                        
                        if incl_hdr:
                            table_data.insert(0, [table_que, "", ""])
                        
                        table_widths = [table_opt1.minWidth(),
                            self.table_opt_gap, table_opt2.minWidth()]
                    
                    # Add option table
                    
                    table_wrapper = Table(data=table_data,
                        colWidths=table_widths, style=self.table_main_style)
                    
                    if incl_hdr:
                        table_wrapper.setStyle(self.table_main_extra_style)
                    
                    element_list.append(table_wrapper)
                    
                    avail_height -= \
                        table_wrapper.wrap(self.page_width, avail_height)[1]
                    
                    row += opt_rows
            
            # Add page footer
            
            element_list.append(Spacer(1, avail_height))
            element_list.append(table_ftr)
            element_list.append(PageBreak())
        
        # Build the PDF file
        
        doc.build(element_list)
        return pdf_buffer

