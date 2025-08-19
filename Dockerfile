# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies for psycopg2 and FAISS
# FAISS requires libblas-dev and liblapack-dev, psycopg2-binary might need libpq-dev
RUN apt-get update && apt-get install -y --no-install-recommends \
    libblas-dev \
    liblapack-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire source code into the container
COPY ./src /app/src

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
# Use Uvicorn to run the FastAPI app
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]