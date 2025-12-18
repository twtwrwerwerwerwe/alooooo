# Python 3.11 rasmiy image
FROM python:3.11-slim

# System sozlamalar
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Ishchi papka
WORKDIR /app

# Kerakli system paketlar
RUN apt-get update && apt-get install -y \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# requirements.txt ni ko‘chiramiz
COPY requirements.txt .

# Python kutubxonalarni o‘rnatamiz
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Bot fayllarini ko‘chiramiz
COPY . .

# Botni ishga tushirish
CMD ["python", "bot.py"]
