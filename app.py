import os
import io
import cv2
import torch
import easyocr
import numpy as np
from PIL import Image
from hanspell import spell_checker
from flask import Flask, request, redirect, url_for, render_template_string, send_from_directory, flash
from datetime import datetime
import sqlite3

# --- 설정 ---
UPLOAD_FOLDER = "uploads"
DB_PATH = "memos.db"
ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'your-secret-key'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- 고급 전처리 함수 ---
def advanced_preprocess(image_path):
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    binary = cv2.adaptiveThreshold(gray, 255,
                                   cv2.ADAPTIVE_THRESH_MEAN_C,
                                   cv2.THRESH_BINARY_INV,
                                   15, 10)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    morph = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)
    sharp = cv2.Laplacian(morph, cv2.CV_8U)
    return Image.fromarray(sharp)

# --- OCR 함수 (오류 방지 포함) ---
def read_korean_text(image_path, min_confidence=0.4):
    reader = easyocr.Reader(['ko', 'en'], gpu=torch.cuda.is_available())
    try:
        result = reader.readtext(image_path, detail=0, paragraph=True)
        result = [line for line in result if len(line.strip()) > 0]
        full_text = " ".join(result)
        if len(full_text.strip()) == 0:
            return "(텍스트 없음)"

        # 맞춤법 검사 예외 처리
        try:
            corrected = spell_checker.check(full_text).checked
        except Exception as e:
            print(f"[맞춤법 검사 실패] {e}")
            corrected = full_text

        return corrected
    except Exception as e:
        print(f"[OCR 실패] {e}")
        return "(OCR 실패)"

# --- DB 초기화 및 저장 함수 ---
def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS memos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            text TEXT,
            created_at TEXT
        )
    ''')
    con.commit()
    con.close()

def save_memo(filename, text):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute('INSERT INTO memos (filename, text, created_at) VALUES (?, ?, ?)',
                (filename, text, datetime.utcnow().isoformat()))
    con.commit()
    con.close()

def search_memos():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT id, filename, text, created_at FROM memos ORDER BY created_at DESC")
    rows = cur.fetchall()
    con.close()
    return rows

# --- HTML 템플릿 ---
INDEX_HTML = """
<!doctype html>
<title>OCR 메모</title>
<h2>OCR 업로드</h2>
<form method=post enctype=multipart/form-data action="{{ url_for('upload') }}">
  <input type=file name=file>
  <input type=submit value="Upload">
</form>
<hr>
<ul>
{% for r in rows %}
  <li><b>{{ r[1] }}</b> — {{ r[3] }}<br><pre>{{ r[2] }}</pre></li>
{% endfor %}
</ul>
"""

# --- 라우터 ---
@app.route('/')
def index():
    rows = search_memos()
    return render_template_string(INDEX_HTML, rows=rows)

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        flash('파일이 없습니다')
        return redirect(url_for('index'))

    f = request.files['file']
    if f.filename == '':
        flash('파일 선택하세요')
        return redirect(url_for('index'))

    ext = f.filename.rsplit('.', 1)[-1].lower()
    if ext not in ALLOWED_EXT:
        flash('지원되지 않는 파일 형식입니다.')
        return redirect(url_for('index'))

    filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{f.filename}"
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    f.save(path)

    # 전처리 후 OCR 수행
    processed_img = advanced_preprocess(path)
    tmp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"processed_{filename}")
    processed_img.save(tmp_path)

    text = read_korean_text(tmp_path)
    save_memo(filename, text)

    flash("업로드 및 OCR 완료")
    return redirect(url_for('index'))

# --- 앱 실행 ---
if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
