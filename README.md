# 한국 주식 재무 정보 조회 웹페이지

Node.js 기반 로컬 서버를 사용하는 웹페이지입니다. 한글 종목명을 입력하면 KRX 종목코드로 검색한 뒤, Naver 금융 데이터에서 기본 재무 지표를 조회합니다.

## 실행 방법

1. 터미널에서 `C:\뉴욕사무소\vs code` 폴더로 이동합니다.
2. `npm install`을 실행하여 의존성을 설치합니다.
3. `npm start`를 실행하여 서버를 시작합니다.
   - 포트 3000이 이미 사용 중이라면 PowerShell에서 `$env:PORT=3001; npm start`로 실행하세요.
4. 브라우저에서 `http://localhost:3000` 또는 다른 포트를 열어 접속합니다.

## 사용 방법

1. 검색창에 한글 종목명을 입력합니다.
2. 조회 버튼을 클릭합니다.
3. 시가총액, 매출액, 영업이익, PER, PBR, 영업이익률, 매출성장률, 이익성장률 결과가 표시됩니다.

## 구현 정보

- `index.html`: 사용자 인터페이스
- `styles.css`: 기본 스타일
- `script.js`: 검색 요청과 결과 표시
- `server.js`: KRX 종목명-코드 매핑 및 Naver 금융 데이터 프록시
- `krx_list.json`: KRX 종목 목록 (회사명, 종목코드)

## 참고

- 성장률 항목은 일부 종목의 경우 페이지에서 직접 제공되지 않아 `정보 없음`으로 표시될 수 있습니다.

## KRX 종목 목록 자동 갱신

- `krx_list.json`은 KRX 상장 종목 목록을 로컬에서 읽는 데이터 파일입니다.
- 신규 상장 또는 상장폐지 반영을 위해서는 이 파일을 최신화해야 합니다.
- 수동으로 갱신하려면 `python update_krx_list.py`를 실행하세요.
- GitHub에 배포된 경우 `.github/workflows/update-krx-list.yml`이 매주 자동으로 `krx_list.json`을 갱신하고 변경 사항을 커밋하도록 설정되어 있습니다.

## Streamlit 앱 실행

1. Python 가상환경을 준비합니다.
2. `pip install -r requirements.txt`를 실행합니다.
3. `streamlit run app.py`를 실행합니다.
4. 브라우저에서 `http://localhost:8501`을 열어 접속합니다.

## GitHub + Streamlit 배포

1. Git 저장소를 초기화하거나 기존 리모트를 사용합니다.
   - `git init`
   - `git add .`
   - `git commit -m "Add Streamlit app for Korean stock lookup"`
2. GitHub에서 새 리포지토리를 생성합니다.
3. 리모트를 추가하고 푸시합니다.
   - `git remote add origin <YOUR_REPO_URL>`
   - `git branch -M main`
   - `git push -u origin main`
4. Streamlit Cloud에 GitHub 리포지토리를 연결합니다.
   - 메인 파일: `app.py`
   - 패키지 파일: `requirements.txt`
   - 배포 후 Streamlit이 자동으로 앱을 빌드합니다.
