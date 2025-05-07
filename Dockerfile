# Use an official Python runtime as the base image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any dependencies the app needs (e.g., Flask, xml, etc.)
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port the app will run on
EXPOSE 5001

# Define environment variable (optional)
ENV FLASK_APP=fakearr.py

# Run the application
CMD ["python", "fakearr.py"]
