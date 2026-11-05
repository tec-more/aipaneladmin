# DeepSeek Harness (dsh) Dockerfile
# 基于 Node.js 24 + pnpm monorepo 构建
# 构建: docker build -t dsh:latest -f deploy/dsh/Dockerfile .
# 注意：构建上下文为项目根目录（以便访问 deepseek-harness/ 源码）
#
# 国内网络友好：基础镜像与 npm 源默认走国内镜像，海外环境用 build-arg 覆盖：
#   docker build --build-arg NODE_IMAGE=node:24-bookworm-slim \
#     --build-arg NPM_REGISTRY=https://registry.npmjs.org ...

# ===== 全局 ARG（供 FROM 使用；必须在第一个 FROM 之前声明）=====
ARG NODE_IMAGE=docker.m.daocloud.io/library/node:24-bookworm-slim
ARG NPM_REGISTRY=https://registry.npmmirror.com

FROM ${NODE_IMAGE} AS builder

# ARG 必须在每个 stage 内重新声明才可引用（否则 buildkit 报 UndefinedVar）
ARG NPM_REGISTRY=https://registry.npmmirror.com

# 构建上下文刻意排除 .git（见根 .dockerignore），浏览器构建元数据会调用
# `git rev-parse HEAD` 取提交号；无 .git 时必然失败，这里用合成提交号短路该逻辑。
# 需要真实提交号时传入：--build-arg DSH_CLIENT_COMMIT_HASH=$(git rev-parse HEAD)
ARG DSH_CLIENT_COMMIT_HASH=0000000000000000000000000000000000000000
ENV DSH_CLIENT_COMMIT_HASH=${DSH_CLIENT_COMMIT_HASH}

# 依赖走国内 npm 源（corepack/pnpm 均读取该环境变量）
ENV npm_config_registry=${NPM_REGISTRY}

# 构建工具链：
#   - git：构建元数据会调用 `git rev-parse HEAD`
#   - build-essential：native/system 直接用 `cc` 编译 C 扩展（flock.c → system.node），
#     slim 镜像不含编译器会报 `spawnSync cc ENOENT`
#   - python3：node-gyp 兜底编译需要
RUN apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates build-essential python3 \
 && rm -rf /var/lib/apt/lists/*

# pnpm 包管理器（Corepack 自带，版本与仓库 package.json 锁定一致）
RUN corepack enable && corepack prepare pnpm@11.28.5 --activate

WORKDIR /build

# ── 依赖安装层：利用 Docker 缓存，仅当依赖变更时重新 install ──
# 先拷贝 workspace 配置和根 package.json
COPY deepseek-harness/package.json ./
COPY deepseek-harness/pnpm-workspace.yaml ./
COPY deepseek-harness/pnpm-lock.yaml ./

# 再拷贝 vendor（Cordis vendored 源码）和根 patches
COPY deepseek-harness/vendor ./vendor
COPY deepseek-harness/patches ./patches

# 安装根级依赖（此时没有 packages/apps 源码，workspace 依赖会被跳过）
# 注：此步允许失败（根级预装，缺 workspace 源码属预期），故显式 || true
RUN pnpm install --frozen-lockfile --ignore-scripts || true

# ── 源码层：拷贝完整 monorepo 后执行正式 install + build ──
COPY deepseek-harness ./

# 正式安装（含 workspace 依赖 + 原生模块编译）
# 注：禁止用 `| tail` 收尾——管道会吞掉退出码，构建失败仍会产出残缺镜像
RUN pnpm install --frozen-lockfile

# 构建所有 artifacts（tsc 编译 + tsdown 打包 + Web 前端构建）
RUN pnpm run build

# ── 运行时镜像 ──
FROM ${NODE_IMAGE} AS runtime

# ARG 需在本 stage 重新声明；pnpm 安装与运行时插件管理都读取该源
ARG NPM_REGISTRY=https://registry.npmmirror.com
ENV npm_config_registry=${NPM_REGISTRY}

# 运行时依赖：hostname（取容器 IP）、ca-certificates（HTTPS 证书链）
RUN apt-get update \
 && apt-get install -y --no-install-recommends hostname ca-certificates net-tools \
 && rm -rf /var/lib/apt/lists/*

# 插件页 / `dsh plugin`（profile 插件安装与列举）实际是把参数转发给 pnpm，
# 缺失时报 `spawn pnpm ENOENT`，前端表现为「可能由于网络问题，无法读取全部插件」。
# 这里直接全局安装实体 pnpm（比 corepack shim 稳：不依赖运行时 HOME 下的缓存目录）。
RUN npm install -g pnpm@11.28.5

WORKDIR /app

# 仅拷贝构建产物：node_modules + apps + packages 下的 lib 产物
# （保留完整 workspace 结构以便 dsh CLI 正确解析插件）
COPY --from=builder /build/node_modules ./node_modules
COPY --from=builder /build/apps ./apps
COPY --from=builder /build/packages ./packages
# native/system 是 pnpm workspace 成员（提供 @deepseek-ai/node-addon-system 等包），
# 依赖它的 session-persistence-jsonl / sandbox-local 等插件会按 workspace 软链解析。
# 漏拷该目录会导致启动时报 ERR_MODULE_NOT_FOUND 并让十余个 entry 无法激活。
COPY --from=builder /build/native ./native
COPY --from=builder /build/vendor ./vendor
COPY --from=builder /build/patches ./patches
COPY --from=builder /build/package.json ./package.json
COPY --from=builder /build/pnpm-workspace.yaml ./pnpm-workspace.yaml

# 暴露 Web UI 端口
EXPOSE 3080

# 入口脚本：容器启动时动态解析本机 IP（dsh 拒绝通配地址绑定，必须用具体 IP）
# 容器在 Docker 网络中的地址即 hostname -i 返回值，nginx 通过 docker DNS 服务名
# （dsh:3080）访问，所以绑定容器自身 IP 即可被同编排内其他容器到达
COPY deploy/dsh/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 允许通过环境变量覆盖绑定地址（如手动指定 DSH_HOST=127.0.0.1）
ENV DSH_HOST=
ENV DSH_PORT=3080

ENTRYPOINT ["/entrypoint.sh"]

