FROM python:3.10-slim

# 작업 디렉토리 설정
WORKDIR /app

# requirements 복사 및 설치
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 전체 코드 복사
COPY . .

# outputs 폴더 생성 및 volume 설정
RUN mkdir -p /app/outputs
VOLUME ["/app/outputs"]

# uvicorn 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--reload", "--port", "9000"]
