# 使用官方 Python 基础镜像
FROM python:3.10.9-slim

# 设置工作目录
WORKDIR /app

# 将 requirements.txt 复制到容器中
COPY requirements.txt /app/

# 安装 Python 依赖项
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件到容器中
COPY . /app/

# 设置环境变量
ENV PYTHONUNBUFFERED=1

# 使用环境变量启动 Django 应用程序
CMD ["sh", "-c", "python manage.py runserver 0.0.0.0:$LLAMA_API_PORT"]
