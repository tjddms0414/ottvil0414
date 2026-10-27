# White Room

사진에서 제품 영역을 지정하고 흰색 스튜디오 배경으로 합성하는 한국어 웹 앱입니다.

## 실행

```sh
cd /workspace/ottvil0414
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m uvicorn app:app --host 0.0.0.0 --port 3000
```

사진 업로드 → 제품을 감싸는 사각형 드래그 → 포함/제외 브러시 보정 → 그림자 조절 → 배경 만들기 → PNG 다운로드.

## 처리 방식과 범위

OpenCV GrabCut으로 제품 마스크를 추정하고 원본 RGB 픽셀을 흰 배경에 합성합니다. 제품을 생성하거나 형태를 재구성하지 않습니다. 출력은 원본 해상도이며, 마스크 분석은 최대 1200px로 수행합니다. 경계에는 리샘플링이 적용됩니다. 투명·반사 소재, 배경과 유사한 제품, 복잡한 경계는 보정이 필요하며 완벽한 자동 분리를 보장하지 않습니다. JPG/PNG/WebP, 최대 20MB 및 4천만 화소. 업로드는 메모리에서 처리하며 서버 파일로 저장하지 않습니다. 브라우저에서 선택한 WebP는 첫 프레임을 사용합니다.

## 검증

```sh
.venv/bin/pip install httpx
.venv/bin/python -m unittest discover -s tests -v
node --check static/app.js
```

원본 내부 픽셀 보존, 흰 배경, 포함/제외 브러시, 잘못된 입력을 검사합니다. 실제 Chromium에서 업로드·드래그·처리·다운로드와 모바일 가로 넘침을 확인했습니다.
