FROM python:3.12-slim

WORKDIR /usr/src/app

RUN apt-get update && apt-get install -y stockfish
RUN pip install boto3 chess

COPY . /usr/src/app

CMD ["python", "analysis.py"]