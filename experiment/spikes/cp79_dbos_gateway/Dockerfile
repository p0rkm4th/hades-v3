FROM python:3.11-slim-bookworm@sha256:0a310eeecf4e1f5a0743f9a6520c90c88d089c903ca5fd283f501e3a805f5f89

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
RUN mkdir -p /state && chown 10001:10001 /state
COPY spikes/cp79_dbos_gateway/requirements.txt /app/requirements.txt
RUN python -m pip install --no-cache-dir -r /app/requirements.txt
COPY spikes/cp79_dbos_gateway/setup.py /app/setup.py
COPY spikes/cp79_dbos_gateway/worker.py /app/worker.py
COPY spikes/cp79_dbos_gateway/verify.py /app/verify.py
USER 10001:10001
