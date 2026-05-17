# 🛡️ Aliyun Guard

阿里云 CDT 流量监控与自动化管理控制台。

## ✨ 功能

- 多账户聚合监控，CDT 流量实时展示
- 流量熔断：超阈值自动停机（节省停机 / 普通停机）
- 抢占式实例保活：被回收自动拉起
- 定时开关机计划
- Cloudflare DDNS 联动（IP 变更自动更新 A 记录）
- Telegram 告警通知
- 账单统计（待还款金额，国际站准确）
- 现代化暗色 UI

## 🚀 一键安装

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/lillinlin/AliCDT-Manager/main/install.sh)
```

安装完成后配置 Nginx 反代即可通过域名访问。

## 🔑 所需 RAM 权限

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances", "ecs:DescribeInstanceStatus",
        "ecs:StartInstance", "ecs:StopInstance", "ecs:DeleteInstance"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["cdt:ListCdtInternetTraffic", "cms:DescribeMetricList"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["bssapi:QueryAccountBalance", "bssapi:QueryBillOverview"],
      "Resource": "*"
    }
  ]
}
```

## 🛠 手动部署

```bash
mkdir -p /app/aliyun-guard/data && cd /app/aliyun-guard

cat > docker-compose.yml << EOF
services:
  aliyun-guard:
    image: ghcr.io/YOUR_GITHUB_USERNAME/aliyun-guard:latest
    container_name: aliyun-guard
    restart: always
    ports:
      - "127.0.0.1:8000:8000"
    volumes:
      - ./data:/app/data
    environment:
      - TZ=Asia/Shanghai
      - ADMIN_USERNAME=admin
      - ADMIN_PASSWORD=your_password
      - SECRET_KEY=your_random_secret
EOF

docker compose up -d
```

## Tech Stack

- Backend: Python 3.12 + FastAPI + APScheduler + SQLite
- Frontend: Vue 3 + TailwindCSS
- Deploy: Docker + GitHub Actions → ghcr.io
