from celery import Celery

# Test redis server, TODO: import the real app and use the same broker from config.

app = Celery('galaxy', broker='redis://localhost', include=['galaxy.celery.tasks'])


if __name__ == '__main__':
    app.start()
