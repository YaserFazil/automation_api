# Use an official Ubuntu runtime as a parent image
FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && apt-get install -y \
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    git \
    && apt-get clean

# Set the working directory
WORKDIR /tool

# Copy the current directory contents into the container at /tool
COPY . /tool

# Install any needed packages specified in requirements.txt
RUN python3.11 -m pip install --no-cache-dir -r requirements.txt

# Make port 80 available to the world outside this container
EXPOSE 80

# Define environment variable
ENV FLASK_APP=app.py

# Run the application
CMD ["gunicorn", "-b", "0.0.0.0:80", "wsgi:app"]
