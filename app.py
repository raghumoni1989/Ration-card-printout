import os
import shutil
import fitz  # PyMuPDF
import re
from flask import Flask, render_template, request, send_file, jsonify, url_for
from werkzeug.utils import secure_filename
from PIL import Image, ImageDraw

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"
STATIC_FOLDER = "static"
DEFAULT_BG_IMAGE = "static/default_bg.jpg"
BPL_BG_IMAGE = "static/bpl_card.jpg"
APL_BG_IMAGE = "static/apl_card.jpg"
AAY_BG_IMAGE = "static/aay_card.jpg"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(STATIC_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def create_default_background(image_path):
    if not os.path.exists(image_path):
        img = Image.new("RGB", (800, 1125), color=(200, 200, 200))
        draw = ImageDraw.Draw(img)
        draw.text((300, 500), "Default Background", fill=(50, 50, 50))
        img.save(image_path)

create_default_background(DEFAULT_BG_IMAGE)
create_default_background(BPL_BG_IMAGE)
create_default_background(APL_BG_IMAGE)
create_default_background(AAY_BG_IMAGE)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        pdf_file = request.files["pdf"]
        if pdf_file:
            pdf_filename = secure_filename(pdf_file.filename)
            pdf_path = os.path.join(app.config["UPLOAD_FOLDER"], pdf_filename)
            output_pdf_path = os.path.join(OUTPUT_FOLDER, "output.pdf")
            static_pdf_path = os.path.join(STATIC_FOLDER, "output.pdf")

            pdf_file.save(pdf_path)
            bg_image = determine_background_image(pdf_path)
            print(f"[INFO] Background selected: {bg_image}")
            process_pdf(pdf_path, bg_image, output_pdf_path)
            shutil.move(output_pdf_path, static_pdf_path)

            return render_template("preview.html", pdf_url=url_for('static', filename="output.pdf"))
    return render_template("index.html")

def extract_text_from_pdf(pdf_path):
    pdf_doc = fitz.open(pdf_path)
    extracted_text = ""
    
    for page in pdf_doc:
        text = page.get_text("text").strip()
        if not text:
            print("[WARNING] No text found, trying block extraction")
            text = " ".join(block[4] for block in page.get_text("blocks") if isinstance(block[4], str))
        extracted_text += text + " "
    
    pdf_doc.close()
    return extracted_text.strip()

def determine_background_image(pdf_path):
    text_content = extract_text_from_pdf(pdf_path)
    
    # Normalize text: remove special characters, extra spaces, and convert to lowercase
    text_content = re.sub(r"[^a-zA-Z0-9 ]", " ", text_content)  # Remove special characters
    text_content = re.sub(r"\s+", " ", text_content).strip().lower()
    print("[DEBUG] Extracted Text:", text_content[:2000])  # Print first 2000 characters for better visibility
    
    # Improved detection using regex
    if re.search(r"\bantyodaya\b", text_content, re.IGNORECASE):
        print("[INFO] AAY detected due to 'Antyodaya' keyword presence")
        return AAY_BG_IMAGE
    elif "non" in text_content:
        print("[INFO] APL detected due to 'Non' keyword presence")
        return APL_BG_IMAGE
    elif "priority household" in text_content:
        print("[INFO] BPL detected")
        return BPL_BG_IMAGE
    
    print("[WARNING] No specific category detected, using default background")
    return DEFAULT_BG_IMAGE

def process_pdf(pdf_path, img_path, output_pdf_path):
    pdf_doc = fitz.open(pdf_path)
    new_pdf = fitz.open()
    if len(pdf_doc) > 0:
        page = pdf_doc[0]  # Only process the first page
        rect = page.rect
        
        # Remove all PNG images
        for img in page.get_images(full=True):
            try:
                xref = img[0]
                img_info = pdf_doc.extract_image(xref)
                if img_info["ext"] == "png":
                    print(f"[INFO] Removing PNG image on first page")
                    page.delete_image(xref)
            except ValueError:
                continue
        
        new_page = new_pdf.new_page(width=rect.width, height=rect.height)
        if os.path.exists(img_path):
            img_rect = fitz.Rect(0, -188, rect.width, rect.height - 188)
            new_page.insert_image(img_rect, filename=img_path)
        new_page.show_pdf_page(rect, pdf_doc, page.number)
    new_pdf.save(output_pdf_path)
    new_pdf.close()

if __name__ == "__main__":
    app.run(debug=True)
