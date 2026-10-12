FROM python:3.13-slim-bookworm@sha256:a1165e272e578941b84abc79e4ab38a0305cd12803a5c4247979ac7655f4d641

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY services/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY services/gateway.py /app/gateway.py
COPY services/commitment_simulator.py /app/commitment_simulator.py
COPY services/workspace_runner.py /app/workspace_runner.py
COPY contracts/tools.json /app/tools.json
USER 10001:10001
EXPOSE 8080
CMD ["python", "/app/gateway.py"]
