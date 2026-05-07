FROM python:3.12-slim

RUN pip install --no-cache-dir pydantic

WORKDIR /workspace

COPY sandbox/runner.py /agent/runner.py

CMD ["tail", "-f", "/dev/null"]
