import requests
import json

def ocr_space_api(image_path, api_key='K89244882588957', language='kor'):
    url_api = "https://api.ocr.space/parse/image"

    with open(image_path, 'rb') as f:
        response = requests.post(
            url_api,
            files={"filename": f},
            data={
                "apikey": api_key,
                "language": language,
                "OCREngine": 2,                # 최신 엔진 사용
                "isOverlayRequired": False,    # 텍스트 좌표 불필요시 False
                "scale": True,                 # 이미지 확대 분석
                "detectOrientation": True,     # 회전된 이미지 자동 보정
                "isTable": True,               # 표 형태 인식 향상
                "iscreatesearchablepdf": False # PDF 생성 안함
            },
            timeout=60
        )

    result = response.json()

    # 응답 확인
    if result.get("IsErroredOnProcessing"):
        print("❌ OCR 처리 중 오류 발생:", result.get("ErrorMessage"))
        return ""

    parsed = result.get("ParsedResults")
    if not parsed:
        print("⚠️ 인식 결과가 없습니다.")
        return ""

    text_detected = parsed[0].get("ParsedText", "")
    return text_detected.strip()

# 실행 예시
text_result = ocr_space_api('001_2.jpg', api_key='K89244882588957')
print("📄 인식된 텍스트:")
print(text_result)
