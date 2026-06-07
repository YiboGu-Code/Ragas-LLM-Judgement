- 进入项目根目录：`e:\Homework\SEEC3\RagasTest`
- 确保同目录有 `.env`（至少包含 `ARK_API_KEY=...`）

```bash
# 1) 构建前后端镜像（镜像名已在 docker-compose.yml 里固定为 ragastest-*:local）
docker compose build

# 2) （可选）启动验证联通
docker compose up -d
curl http://localhost:8000/healthz
curl http://localhost/api/healthz

# 3) 打包导出为 tar（输出到项目根目录）
docker save -o ragastest-images.tar ragastest-backend:local ragastest-frontend:local

# 4) （可选）停止并清理容器
docker compose down
```

- 产物：`e:\Homework\SEEC3\RagasTest\ragastest-images.tar`
- 在另一台机器导入并启动：

```bash
docker load -i ragastest-images.tar
docker compose up -d
```
