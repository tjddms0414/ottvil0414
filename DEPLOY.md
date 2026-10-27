# Render 배포

`render.yaml`은 Python 웹 서비스 한 개를 정의합니다. 이미지 처리 서버가 필요하므로 정적 사이트로 배포하지 마세요. API 키 없이 작동하며 사용자 사진은 서버 디스크에 저장하지 않습니다.

## 계정 연결 후

1. 앱 코드와 `render.yaml`, `requirements.txt`, `static/`을 GitHub 저장소에 올립니다. 현재 클라우드 작업 파일은 자동으로 GitHub에 반영되지 않습니다.
2. https://dashboard.render.com 에서 GitHub 계정을 연결합니다.
3. New → Blueprint에서 이 저장소와 앱 코드가 올라간 브랜치를 선택합니다.
4. 서비스 설정을 확인하고 배포합니다. 기본 설정은 free 플랜입니다. 유료 플랜으로 변경하기 전 요금을 확인하세요.
5. 배포가 완료되면 Render가 서비스에 실제 HTTPS 주소를 부여합니다. 생성되기 전에는 주소를 추측하지 마세요.
6. 해당 주소에서 사진 업로드 → 제품 영역 지정 → 배경 만들기 → PNG 다운로드를 확인합니다.

무료 서비스는 유휴 후 첫 접속이 느릴 수 있고 메모리가 제한됩니다. 먼저 작은 사진으로 검증하세요. 현재 앱의 입력 상한인 4천만 화소는 무료 인스턴스 메모리를 초과할 수 있습니다. 운영 규모와 사진 크기에 맞게 인스턴스를 선택해야 합니다.

## 수동 서비스 설정

- Runtime: Python 3.12.12
- Build: `pip install -r requirements.txt`
- Start: `python -m uvicorn app:app --host 0.0.0.0 --port $PORT --workers 1 --limit-concurrency 2`
- Health check: `/`

## 검증 상태

현재 환경에서 원본 픽셀 보존·브러시·오류 입력 테스트와 Chromium 사용 흐름을 검증했습니다. 공개 서비스에 대한 검증은 배포 및 실제 주소 발급 후 별도로 수행해야 합니다.
