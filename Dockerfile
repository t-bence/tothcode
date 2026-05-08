FROM python:3.12-slim

RUN pip install --no-cache-dir pydantic

ENV PYTHONPATH=/agent

WORKDIR /workspace

# Copy only what the runner needs inside the container.
COPY harness/__init__.py /agent/harness/__init__.py
COPY harness/tools/__init__.py /agent/harness/tools/__init__.py
COPY harness/tools/impl.py /agent/harness/tools/impl.py
COPY sandbox/runner.py /agent/runner.py

CMD ["tail", "-f", "/dev/null"]
