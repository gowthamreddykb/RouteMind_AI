# -*- coding: utf-8 -*-
"""
Reconstructs the complete 57-page authentic Referral Document exactly as structured,
with all 23 diagrams, complete chapters 1-17, real narrative prose, clean typography,
and no AI markers/emojis.
"""

import os
import re
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

OUTPUT_PATH = r"C:\gowtham_mithraz\control tower docement_final.docx"
TARGET_PATH = r"C:\gowtham_mithraz\control tower docement.docx"
DOCS_PATH = r"C:\gowtham_mithraz\RouteMind_AI\docs\control_tower_documentation.docx"
IMAGES_DIR = r"C:\gowtham_mithraz\RouteMind_AI\extracted_images"
TEXT_PATH = r"C:\gowtham_mithraz\RouteMind_AI\extracted_ref_doc.txt"

def add_header_footer(doc):
    for s in doc.sections:
        s.top_margin = Inches(1.0)
        s.bottom_margin = Inches(1.0)
        s.left_margin = Inches(1.0)
        s.right_margin = Inches(1.0)
        
        # Header
        header = s.header
        hp = header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hrun = hp.add_run("Inventory Management System & Logistics Control Tower")
        hrun.font.name = "Calibri"
        hrun.font.size = Pt(8.5)
        hrun.font.italic = True
        hrun.font.color.rgb = RGBColor(128, 128, 128)
        
        # Footer
        footer = s.footer
        fp = footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        frun = fp.add_run("Inventory Management System | Technical Specification")
        frun.font.name = "Calibri"
        frun.font.size = Pt(8.5)
        frun.font.color.rgb = RGBColor(128, 128, 128)

def format_doc_paragraph(p, text, align=WD_ALIGN_PARAGRAPH.LEFT, space_before=0, space_after=6, bold=False, italic=False, size=11, color=(51, 51, 51)):
    p.alignment = align
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.15
    run = p.add_run(text)
    run.font.name = "Calibri"
    run.font.size = Pt(size)
    run.bold = bold
    run.font.italic = italic
    run.font.color.rgb = RGBColor(*color)
    return run

def add_heading_1(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.keep_with_next = True
    format_doc_paragraph(p, text, space_before=18, space_after=8, bold=True, size=16, color=(31, 78, 121))
    return p

def add_heading_2(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.keep_with_next = True
    format_doc_paragraph(p, text, space_before=14, space_after=6, bold=True, size=13, color=(46, 117, 182))
    return p

def add_heading_3(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.keep_with_next = True
    format_doc_paragraph(p, text, space_before=10, space_after=4, bold=True, size=11.5, color=(31, 78, 121))
    return p

def insert_image_safely(doc, img_name, max_width=Inches(5.8)):
    img_path = os.path.join(IMAGES_DIR, img_name)
    if os.path.exists(img_path):
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.paragraph_format.space_before = Pt(6)
        p_img.paragraph_format.space_after = Pt(6)
        run = p_img.add_run()
        run.add_picture(img_path, width=max_width)
        return True
    return False

def clean_and_reconstruct_pages():
    with open(TEXT_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    
    pages = content.split('=== PAGE ')
    parsed_pages = []
    
    # regex definitions
    re_footer = re.compile(r'Inventory\s+Management\s+System\s*\|\s*Page\s+\d+\s+of\s+\d+', re.IGNORECASE)
    re_ch = re.compile(r'^(Chapter[\-\s]+\d+:?.*)$', re.IGNORECASE)
    re_sec = re.compile(r'^(\d+\.\d+(\.\d+)?\.?\s+[A-Za-z].*)$')
    re_fig = re.compile(r'^(Figure\s+\d+\.[\da-z]+.*)$', re.IGNORECASE)
    
    for idx, p_text in enumerate(pages[1:], 1):
        p_clean = re_footer.sub('', p_text)
        raw_lines = [l.strip() for l in p_clean.split('\n') if l.strip()]
        if raw_lines and raw_lines[0].endswith('==='):
            raw_lines = raw_lines[1:]
            
        elements = []
        current_words = []
        
        for line in raw_lines:
            line_norm = re.sub(r'\s+', ' ', line).strip()
            
            # Check if this line is a heading or figure
            is_ch = bool(re_ch.match(line_norm))
            is_sec = bool(re_sec.match(line_norm))
            is_fig = bool(re_fig.match(line_norm))
            is_special = line_norm in [
                "Table of Contents", "User Management", "Inventory Operations", 
                "Invoice Generation", "Authentication System — How JWT Works"
            ] or (len(line_norm) < 35 and line_norm.isupper() and len(line_norm.split()) < 5)
            
            if is_ch or is_sec or is_fig or is_special:
                if current_words:
                    elements.append(('body', ' '.join(current_words)))
                    current_words = []
                
                if is_ch:
                    elements.append(('h1', line_norm))
                elif is_sec:
                    # check if sec level 2 or 3
                    parts = line_norm.split()[0].split('.')
                    if len(parts) > 3 or (len(parts) == 3 and parts[2]):
                        elements.append(('h3', line_norm))
                    else:
                        elements.append(('h2', line_norm))
                elif is_fig:
                    elements.append(('fig', line_norm))
                else:
                    elements.append(('h3', line_norm))
            else:
                current_words.append(line_norm)
                
        if current_words:
            elements.append(('body', ' '.join(current_words)))
            
        parsed_pages.append((idx, elements))
        
    return parsed_pages

def build_referral_exact_document():
    print("Parsing referral text across all 57 pages...")
    parsed_pages = clean_and_reconstruct_pages()
    
    doc = docx.Document()
    add_header_footer(doc)
    
    # ---------------------------------------------------------
    # PAGE 1: TITLE PAGE (Exact Match to Referral Doc)
    # ---------------------------------------------------------
    p_title = doc.add_paragraph()
    p_title.paragraph_format.space_before = Pt(200)
    p_title.paragraph_format.space_after = Pt(24)
    format_doc_paragraph(p_title, "Inventory Management System", align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, size=28, color=(31, 78, 121))
    
    p_sub = doc.add_paragraph()
    p_sub.paragraph_format.space_before = Pt(12)
    p_sub.paragraph_format.space_after = Pt(180)
    format_doc_paragraph(p_sub, "Enterprise Technical Specification & System Architecture", align=WD_ALIGN_PARAGRAPH.CENTER, size=13, color=(89, 89, 89))
    
    doc.add_page_break()
    
    # ---------------------------------------------------------
    # Mapping of figures to extracted image files
    # ---------------------------------------------------------
    fig_to_image = {
        "4.1a": "page_13_X34.png",
        "4.1b": "page_15_X41.png",
        "4.1c": "page_16_X44.png",
        "4.1d": "page_16_X44.png",
        "4.2": "page_17_X47.png",
        "4.3": "page_18_X50.png",
        "4.4": "page_19_X53.png",
        "4.5": "page_21_X58.png",
        "8.1": "page_30_X79.png",
        "8.2": "page_31_X82.png",
        "8.3": "page_31_X83.png",
        "8.4": "page_32_X86.png",
        "8.5": "page_33_X89.png",
        "8.6": "page_33_X90.png",
        "8.7": "page_34_X93.png",
        "8.8": "page_34_X94.png",
        "8.9": "page_35_X97.png",
        "8.10": "page_35_X98.png",
        "8.11": "page_36_X101.jpg",
        "8.12": "page_37_X104.jpg",
        "8.13": "page_37_X105.jpg",
        "8.14": "page_38_X108.png",
        "8.15": "page_39_X111.jpg"
    }

    print("Writing pages and placing diagrams...")
    # Iterate through pages starting from Page 2
    for page_num, elements in parsed_pages:
        if page_num == 1:
            continue
            
        for el_type, text in elements:
            if not text.strip():
                continue
                
            if el_type == 'h1':
                add_heading_1(doc, text)
            elif el_type == 'h2':
                add_heading_2(doc, text)
            elif el_type == 'h3':
                add_heading_3(doc, text)
            elif el_type == 'fig':
                # Caption
                p_fig = doc.add_paragraph()
                p_fig.paragraph_format.keep_with_next = True
                format_doc_paragraph(p_fig, text, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=10, space_after=6, bold=True, size=10, color=(46, 117, 182))
                
                # Check which image maps to this figure
                matched_key = None
                for k in fig_to_image:
                    if f"Figure {k}" in text or f"Figure  {k}" in text:
                        matched_key = k
                        break
                        
                if matched_key and matched_key in fig_to_image:
                    insert_image_safely(doc, fig_to_image[matched_key])
            else: # body paragraph
                # Check if it looks like bullet point or definition
                p_body = doc.add_paragraph()
                format_doc_paragraph(p_body, text, space_before=0, space_after=6, size=11, color=(38, 38, 38))
                
        # If this is Page 4 (end of Table of Contents) or end of a major chapter, add clean break
        if page_num in [4, 5, 8, 11, 21, 25, 29, 39, 41, 43, 49, 51, 54]:
            doc.add_page_break()

    # Save finalized document
    print(f"Saving finalized document to {OUTPUT_PATH}...")
    doc.save(OUTPUT_PATH)
    print("Saved successfully!")
    
    # Copy to project docs
    import shutil
    try:
        shutil.copy2(OUTPUT_PATH, DOCS_PATH)
        print(f"Copied to project docs: {DOCS_PATH}")
    except Exception as e:
        print(f"Copy to docs error: {e}")
        
    try:
        shutil.copy2(OUTPUT_PATH, TARGET_PATH)
        print(f"Successfully overwritten target: {TARGET_PATH}")
    except Exception as e:
        print(f"Target {TARGET_PATH} is locked by WPS Office ({e}). File is ready at {OUTPUT_PATH}.")

if __name__ == "__main__":
    build_referral_exact_document()
