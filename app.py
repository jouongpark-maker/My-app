from flask import Flask, render_template, request, send_file
from docx import Document
from PIL import Image, ImageDraw, ImageFont
import os
import zipfile
import io

app = Flask(__name__)

UPLOAD_FOLDER = 'tmp'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def process_novel_to_images(word_path, bg_path, font_path, vol_num, ch_num):
    doc = Document(word_path)
    full_text = []
    for para in doc.paragraphs:
        if para.text.strip():
            full_text.append(para.text.strip())
    
    bg_image = Image.open(bg_path)
    img_w, img_h = bg_image.size
    
    # تنظیم ابعاد فونت (می‌توانید بعداً این عدد را تغییر دهید)
    font_size = 28
    try:
        font = ImageFont.truetype(font_path, font_size)
    except:
        font = ImageFont.load_default()
    
    margin_left = int(img_w * 0.1)
    margin_right = int(img_w * 0.1)
    margin_top = int(img_h * 0.15)
    margin_bottom = int(img_h * 0.1)
    max_width = img_w - margin_left - margin_right
    max_height = img_h - margin_top - margin_bottom

    pages_data = []
    current_page_text = []
    current_height = 0
    
    for paragraph in full_text:
        words = paragraph.split(' ')
        current_line = ""
        
        for word in words:
            test_line = current_line + " " + word if current_line else word
            bbox = font.getbbox(test_line)
            line_w = bbox[2] - bbox[0]
            line_h = bbox[3] - bbox[1] + 15
            
            if line_w <= max_width:
                current_line = test_line
            else:
                current_page_text.append(current_line)
                current_height += line_h
                current_line = word
                
                if current_height >= max_height:
                    pages_data.append(current_page_text)
                    current_page_text = []
                    current_height = 0
        
        if current_line:
            current_page_text.append(current_line)
            current_height += 35
            
        if current_height >= max_height:
            pages_data.append(current_page_text)
            current_page_text = []
            current_height = 0

    if current_page_text:
        pages_data.append(current_page_text)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        padding = len(str(len(pages_data)))
        
        for idx, page_lines in enumerate(pages_data):
            page_img = bg_image.copy()
            draw = ImageDraw.Draw(page_img)
            
            header_text = f"Ch {ch_num} - Page {idx+1}"
            draw.text((img_w//2, margin_top - 50), header_text, font=font, fill="#ffd700", anchor="mm")
            
            y_offset = margin_top
            for line in page_lines:
                draw.text((img_w - margin_right, y_offset), line, font=font, fill="#ffffff", anchor="ra")
                bbox = font.getbbox(line)
                y_offset += (bbox[3] - bbox[1] + 15)
            
            img_byte_arr = io.BytesIO()
            page_img.save(img_byte_arr, format='WEBP', quality=85)
            img_byte_arr.seek(0)
            
            image_filename = f"{idx + 1:0{padding}d}.webp"
            zipf.writestr(image_filename, img_byte_arr.read())
            
    zip_buffer.seek(0)
    return zip_buffer

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # بررسی وجود فایل‌ها در درخواست برای جلوگیری از خطای Bad Request
        if 'word' not in request.files or 'background' not in request.files:
            return "خطا: لطفاً هر دو فایل ورد و پس‌زمینه را انتخاب کنید.", 400
            
        word_file = request.files['word']
        bg_file = request.files['background']
        vol = request.form.get('volume', '1')
        ch = request.form.get('chapter', '1')
        
        if word_file.filename == '' or bg_file.filename == '':
            return "خطا: فایل‌های انتخابی نمی‌توانند خالی باشند.", 400
            
        word_path = os.path.join(UPLOAD_FOLDER, word_file.filename)
        bg_path = os.path.join(UPLOAD_FOLDER, bg_file.filename)
        font_path = "B_Yekan.ttf" 
        
        word_file.save(word_path)
        bg_file.save(bg_path)
        
        try:
            zip_output = process_novel_to_images(word_path, bg_path, font_path, vol, ch)
            return send_file(
                zip_output,
                mimetype='application/zip',
                as_attachment=True,
                download_name=f"Novel_Vol{vol}_Ch{ch}.zip"
            )
        except Exception as e:
            return f"خطا در پردازش فایل: {str(e)}", 500
        
    return '''
    <!doctype html>
    <html lang="fa" dir="rtl">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>تایپوگرافی هوشمند ناول موبایل</title>
        <style>
            body { background: #1a1a1a; color: #e0e0e0; font-family: system-ui, Tahoma; text-align: center; padding: 20px; margin: 0; }
            .container { max-width: 450px; margin: 30px auto; background: #2d2d2d; padding: 25px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); }
            h3 { color: #ffd700; margin-bottom: 25px; }
            label { display: block; text-align: right; margin-top: 15px; font-size: 14px; color: #aaa; }
            input[type=file], input[type=text] { display: block; margin: 8px 0; padding: 12px; width: 100%; border-radius: 8px; border: 1px solid #444; background: #222; color: #fff; box-sizing: border-box; }
            button { background: #ffd700; color: #1a1a1a; font-weight: bold; font-size: 16px; cursor: pointer; margin-top: 25px; padding: 14px; width: 100%; border: none; border-radius: 8px; transition: 0.2s; }
            button:hover { background: #ffcc00; }
        </style>
    </head>
    <body>
        <div class="container">
            <h3>تایپوگرافی و تبدیل مانهوایی ناول</h3>
            <form method="post" enctype="multipart/form-data">
              <label>فایل ورد رمان (.docx):</label>
              <input type="file" name="word" accept=".docx" required>
              
              <label>عکس پس‌زمینه (بک‌گراند):</label>
              <input type="file" name="background" accept="image/*" required>
              
              <label>شماره ولوم (Volume):</label>
              <input type="text" name="volume" value="1">
              
              <label>شماره چپتر (Chapter):</label>
              <input type="text" name="chapter" value="1">
              
              <button type="submit">بزن بریم و خروجی ZIP بگیر!</button>
            </form>
        </div>
    </body>
    </html>
    '''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
    
