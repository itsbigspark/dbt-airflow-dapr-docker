FROM python:3.11
WORKDIR /app

# Copy only the requirements file first
COPY requirements.txt .

# Install dependencies
RUN pip install -r requirements.txt

# Copy the rest of the application
COPY . .

RUN ls -la /app
CMD ["python", "-m", "streamlit", "run", "app.py"]
# ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]