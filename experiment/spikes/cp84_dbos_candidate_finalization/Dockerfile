FROM python:3.11-slim-bookworm@sha256:0a310eeecf4e1f5a0743f9a6520c90c88d089c903ca5fd283f501e3a805f5f89

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1 PYTHONPATH=/app/candidates:/app
WORKDIR /app
COPY spikes/a2_gateway_workspace/requirements.txt /tmp/a2-requirements.txt
COPY spikes/cp79_dbos_gateway/requirements.txt /tmp/dbos-requirements.txt
RUN python -m pip install --no-cache-dir -r /tmp/a2-requirements.txt -r /tmp/dbos-requirements.txt
COPY candidates/api.py /app/candidates/api.py
COPY contracts /app/contracts
COPY spikes/cp84_dbos_candidate_finalization/test_dbos_candidate_finalization.py /app/test_dbos_candidate_finalization.py
USER 10001:10001
CMD ["python", "/app/test_dbos_candidate_finalization.py"]
