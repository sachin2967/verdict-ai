# Start from an official, lightweight Python base image
FROM python:3.11-slim

# Set the working directory inside the container to /app
# All subsequent commands will run from this directory
WORKDIR /app

# Copy the requirements file first. Docker is smart and will only re-run this
# step if requirements.txt changes, speeding up future builds.
COPY requirements.txt .

# Install your Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the rest of your application's code into the container
COPY . .

# Install Gunicorn, a production-ready server for your Flask app
RUN pip install gunicorn

# Tell Docker that your app will be listening on port 5000 inside the container
EXPOSE 5000

# The command to execute when the container starts.
# This runs your app using Gunicorn with 4 worker threads.
# Replace 'app:app' if your Flask entrypoint file is named differently (e.g., 'run:app')
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:5000", "run:app"]