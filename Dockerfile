# Use the official Playwright image for Python (includes pip & Chromium deps)
FROM mcr.microsoft.com/playwright/python:v1.52.0-noble

WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose the port (SnapDeploy auto-detects this, but it's good practice)
EXPOSE 8000

# Start the Flask app
CMD ["python", "app.py"]
