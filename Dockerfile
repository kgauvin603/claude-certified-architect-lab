FROM oraclelinux:9

RUN dnf install -y python3.11 python3.11-pip nodejs npm && \
    npm install -g @anthropic-ai/claude-code && \
    dnf clean all

WORKDIR /opt/claude-certified-architect-lab

COPY requirements.txt .
RUN python3.11 -m venv .venv && \
    .venv/bin/pip install --upgrade pip && \
    .venv/bin/pip install -r requirements.txt

COPY . .

ENV PYTHONPATH=/opt/claude-certified-architect-lab

EXPOSE 8000

CMD [".venv/bin/python", "-m", "uvicorn", "src.main:app", \
     "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
