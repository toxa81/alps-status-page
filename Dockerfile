FROM python:3.11-slim

WORKDIR /app

# Install any dependencies specified in requirements.txt
RUN pip install --no-cache-dir fastapi uvicorn sqlalchemy mysql-connector-python

#RUN apt-get update && apt-get install -y git
#
#RUN git clone https://github.com/toxa81/alps-status-page.git

EXPOSE 8000

#CMD ["uvicorn", "backend:app", "--host", "0.0.0.0", "--port", "8000"]

