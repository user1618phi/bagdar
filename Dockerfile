# Bagdar needs nothing but Python: no packages are installed.
FROM python:3.12-slim
WORKDIR /app
COPY bagdar ./bagdar
COPY content ./content
COPY web ./web
COPY docs/results.json docs/results_real.json ./docs/
RUN useradd --create-home --uid 10001 bagdar
USER bagdar
ENV HOST=0.0.0.0 PORT=8000
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request,os; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/health')"
CMD ["python", "-m", "bagdar", "serve", "--no-browser"]
