# Dockerfile for Google Cloud Run deployment
# Optimized for Streamlit multi-page app with SQLite database

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY golf_db.py .
COPY golf_scraper.py .
COPY pages/ ./pages/
COPY components/ ./components/

# Copy optional files if they exist
COPY .env* ./

# Create directory for SQLite database
RUN mkdir -p /app/data

# Create Streamlit config directory and config file
RUN mkdir -p ~/.streamlit
RUN echo "\
[server]\n\
port = 8080\n\
address = 0.0.0.0\n\
headless = true\n\
enableCORS = false\n\
enableXsrfProtection = true\n\
maxUploadSize = 200\n\
\n\
[browser]\n\
gatherUsageStats = false\n\
serverAddress = \"0.0.0.0\"\n\
serverPort = 8080\n\
\n\
[theme]\n\
primaryColor = \"#1f77b4\"\n\
backgroundColor = \"#ffffff\"\n\
secondaryBackgroundColor = \"#f0f2f6\"\n\
textColor = \"#262730\"\n\
font = \"sans serif\"\n\
" > ~/.streamlit/config.toml

# Expose port 8080 (Cloud Run requirement)
EXPOSE 8080

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8080/_stcore/health || exit 1

# Run the Streamlit app
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
