FROM python:3.13-slim-bookworm@sha256:a1165e272e578941b84abc79e4ab38a0305cd12803a5c4247979ac7655f4d641

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY candidates/requirements.lock.txt /app/requirements.lock.txt
RUN pip install --no-cache-dir -r /app/requirements.lock.txt
COPY candidates/api.py candidates/index.html candidates/run_trial.py /app/candidates/
COPY contracts/tools.json /app/contracts/tools.json
COPY contracts/task_lifecycle.py /app/candidates/task_lifecycle.py
RUN mkdir -p /hermes/amber-task /hermes/amber-trace /hermes/cobalt-task /hermes/cobalt-trace \
    && chown -R 10001:10001 /hermes
USER 10001:10001
EXPOSE 8080
CMD ["python", "/app/candidates/api.py"]
