FROM python:3.12-slim

WORKDIR /app

COPY . /app

RUN pip install setuptools
RUN pip install Cython
RUN pip install --no-binary=h5py h5py
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "main.py"]
