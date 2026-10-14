FROM python:3.11-slim-bookworm@sha256:0a310eeecf4e1f5a0743f9a6520c90c88d089c903ca5fd283f501e3a805f5f89

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY spikes/a2_gateway_workspace/requirements.txt /tmp/a2-requirements.txt
COPY spikes/cp79_dbos_gateway/requirements.txt /tmp/dbos-requirements.txt
RUN python -m pip install --no-cache-dir -r /tmp/a2-requirements.txt -r /tmp/dbos-requirements.txt
COPY spikes/a2_gateway_workspace/gateway_workspace.py /app/gateway_workspace.py
COPY spikes/a2_gateway_workspace/operation_identity.py /app/operation_identity.py
COPY spikes/cp83_a2_dbos_workspace/test_durable_shell_recovery.py /app/test_durable_shell_recovery.py
USER 10001:10001
CMD ["python", "/app/test_durable_shell_recovery.py"]
