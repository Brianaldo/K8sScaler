FROM python:3.11-slim

WORKDIR /app

COPY ./src /app/src
COPY ./models /app/models
COPY ./data /app/data

COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "src/main.py"]
