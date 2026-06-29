
from flask import Flask, render_template, request, send_file
from docx import Document
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display
import os
import zipfile
import io

app = Flask(__name__)
UPLOAD_FOLDER = 'tmp'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# کش کردن متون پردازش شده برای بالا بردن چشمگیر سرعت سرور
_cache = {}
def reshape_text(text):
    if text in _cache:
        return _cache[text]
    reshaped = arabic_reshaper.reshape(text)
    result = get_display(reshaped)
    _cache[text] = result
    return result

def process_novel_to_images(word_path, bg_path, title_font_path, body_font_path, vol_num, ch_num):
    doc = Document(word_path)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    
    bg_image = Image.open(bg_path)
    img_w, img_h = bg_image.size
    
    body_font_size = int(img_h * 0.022) 
    title_font_size = int(img_h * 0.04)
    
    font_body = ImageFont.truetype(body_font_path, body_font_size) if body_font_path else ImageFont.load_default()
    font_title = ImageFont.truetype(title_font_path, title_font_size) if title_font_path else font_body

    margin_left = int(img_w * 0.12)
    margin_right = int(img_w * 0.12)
    margin_top = int(img_h * 0.14)
    margin_bottom = int(img_h * 0.12)
    max_width = img_w - margin_left - margin_right
    max_height = img_h - margin_top - margin_bottom

    pages_data = []
    current_page_text = []
    current_height = 0
    
    # الگوریتم سریع‌تر برای شکستن خطوط
    for para in paragraphs:
        words = para.split(' ')
        current_line = ""
        
        for word in words:
            test_line = current_line + " " + word if current_line else word
            # برای تست ابعاد خط، از کش سریع استفاده میکنیم
            test_reshaped = reshape_text(test_line)
            bbox = font_body.getbbox(test_reshaped)
            line_w = bbox[2] - bbox[0]
            line_h = (bbox[3] - bbox[1]) + int(body_font_size * 0.5)
            
            if line_w <= max_width:
                current_line = test_line
            else:
                if current_line:
                    current_page_text.append(current_line)
                    current_height += line_h
                current_line = word
                
                if current_height >= max_height:
                    pages_data.append(current_page_text)
                    current_page_text = []
                    current_height = 0
        
        if current_line:
            current_page_text.append(current_line)
            current_height += int(body_font_size * 1.2)
            
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
            y_offset = margin_top
            
            if idx == 0:
                ch_title = reshape_text(f"چپتر {ch_num}")
                draw.text((img_w // 2, y_offset), ch_title, font=font_title, fill="#ffd700", anchor="mm")
                y_offset += title_font_size + int(body_font_size * 2)
            
            for line in page_lines:
                if not line.strip():
                    continue
                final_line = reshape_text(line)
                draw.text((img_w - margin_right, y_offset), final_line, font=font_body, fill="#ffffff", anchor="ra")
                bbox = font_body.getbbox(final_line)
                y_offset += (bbox[3] - bbox[1]) + int(body_font_size * 0.5)
            
            img_byte_arr = io.BytesIO()
            # بهینه‌سازی فشرده‌سازی برای ملو کردن کار سرور
            page_img.save(img_byte_arr, format='WEBP', quality=80, method=2)
            img_byte_arr.seek(0)
            
            image_filename = f"{idx + 1:0{padding}d}.webp"
            zipf.writestr(image_filename, img_byte_arr.read())
            
    zip_buffer.seek(0)
    return zip_buffer

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'word' not in request.files or 'background' not in request.files:
            return "خطا: فایل‌های اصلی انتخاب نشده‌اند.", 400
            
        word_file = request.files['word']
        bg_file = request.files['background']
        title_font = request.files.get('title_font')
        body_font = request.files.get('body_font')
        
        vol = request.form.get('volume', '1')
        ch = request.form.get('chapter', '1')
        
        word_path = os.path.join(UPLOAD_FOLDER, word_file.filename)
        bg_path = os.path.join(UPLOAD_FOLDER, bg_file.filename)
        word_file.save(word_path)
        bg_file.save(bg_path)
        
        title_font_path = os.path.join(UPLOAD_FOLDER, title_font.filename) if title_font and title_font.filename != '' else ""
        body_font_path = os.path.join(UPLOAD_FOLDER, body_font.filename) if body_font and body_font.filename != '' else ""
        
        if title_font_path: title_font.save(title_font_path)
        if body_font_path: body_font.save(body_font_path)
        
        try:
            zip_output = process_novel_to_images(word_path, bg_path, title_font_path, body_font_path, vol, ch)
            return send_file(
                zip_output,
                mimetype='application/zip',
                as_attachment=True,
                download_name=f"Novel_Vol{vol}_Ch{ch}.zip"
            )
        except Exception as e:
            return f"خطا در پردازش: {str(e)}", 500
        
    return '''
    <!doctype html>
    <html lang="fa" dir="rtl">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>تایپوگرافی حرفه‌ای ناول</title>
        <style>
            body { background: #121212; color: #e0e0e0; font-family: Tahoma; text-align: center; padding: 10px; margin: 0; }
            .container { max-width: 480px; margin: 20px auto; background: #1e1e1e; padding: 20px; border-radius: 12px; border: 1px solid #333; }
            h2 { color: #ffd700; font-size: 20px; margin-bottom: 20px; }
            label { display: block; text-align: right; margin-top: 12px; font-size: 13px; color: #bbb; }
            input[type=file], input[type=text] { display: block; margin: 6px 0; padding: 10px; width: 100%; border-radius: 6px; border: 1px solid #444; background: #2a2a2a; color: #fff; box-sizing: border-box; font-size: 14px; }
            button { background: #ffd700; color: #111; font-weight: bold; font-size: 15px; cursor: pointer; margin-top: 20px; padding: 12px; width: 100%; border: none; border-radius: 6px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>تایپوگرافی مانهوایی ناول (نسخه موبایل)</h2>
            <form method="post" enctype="multipart/form-data">
              <label>فایل ورد رمان (.docx):</label>
              <input type="file" name="word" accept=".docx" required>
              
              <label>عکس پس‌زمینه خام:</label>
              <input type="file" name="background" accept="image/*" required>
              
              <label>فونت عنوان صفحه اول (مثل Afsaneh.ttf):</label>
              <input type="file" name="title_font" accept=".ttf,.otf">
              
              <label>فونت متن اصلی (مثل B-Titr.ttf):</label>
              <input type="file" name="body_font" accept=".ttf,.otf">
              
              <input type="text" name="volume" placeholder="شماره ولوم" value="1">
              <input type="text" name="chapter" placeholder="شماره چپتر" value="1">
              
              <button type="submit">پردازش و دانلود فایل ZIP تصاویر</button>
            </form>
        </div>
    </body>
    </html>
    '''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
        
