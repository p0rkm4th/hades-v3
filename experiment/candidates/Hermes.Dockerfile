FROM python:3.14-slim-bookworm@sha256:48b13b003dda20b16f9442b8475aa05fe21bf6579a8c881db92ffb4d8fd20f83

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1 HOME=/home/hermes HERMES_HOME=/home/hermes/.hermes
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
ARG HERMES_COMMIT=e4d86423856350825a3a0dc4f52aed89759e11bd
RUN git init /opt/hermes \
    && git -C /opt/hermes remote add origin https://github.com/NousResearch/hermes-agent.git \
    && git -C /opt/hermes fetch --depth 1 origin ${HERMES_COMMIT} \
    && git -C /opt/hermes checkout --detach FETCH_HEAD \
    && pip install --no-cache-dir uv==0.13.0 \
    && cd /opt/hermes && uv sync --locked --extra web --extra mcp --extra messaging --no-default-groups --no-install-project
WORKDIR /app
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin hermes \
    && mkdir -p /home/hermes/.hermes \
    && mkdir -p /var/hades-task /var/hades-trace \
    && chown -R hermes:hermes /home/hermes /var/hades-task /var/hades-trace
COPY candidates/api.py /app/candidates/api.py
COPY contracts/task_lifecycle.py /app/candidates/task_lifecycle.py
COPY candidates/mcp_proxy.py candidates/hermes_config.yaml.in candidates/hermes_start.py /app/
COPY contracts/tools.json /app/contracts/tools.json
USER hermes
ENTRYPOINT ["python", "/app/hermes_start.py"]
