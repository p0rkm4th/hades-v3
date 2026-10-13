FROM mcr.microsoft.com/playwright/python@sha256:640d578aae63cfb632461d1b0aecb01414e4e020864ac3dd45a868dc0eff3078

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m pip install --no-cache-dir playwright==1.55.0
WORKDIR /app
RUN mkdir -p /app/services
COPY tests/ /app/tests/
COPY services/inference_adapter.py /app/services/inference_adapter.py
COPY contracts/tools.json /app/tools.json
COPY contracts/task_lifecycle.py /app/contracts/task_lifecycle.py
COPY contracts/tools.json /app/contracts/tools.json
COPY contracts/task_lifecycle.py /app/candidates/task_lifecycle.py
COPY candidates/api.py /app/candidates/api.py
CMD ["python", "-m", "unittest", "discover", "-s", "/app/tests"]
