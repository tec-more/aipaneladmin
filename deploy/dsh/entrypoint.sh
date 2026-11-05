#!/bin/sh
# DeepSeek Harness 入口脚本
# dsh 拒绝 0.0.0.0 / :: 等通配地址绑定（安全策略：防止端口暴露到所有接口）
# Docker 容器内 hostname -i 返回容器在 docker 网络中的具体 IP，
# nginx 通过 docker DNS 服务名 dsh:3080 解析到该 IP，实现容器间通信

set -e

# 优先使用环境变量 DSH_HOST（若显式指定），否则动态取容器 IP
if [ -n "$DSH_HOST" ]; then
  HOST="$DSH_HOST"
else
  # hostname -i 可能返回多个地址（IPv4 + IPv6），取第一个
  HOST=$(hostname -i 2>/dev/null | awk '{print $1}')
  # 兜底：如果 hostname -i 失败（某些网络模式），用 getent 查 hosts
  if [ -z "$HOST" ]; then
    HOST=$(getent hosts "$(hostname)" 2>/dev/null | awk '{print $1; exit}')
  fi
  # 最终兜底：127.0.0.1（仅容器内可访问，nginx 无法到达；此时需手动设 DSH_HOST）
  if [ -z "$HOST" ]; then
    HOST="127.0.0.1"
    echo "[dsh] WARNING: 无法自动解析容器 IP，将绑定 127.0.0.1（仅容器内可访问）"
    echo "[dsh]        如需外部访问，请在 docker-compose.yml 中设置 DSH_HOST=<容器IP>"
  fi
fi

PORT="${DSH_PORT:-3080}"

echo "[dsh] binding to ${HOST}:${PORT}"
echo "[dsh] DEEPSEEK_API_KEY ${DEEPSEEK_API_KEY:+已配置（长度 ${#DEEPSEEK_API_KEY}）}"

# 浏览器侧认证：dsh web 强制 cookie + 一次性 token，登录链接按此公开地址打印。
# 容器自身 IP（如 172.x.x.x）在宿主机浏览器上不可达，必须用外部可达地址。
PUBLIC_URL_ARGS=""
if [ -n "$DSH_PUBLIC_URL" ]; then
  echo "[dsh] public url: ${DSH_PUBLIC_URL}"
  PUBLIC_URL_ARGS="--public-url $DSH_PUBLIC_URL"
fi

# --trusted-host 可额外放行代理域名（host 或 host:port，空格分隔，可多个）
TRUSTED_ARGS=""
for authority in $DSH_TRUSTED_HOSTS; do
  TRUSTED_ARGS="$TRUSTED_ARGS --trusted-host $authority"
done

# shellcheck disable=SC2086
exec node apps/cli/lib/bin.js web --host "$HOST" --port "$PORT" --no-open $PUBLIC_URL_ARGS $TRUSTED_ARGS
