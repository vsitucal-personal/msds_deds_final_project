#!/bin/bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /app/jupyter.key -out /app/jupyter.pem \
    -subj "/"
python -c "from jupyter_server.auth import passwd; print('c.ServerApp.password = \\'{}\\''.format(passwd('JUPYTER_TOKEN')))" > /root/.jupyter/jupyter_server_config.py
exec jupyter lab --ip=0.0.0.0 --port=8889 --certfile jupyter.pem --keyfile jupyter.key --no-browser
