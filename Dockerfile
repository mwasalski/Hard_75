FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app .

EXPOSE 8000
EXPOSE 8501

# Create a script to run both servers
RUN echo '#!/bin/bash\n\
uvicorn main:app --host 0.0.0.0 --port 8000 &\n\
sleep 5 && \n\
streamlit run frontend.py --server.port 8501 --server.address 0.0.0.0\n\
' > /app/start.sh

RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]
