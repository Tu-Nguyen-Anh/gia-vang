# Sử dụng một base image Python chính thức, gọn nhẹ
FROM python:3.10-slim

# Thiết lập thư mục làm việc bên trong container
WORKDIR /app

# Tạo thư mục log cho Supervisor
RUN mkdir -p /var/log/supervisor

# Cài đặt Supervisor và các gói hệ thống cần thiết
# apt-get update: Cập nhật danh sách gói
# apt-get install -y supervisor: Cài đặt Supervisor
# -y: Tự động đồng ý
# --no-install-recommends: Không cài các gói đề xuất không cần thiết
RUN apt-get update && apt-get install -y supervisor --no-install-recommends && rm -rf /var/lib/apt/lists/*

# Sao chép file requirements.txt vào trước để tận dụng cache của Docker
COPY requirements.txt .

# Cài đặt các thư viện Python cần thiết
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép toàn bộ mã nguồn của ứng dụng vào thư mục làm việc
COPY . .

# Sao chép file cấu hình của Supervisor vào đúng vị trí của nó trong container
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Lệnh sẽ được thực thi khi container khởi động
# Khởi động Supervisor, nó sẽ tự động chạy các file python đã được cấu hình
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
