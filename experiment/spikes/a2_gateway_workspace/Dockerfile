FROM python:3.14-slim-bookworm@sha256:48b13b003dda20b16f9442b8475aa05fe21bf6579a8c881db92ffb4d8fd20f83

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1 PYDANTIC_AI_NO_BANNER=1
WORKDIR /app
COPY spikes/a2_gateway_workspace/requirements.txt /app/requirements.txt
RUN python -m pip install --no-cache-dir -r /app/requirements.txt
COPY spikes/a2_gateway_workspace/gateway_workspace.py /app/gateway_workspace.py
COPY spikes/a2_gateway_workspace/probe.py /app/probe.py
COPY spikes/a2_gateway_workspace/test_uncertain_shell.py /app/test_uncertain_shell.py
COPY spikes/a2_gateway_workspace/test_operation_identity_context.py /app/test_operation_identity_context.py
COPY spikes/a2_gateway_workspace/test_step_persistence_interrupted_shell.py /app/test_step_persistence_interrupted_shell.py
USER 10001:10001
CMD ["python", "/app/probe.py"]
