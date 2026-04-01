FROM nginx:alpine

COPY nginx.conf /etc/nginx/nginx.conf

# 前端构建产物目录
RUN mkdir -p /usr/share/nginx/html

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
