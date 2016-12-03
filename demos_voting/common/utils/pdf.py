# File: pdf.py

from __future__ import absolute_import, division, print_function, unicode_literals

import io
import math
import os
import random
import string
import subprocess

from django.conf import settings
from django.utils.encoding import force_text
from django.utils.lru_cache import lru_cache
from django.utils.six.moves import range, zip
from django.utils.six.moves.urllib.parse import quote, urljoin
from django.utils.translation import ugettext as _

import qrcode

from reportlab.graphics.shapes import Drawing, Line
from reportlab.lib import colors, enums, pagesizes
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import registerFont, stringWidth
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from demos_voting.common.models import Election
from demos_voting.common.utils import base32


@lru_cache(maxsize=None)
def _load_ttf(family, style):

    path = subprocess.check_output(
        ['fc-list', '-f', '%{file}', ':family=%s:style=%s' % (family, style)],
        universal_newlines=True
    )

    if not path:
        raise EnvironmentError("Missing font for: family='%s', style='%s'" % (family, style))

    name = os.path.splitext(os.path.basename(path))[0]
    registerFont(TTFont(name, path))

    return name


@lru_cache(maxsize=None)
def _load_image(filename, width=None, height=None):

    p = os.path.join(settings.BASE_DIR, 'common/static/common/images', filename)
    with open(p, 'rb') as f:
        b = io.BytesIO(f.read())

    if (width is not None) != (height is not None):
        w, h = ImageReader(b).getSize()
        if width is None:
            width = (float(h) / float(w)) * height
        elif height is None:
            height = (float(h) / float(w)) * width

    return Image(b, width=width, height=height)


def generate(*ballots):

    election = ballots[0].election

    # Paper configuration.

    pagesize = pagesizes.A4

    h_margin = 36
    v_margin = 28

    h_padding = 12
    v_padding = 8

    font_sm = 9
    font_md = 12
    font_lg = 15

    ttf_sans_bold = _load_ttf('Liberation Sans', 'Bold')
    ttf_sans_italic = _load_ttf('Liberation Sans', 'Italic')
    ttf_sans_regular = _load_ttf('Liberation Sans', 'Regular')
    ttf_mono_bold = _load_ttf('Liberation Mono', 'Bold')
    ttf_mono_regular = _load_ttf('Liberation Mono', 'Regular')

    long_votecode_chunk_length = 4

    page_width, page_height = pagesize
    page_width -= 2 * h_margin
    page_height -= 2 * v_margin

    logo_img = _load_image('logos/LOGO_BLACK_1.png', width=(page_width // 3))

    option_table_style = TableStyle([
        ('FONT',          ( 0, 0), (-1,-1), ttf_mono_regular),
        ('FONTSIZE',      ( 0, 0), (-1,-1), font_sm),
        ('ALIGN',         ( 0, 0), (-1,-1), 'CENTER'),
        ('INNERGRID',     ( 0, 0), ( 2,-1), 0.25, colors.black),
        ('INNERGRID',     ( 4, 0), ( 6,-1), 0.25, colors.black),
        ('LINEBEFORE',    ( 0, 0), ( 0,-1), 2, colors.black),
        ('LINEBEFORE',    ( 4, 0), ( 4,-1), 2, colors.black),
        ('LINEAFTER',     ( 2, 0), ( 2,-1), 2, colors.black),
        ('LINEAFTER',     ( 6, 0), ( 6,-1), 2, colors.black),
        ('LINEABOVE',     ( 0, 0), ( 2, 0), 0.25, colors.black),
        ('LINEABOVE',     ( 4, 0), ( 6, 0), 0.25, colors.black),
        ('LINEBELOW',     ( 0,-1), ( 2,-1), 0.25, colors.black),
        ('LINEBELOW',     ( 4,-1), ( 6,-1), 0.25, colors.black),
    ])

    option_table_header_style = TableStyle([
        ('FONT',          ( 0, 0), (-1, 0), ttf_sans_bold),
        ('BOX',           ( 0, 0), ( 2, 0), 1, colors.black),
        ('BOX',           ( 4, 0), ( 6, 0), 1, colors.black),
        ('LINEABOVE',     ( 0, 0), ( 2, 0), 2, colors.black),
        ('LINEABOVE',     ( 4, 0), ( 6, 0), 2, colors.black),
    ])

    option_table_footer_style = TableStyle([
        ('LINEBELOW',     ( 0,-1), ( 2,-1), 2, colors.black),
        ('LINEBELOW',     ( 4,-1), ( 6,-1), 2, colors.black),
    ])

    question_table_style = TableStyle([
        ('ALIGN',         ( 0,-1), (-1,-1), 'CENTER'),
    ])

    page_header_table_style = TableStyle([
        ('FONT',          ( 0, 0), ( 3, 0), ttf_sans_bold),
        ('FONT',          ( 4, 0), ( 4, 0), ttf_mono_bold),
        ('FONTSIZE',      ( 0, 0), (-1, 0), font_lg),
        ('ALIGN',         ( 0, 0), ( 0, 0), 'LEFT'),
        ('ALIGN',         ( 1, 0), ( 1, 0), 'RIGHT'),
        ('ALIGN',         ( 3, 0), ( 3, 0), 'LEFT'),
        ('ALIGN',         ( 4, 0), ( 4, 0), 'RIGHT'),
        ('BOTTOMPADDING', ( 0, 0), (-1, 0), 2 * v_padding),
        ('SPAN',          ( 0, 1), (-1, 1)),
        ('SPAN',          ( 0, 2), (-1, 2)),
    ])

    page_footer_table_style = TableStyle([
        ('SPAN',          ( 0, 0), (-1, 0)),
        ('SPAN',          ( 0, 1), (-1, 1)),
        ('ALIGN',         ( 0, 2), ( 0, 3), 'LEFT'),
        ('VALIGN',        ( 0, 2), ( 0, 3), 'MIDDLE'),
        ('ALIGN',         ( 1, 2), ( 1, 3), 'CENTER'),
        ('VALIGN',        ( 1, 2), ( 1, 3), 'MIDDLE'),
        ('ALIGN',         ( 2, 2), ( 2, 3), 'RIGHT'),
        ('VALIGN',        ( 2, 2), ( 2, 3), 'BOTTOM'),
        ('FONT',          ( 2, 2), ( 2, 3), ttf_sans_bold),
        ('FONTSIZE',      ( 2, 2), ( 2, 3), int(page_width // 5)),
        ('SPAN',          ( 0, 4), (-1, 4)),
        ('ALIGN',         ( 0, 4), (-1, 4), 'CENTER'),
    ])

    option_paragraph_style = ParagraphStyle(
        name='option_paragraph_style',
        fontSize=font_sm,
        fontName=ttf_sans_regular,
        alignment=enums.TA_CENTER,
    )

    blank_paragraph_style = ParagraphStyle(
        name='blank_paragraph_style',
        fontSize=font_sm,
        fontName=ttf_sans_italic,
        alignment=enums.TA_CENTER,
    )

    help_paragraph_style = ParagraphStyle(
        name='help_paragraph_style',
        fontSize=font_md,
        fontName=ttf_sans_regular,
        alignment=enums.TA_CENTER,
    )

    # Functions to truncate or split long strings.

    def _truncate(text, max_width, font_name, font_size):
        while stringWidth(text, font_name, font_size) > max_width:
            text = text[:-4] + "..."
        return text

    def _split(text, max_width, font_name, font_size):
        lines = [""]
        for i, char in enumerate(text):
            cur_width = stringWidth(lines[-1] + char, font_name, font_size)
            if cur_width > max_width:
                lines.append(char)
            else:
                lines[-1] += char
        return lines

    # Function to prepare key-value paragraphs.

    kv_text_paragraph_style = ParagraphStyle(
        name='kv_text_paragraph_style',
        fontSize=font_md,
        fontName=ttf_sans_regular,
        leading=16,
    )

    kv_data_paragraph_style = ParagraphStyle(
        name='kv_data_paragraph_style',
        fontSize=font_md,
        fontName=ttf_mono_regular,
        firstLineIndent=-20,
        leftIndent=20,
        leading=16,
    )

    kv_url_paragraph_style = ParagraphStyle(
        name='kv_url_paragraph_style',
        fontSize=font_md,
        fontName=ttf_mono_regular,
        firstLineIndent=-20,
        leftIndent=20,
        leading=16,
    )

    def _kv_paragraph(key, value, mode):
        if mode == 't':
            style = kv_text_paragraph_style
            max_width = page_width - stringWidth(key + ":", ttf_sans_bold, style.fontSize) - h_padding
            value = "&nbsp;%s" % _truncate(" " + value, max_width, style.fontName, style.fontSize)
        elif mode == 'd':
            style = kv_data_paragraph_style
            value = "&nbsp;%s" % value
        elif mode == 'u':
            style = kv_url_paragraph_style
            max_width = page_width - style.leftIndent - h_padding
            value = "<br/><link href='%s'>%s</link>" % (
                value, "<br/>".join(_split(value, max_width, style.fontName, style.fontSize))
            )
        return Paragraph("<font name='%s'>%s:</font>%s" % (ttf_sans_bold, key, value), style)

    # Translatable strings.

    serial_number_text = _("Serial number") + ":"
    security_code_text =  (_("Security code") + ":") if not election.security_code_type_is_none else ""

    election_name_text = _("Election Name")
    election_id_text = _("Election ID")

    if election.type_is_referendum:
        question_text = (_("Question %(index)s") if election.questions.count() > 1 else _("Question"))
        option_text = _("Option")
    elif election.type_is_election:
        question_text = _("Party")
        option_text = _("Candidate")

    blank_text = _("Blank")

    votecode_text = _("Vote-code")
    receipt_text = _("Receipt")

    abb_text = _("Audit and Results")
    vbb_text = _("Virtual Ballot Box")

    help_text = _("Every ballot consists of two parts, A and B. Please use one of them to vote and keep the other "
        "one for the verification process.")

    # Calculate serial number and security code's column widths.

    sn_length = len(force_text(100 + election.ballots.count() - 1))

    sn_key_width = stringWidth(serial_number_text, ttf_sans_bold, font_lg) + h_padding
    sn_value_width = max(stringWidth(c, ttf_sans_bold, font_lg) for c in string.digits) * sn_length + h_padding

    sc_length = election.security_code_length

    if election.security_code_type_is_none:
        sc_key_width = 0
        sc_value_width = 0
    else:
        if election.security_code_type_is_numeric:
            security_code_chars = string.digits
        elif election.security_code_type_is_alphanumeric:
            security_code_chars = base32.symbols
        sc_key_width = stringWidth(security_code_text, ttf_sans_bold, font_lg) + h_padding
        sc_value_width = stringWidth(security_code_chars[0], ttf_mono_bold, font_lg) * sc_length + h_padding

    sn_sc_separator_width = max(h_padding, page_width - sn_key_width - sn_value_width - sc_key_width - sc_value_width)

    # Calculate votecode and receipt's minimum column widths.

    if election.votecode_type_is_short:
        votecode_chars = string.digits
        if election.type_is_referendum:
            max_options = settings.DEMOS_VOTING_MAX_REFERENDUM_OPTIONS
        elif election.type_is_election:
            max_options = election.questions.all()[1].options.count()
        votecode_length = len(force_text(max_options - 1))
    elif election.votecode_type_is_long:
        votecode_chars = base32.symbols + '-'
        votecode_length = (election.long_votecode_length +
            int(math.ceil(election.long_votecode_length / long_votecode_chunk_length)) - 1)

    votecode_column_min_width = h_padding + max(
        stringWidth(votecode_text, ttf_sans_bold, font_sm),
        stringWidth(votecode_chars[0], ttf_mono_regular, font_sm) * votecode_length
    )

    receipt_column_min_width = h_padding + max(
        stringWidth(receipt_text, ttf_sans_bold, font_sm),
        stringWidth(base32.symbols[0], ttf_mono_regular, font_sm) * election.receipt_length
    )

    # Calculate option table's column widths (option, votecode, receipt).

    _option_table_data = []

    if election.type_is_election:
        parties = election.questions.all()[0].options.all()
        candidates = election.questions.all()[1].options.all()
        groups = [options for options in zip(*([iter(candidates)] * (len(candidates) // len(parties))))]
    elif election.type_is_referendum:
        groups = [tuple(question.options.all()) for question in election.questions.all()]

    for i, options in enumerate(groups):

        if election.type_is_election:
            question = election.questions.all()[1]
        elif election.type_is_referendum:
            question = election.questions.all()[i]

        options = [
            Paragraph(option.name, option_paragraph_style)
                if option.name is not None else
            Paragraph(blank_text, blank_paragraph_style)
                for option in options
        ]

        option_column_width = h_padding + max(
            stringWidth(option_text, ttf_sans_bold, font_sm),
            *[option.minWidth() for option in options]
        )

        votecode_column_width = votecode_column_min_width
        receipt_column_width = receipt_column_min_width

        available_width = page_width - (option_column_width + votecode_column_width + receipt_column_width)
        if question.layout_is_two_column:
            available_width -= (page_width + h_padding) / 2

        if available_width < 0:
            option_column_width += available_width
            option_value_width = option_column_width - h_padding
            for i, option in enumerate(options):
                text = _truncate(option.name, option_value_width, option.style.fontName, option.style.fontSize)
                options[i] = Paragraph(text, option.style)
        elif available_width > 0:
            option_column_width += available_width / 3
            receipt_column_width += available_width / 3
            votecode_column_width += available_width / 3

        option_table_column_widths = [option_column_width, votecode_column_width, receipt_column_width]
        if question.layout_is_two_column:
            option_table_column_widths += [h_padding] + option_table_column_widths

        _option_table_data.append((options, option_table_column_widths))

    pdf_list = []

    for ballot in ballots:
        assert ballot.election is election

        elements = []

        for part in ballot.parts.all():

            abb_url = urljoin(settings.DEMOS_VOTING_URLS['abb'], quote("%s/" % election.id))
            vbb_url = urljoin(settings.DEMOS_VOTING_URLS['vbb'], quote("%s/%s/" % (election.id, part.token)))

            qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M)
            qr.add_data(vbb_url)
            qr.make(fit=True)
            qr_data = io.BytesIO()
            qr.make_image().save(qr_data, 'png')
            qr_data.seek(0)
            qr_img = Image(qr_data, width=(page_width // 5), height=(page_width // 5))

            # Prepare header and footer, common for all pages of this part.

            page_header_table = Table(
                data=[
                    [serial_number_text, ballot.serial_number, "", security_code_text, part.security_code or ""],
                    [_kv_paragraph(election_name_text, election.name, mode='t')],
                    [_kv_paragraph(election_id_text, election.id, mode='d')],
                ],
                colWidths=[sn_key_width, sn_value_width, sn_sc_separator_width, sc_key_width, sc_value_width],
                style=page_header_table_style
            )

            page_footer_table = Table(
                data = [
                    [_kv_paragraph(vbb_text, vbb_url, mode='u')],
                    [_kv_paragraph(abb_text, abb_url, mode='u')],
                    ["", "", part.tag],
                    [qr_img, logo_img, ""],
                    [Paragraph(help_text, help_paragraph_style)]
                ],
                colWidths=[page_width / 3, page_width / 3, page_width / 3],
                rowHeights=[None, None, 0, None, None],
                style=page_footer_table_style
            )

            line = Drawing(width=(page_width - h_padding), height=0.5)
            line.add(Line(x1=0, y1=0, x2=(page_width - h_padding), y2=0, strokeWidth=0.5, strokeDashArray=(6, 3)))

            spacer = Spacer(page_width, 1.5 * v_padding)

            header_elements = [page_header_table, spacer, line, spacer]
            footer_elements = [spacer, line, spacer, page_footer_table]

            elements.extend(header_elements)

            # Available height for each page's questions and options.

            total_height = page_height - sum(
                sum(e.wrap(page_width, page_height)[1] for e in s) for s in (header_elements, footer_elements)
            ) - 12

            available_height = total_height

            # Split options into groups. In the election case, candidates are
            # grouped by party. Otherwise, the groups are the questions.

            if election.type_is_election:
                parties = part.questions.all()[0].options.all()
                candidates = part.questions.all()[1].options.all()
                groups = [p_options for p_options in zip(*([iter(candidates)] * (len(candidates) // len(parties))))]
            elif election.type_is_referendum:
                groups = [tuple(p_question.options.all()) for p_question in part.questions.all()]

            for i, (p_options, (options, option_table_column_widths)) in enumerate(zip(groups, _option_table_data)):

                # Prepare question table's data.

                if election.type_is_election:
                    party_option = election.questions.all()[0].options.all()[i]
                    party_p_option = part.questions.all()[0].options.all()[i]

                    name = party_option.name
                    votecode = party_p_option.votecode
                    receipt = party_p_option.receipt

                    if election.votecode_type_is_long:
                        votecode = base32.hyphen(votecode, long_votecode_chunk_length)
                        receipt = receipt[-election.receipt_length:]

                    question_table_rows = [
                        [_kv_paragraph(question_text, name, mode='t')],
                        [_kv_paragraph(votecode_text, votecode, mode='d')],
                        [_kv_paragraph(receipt_text, receipt, mode='d')]
                    ]

                elif election.type_is_referendum:
                    question = election.questions.all()[i]
                    question_table_rows = [
                        [_kv_paragraph(question_text % {'index': question.index + 1}, question.name, mode='t')]
                    ]

                question_table = Table(question_table_rows, colWidths=[page_width], style=question_table_style)
                question_table_height = question_table.wrap(page_width, page_height)[1]

                # Prepare option table's data.

                option_table_header_row = [option_text, votecode_text, receipt_text]

                votecodes = [p_option.votecode for p_option in p_options]
                receipts = [p_option.receipt[-election.receipt_length:] for p_option in p_options]

                if election.votecode_type_is_long:
                    votecodes = [base32.hyphen(votecode, long_votecode_chunk_length) for votecode in votecodes]

                option_rows = [list(row) for row in zip(options, votecodes, receipts)]
                option_row_cnt = len(option_rows)

                option_table_row_height = Table([[""]], style=option_table_style).wrap(page_width, page_height)[1]

                row = 0
                while row < option_row_cnt:

                    include_option_table_header = (row == 0)

                    # Find the number of options that can fit in this page.

                    option_table_available_height = available_height - v_padding
                    if include_option_table_header:
                        if available_height < total_height:
                            option_table_available_height -= 2 * v_padding
                        option_table_available_height -= question_table_height + option_table_row_height

                    option_table_available_row_cnt = int(option_table_available_height // option_table_row_height)

                    if option_table_available_row_cnt < 1:
                        elements.append(Spacer(page_width, available_height))
                        elements.extend(footer_elements)
                        elements.append(PageBreak())
                        elements.extend(header_elements)
                        available_height = total_height
                        continue

                    # Prepare one- or two-column option table.

                    if question.layout_is_one_column:

                        option_table_row_cnt = min(option_table_available_row_cnt, option_row_cnt - row)
                        option_table_rows = option_rows[row: row + option_table_row_cnt]

                        include_option_table_footer = (row + option_table_row_cnt == option_row_cnt)

                        if include_option_table_header:
                            option_table_rows = [option_table_header_row] + option_table_rows

                    elif question.layout_is_two_column:

                        option_table_row_cnt = min(2 * option_table_available_row_cnt, option_row_cnt - row)

                        start = row // 2
                        stop = (2 * start + option_table_row_cnt) - (2 * start + option_table_row_cnt) // 2
                        option_table_offset = int(math.ceil(option_row_cnt / 2))

                        include_option_table_footer = (row + option_table_row_cnt == option_row_cnt)

                        option_table1_rows = option_rows[start: stop]

                        if include_option_table_header:
                            option_table1_rows = [option_table_header_row] + option_table1_rows

                        option_table2_rows = option_rows[start + option_table_offset: stop + option_table_offset]

                        if include_option_table_header:
                            option_table2_rows = [option_table_header_row] + option_table2_rows

                        if len(option_table2_rows) < len(option_table1_rows):
                            option_table2_rows.append(["", "", ""])

                        option_table_rows = [r1 + [""] + r2 for r1, r2 in zip(option_table1_rows, option_table2_rows)]

                    option_table = Table(
                        data=option_table_rows,
                        colWidths=option_table_column_widths,
                        style=option_table_style
                    )

                    if include_option_table_header:
                        option_table.setStyle(option_table_header_style)

                    if include_option_table_footer:
                        option_table.setStyle(option_table_footer_style)

                    # Add the question and option tables to the document.

                    if include_option_table_header:
                        if available_height < total_height:
                            elements.append(Spacer(page_width, 2 * v_padding))
                            available_height -= 2 * v_padding
                        elements.append(question_table)
                        available_height -= question_table_height

                    elements.append(Spacer(page_width, v_padding))
                    elements.append(option_table)
                    available_height -= v_padding + option_table.wrap(page_width, page_height)[1]

                    row += option_table_row_cnt

            elements.append(Spacer(page_width, available_height))
            elements.extend(footer_elements)
            elements.append(PageBreak())

        # Generate the PDF file.

        pdf = io.BytesIO()
        pdf_list.append(pdf)

        doc = SimpleDocTemplate(
            filename=pdf,
            pagesize=pagesize,
            topMargin=v_margin, bottomMargin=v_margin, leftMargin=h_margin, rightMargin=h_margin,
            author="DEMOS Voting",
            subject=_("Election %(id)s") % {'id': election.id},
            title=_("Ballot %(serial_number)s") % {'serial_number': ballot.serial_number},
        )
        doc.build(elements)

    return pdf_list if len(ballots) > 1 else pdf_list[0]
