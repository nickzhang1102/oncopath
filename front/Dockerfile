# 构建阶段
FROM node:22-alpine AS builder

WORKDIR /app

# 使用国内 npm 镜像源
RUN npm config set registry https://registry.npmmirror.com

# 复制package文件
COPY package*.json ./

# 按 lockfile 安装依赖
RUN npm ci

# 复制源代码
COPY . .

# 构建
RUN npm run build

# 运行阶段
FROM nginx:alpine

# 删除默认配置，避免冲突
RUN rm /etc/nginx/conf.d/default.conf

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制nginx配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
