.PHONY: help install test run docker-build docker-up docker-down clean

help:
	@echo "智能体框架 - 常用命令"
	@echo ""
	@echo "  make install      - 安装 Python 依赖"
	@echo "  make test         - 运行测试"
	@echo "  make run          - 启动开发服务器"
	@echo "  make docker-build - 构建 Docker 镜像"
	@echo "  make docker-up    - 启动所有服务"
	@echo "  make docker-down  - 停止所有服务"
	@echo "  make clean        - 清理临时文件"

install:
	cd src && pip install -r requirements.txt

test:
	cd src && pytest

run:
	cd src && uvicorn assistant.main:app --host 0.0.0.0 --port 8000 --reload

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
