FROM python:3.9-slim

WORKDIR /app

# Install system dependencies (needed for psycopg2)
RUN apt-get update && apt-get install -y libpq-dev gcc

# Copy files
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY etl.py .

# Run the script
CMD ["python", "etl.py"]