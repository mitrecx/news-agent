#!/bin/bash
# News Agent 代码部署脚本
# 用法: ./deploy.sh [env-file]
# 示例: ./deploy.sh .env

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# 加载环境变量
load_env() {
    local env_file="${1:-.env}"

    if [ ! -f "$env_file" ]; then
        log_error "错误: 找不到环境变量文件 $env_file"
    fi

    log_info "加载环境变量: $env_file"

    # 导出环境变量（忽略注释和空行，移除行尾注释）
    while IFS='=' read -r key value; do
        # 跳过注释行和空行
        [[ "$key" =~ ^#.*$ ]] && continue
        [[ -z "$key" ]] && continue

        # 移除行尾注释和空白
        value=$(echo "$value" | cut -d'#' -f1 | xargs)

        # 导出环境变量
        export "$key=$value"
    done < "$env_file"

    # 检查必要的环境变量
    required_vars=(
        "SERVER_HOST"
        "SERVER_USER"
        "DEEPSEEK_API_KEY"
    )

    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            log_error "错误: 环境变量 $var 未设置"
        fi
    done

    log_success "环境变量加载完成"
}

# 显示配置信息
show_config() {
    log_info "部署配置:"
    echo "  服务器地址: $SERVER_HOST:$SERVER_PORT"
    echo "  SSH 用户: $SERVER_USER"
    echo "  项目路径: ${SERVER_PROJECT_PATH:-$HOME/news-agent}"
    echo ""
}

# 测试 SSH 连接
test_ssh_connection() {
    log_info "测试 SSH 连接..."

    if ssh -o ConnectTimeout=10 -o BatchMode=yes "$SERVER_USER@$SERVER_HOST" "echo 'SSH 连接成功'" >/dev/null 2>&1; then
        log_success "SSH 连接测试通过"
    else
        log_error "错误: 无法连接到服务器 $SERVER_HOST"
    fi
}

# 上传项目文件到服务器
upload_project() {
    log_info "上传项目文件到服务器..."

    local project_path="${SERVER_PROJECT_PATH:-$HOME/news-agent}"

    # 创建服务器上的项目目录
    ssh "$SERVER_USER@$SERVER_HOST" "mkdir -p $project_path"

    # 使用 rsync 同步文件（排除不必要的文件）
    log_info "正在同步文件（这可能需要一些时间）..."
    rsync -avz --progress \
        --exclude='.venv' \
        --exclude='__pycache__' \
        --exclude='node_modules' \
        --exclude='.git' \
        --exclude='*.pyc' \
        --exclude='.DS_Store' \
        --exclude='._*' \
        --exclude='dist' \
        ./ \
        "$SERVER_USER@$SERVER_HOST:$project_path/"

    log_success "项目文件上传完成"
}

# 在服务器上部署项目
deploy_project() {
    log_info "部署项目..."

    local project_path="${SERVER_PROJECT_PATH:-$HOME/news-agent}"

    ssh "$SERVER_USER@$SERVER_HOST" "
    set -e

    cd $project_path

    echo '=== 配置环境变量 ==='

    # 创建 .env 文件
    cat > .env << ENVFILE
# DeepSeek API
DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY
DEEPSEEK_BASE_URL=${DEEPSEEK_BASE_URL:-https://api.deepseek.com/v1}

# 服务配置
HOST=127.0.0.1
PORT=${PORT:-8000}

# Agent 配置
AGENT_MODEL=${AGENT_MODEL:-deepseek-chat}
AGENT_TEMPERATURE=${AGENT_TEMPERATURE:-0.7}
AGENT_MAX_TOKENS=${AGENT_MAX_TOKENS:-2000}

# 微博热搜
WEIBO_SCRAPER_TIMEOUT=${WEIBO_SCRAPER_TIMEOUT:-10}
WEIBO_USE_SELENIUM=${WEIBO_USE_SELENIUM:-true}

# 数据库配置
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}
DB_NAME=${DB_NAME:-news_agent}

# JWT 配置
JWT_SECRET=${JWT_SECRET}
ENVFILE

    echo '环境变量配置完成'

    echo ''
    echo '=== 构建前端 ==='
    cd src/frontend-vue

    # 清理 dist 目录
    echo '清理 dist 目录...'
    sudo rm -rf dist
    mkdir -p dist

    npm install
    npm run build

    echo ''
    echo '=== 部署前端静态文件 ==='
    sudo mkdir -p /var/www/news-agent
    sudo cp -r dist/* /var/www/news-agent/
    sudo chown -R nginx:nginx /var/www/news-agent/
    sudo chmod -R 755 /var/www/news-agent/

    "

    log_success "项目部署完成"
}

# 重启后端服务
restart_service() {
    log_info "重启后端服务..."

    ssh "$SERVER_USER@$SERVER_HOST" "
    set -e

    echo '=== 重启后端服务 ==='
    sudo systemctl restart news-agent-backend || sudo systemctl start news-agent-backend
    sudo systemctl enable news-agent-backend

    echo ''
    echo '=== 检查服务状态 ==='
    sudo systemctl status news-agent-backend | head -10

    "

    log_success "后端服务重启完成"
}

# 测试部署
test_deployment() {
    log_info "测试部署..."

    echo ""
    echo "=== 服务访问信息 ==="
    echo "前端地址: http://$SERVER_HOST"
    echo "API 文档: http://$SERVER_HOST/api/docs"
    echo "健康检查: http://$SERVER_HOST/health"
    echo ""

    # 测试健康检查
    log_info "测试健康检查端点..."
    if curl -s "http://$SERVER_HOST/health" | grep -q "ok"; then
        log_success "健康检查通过"
    else
        log_warning "健康检查失败，请检查服务状态"
    fi

    echo ""
    log_success "部署完成！"
    echo ""
    echo "查看日志: ssh $SERVER_USER@$SERVER_HOST 'sudo journalctl -u news-agent-backend -f'"
}

# 主函数
main() {
    local env_file="${1:-.env}"
    local skip_confirm=false

    # 检查是否跳过确认
    #if [[ "$2" == "--yes" ]] || [[ "$2" == "-y" ]]; then
        skip_confirm=true
    #fi

    echo -e "${BLUE}"
    echo "======================================"
    echo "    News Agent 代码部署脚本"
    echo "======================================"
    echo -e "${NC}"
    echo ""

    # 加载环境变量
    load_env "$env_file"

    # 显示配置
    show_config

    # 确认部署
    if [ "$skip_confirm" = false ]; then
        echo -n "${YELLOW}确认开始部署? (yes/no): ${NC}"
        read -r confirm
        if [[ "$confirm" != "yes" ]]; then
            log_warning "部署已取消"
            exit 0
        fi
    else
        log_warning "自动确认模式: 跳过确认步骤"
    fi

    echo ""

    # 执行部署步骤
    test_ssh_connection
    upload_project
    deploy_project
    restart_service
    test_deployment

    echo ""
    log_success "===================="
    echo "   部署成功完成！"
    echo "===================="
}

# 运行主函数
main "$@"
