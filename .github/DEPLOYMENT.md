# Автоматический деплой бэкенда

## Настройка GitHub Actions

### 1. Секреты в GitHub

Добавьте в **Settings → Secrets and variables → Actions**:

```
SSH_HOST=195.133.196.30
SSH_USER=deploy
SSH_PORT=22
SSH_KEY=<приватный ключ deploy пользователя>
REGISTRY_USERNAME=demon
REGISTRY_TOKEN=<PAT с правами write:packages, read:packages>
```

### 2. Настройка сервера

#### Создание пользователя deploy:
```bash
sudo useradd -m -s /bin/bash deploy
sudo usermod -aG docker deploy
sudo mkdir -p /opt/deploy
sudo chown deploy:deploy /opt/deploy
```

#### Копирование файлов:
```bash
# Скопировать docker-compose.yml и docker-compose.override.yml в /opt/deploy/
# Скопировать .env.docker в /opt/deploy/../
# Скопировать deploy_api.sh в /opt/deploy/
sudo chmod +x /opt/deploy/deploy_api.sh
```

#### SSH ключи:
```bash
# На сервере
sudo -u deploy mkdir -p /home/deploy/.ssh
sudo -u deploy chmod 700 /home/deploy/.ssh

# На локальной машине - сгенерировать ключ
ssh-keygen -t ed25519 -f ~/.ssh/deploy_key -C "deploy@server"

# Скопировать публичный ключ на сервер
ssh-copy-id -i ~/.ssh/deploy_key.pub deploy@195.133.196.30

# Приватный ключ (~/.ssh/deploy_key) добавить в SSH_KEY секрет GitHub
```

### 3. Права доступа

Убедитесь, что пользователь deploy может:
- Запускать Docker команды
- Выполнять sudo /opt/deploy/deploy_api.sh
- Читать файлы в /opt/deploy/

### 4. Проверка

После настройки:
1. Сделайте push в main ветку
2. Проверьте Actions вкладку в GitHub
3. Проверьте логи деплоя на сервере

## Структура файлов

```
/opt/deploy/
├── docker-compose.yml
├── docker-compose.override.yml
├── deploy_api.sh
└── ../.env.docker

/home/deploy/.ssh/
├── authorized_keys
└── ...
```

## Troubleshooting

### Ошибки SSH:
- Проверьте права на .ssh директорию (700)
- Проверьте authorized_keys (600)
- Проверьте SSH_KEY секрет в GitHub

### Ошибки Docker:
- Проверьте права пользователя deploy в группе docker
- Проверьте доступность GHCR образа
- Проверьте docker-compose файлы

### Ошибки деплоя:
- Проверьте логи: `docker-compose logs api`
- Проверьте статус: `docker-compose ps`
- Проверьте образ: `docker images | grep technofame-api`
