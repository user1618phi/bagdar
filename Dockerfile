FROM python:3.12-slim
WORKDIR /app
COPY meje ./meje
COPY content ./content
COPY web ./web
COPY docs/results.json docs/results_real.json ./docs/
RUN useradd --create-home --uid 10001 meje
USER meje
ENV HOST=0.0.0.0 PORT=8000
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request,os; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/health')"
CMD ["python", "-m", "meje", "serve", "--no-browser"]
