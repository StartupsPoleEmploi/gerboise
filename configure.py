#! /usr/bin/env python
import argparse
import json
import os
import subprocess
import sys
try:
    # Define a portable input function
    input = raw_input# pylint: disable=redefined-builtin
except NameError:
    pass


def main():
    parser = argparse.ArgumentParser(description="Configure an Kibana/Elasticsearch application for your app")
    parser.add_argument('app', help="Application name (letters only)")
    args = parser.parse_args()
    configure(args.app)

def configure(app):
    config = get_app_config(app)
    configure_nginx(app, config)
    configure_docker(app, config)
    configure_auth(app)
    print("Elasticsearch will be available on 127.0.0.1:92{id} (without auth) and on 0.0.0.0:93{id} (with auth)".format(id=config['id']))
    print("Kibana will be available on 0.0.0.0:56{} (with auth)".format(config['id']))
    print("""You can now run the docker containers for your app by running:

      cd apps/{}/
      docker-compose up -d
""".format(app))

    print("""On your application server, run log collection:

      cd apps/{}/
      ES_PASSWORD=yourpassword docker-compose -f docker-compose-fluentbit.yml up -d
""".format(app))

def configure_nginx(app, config):
    print('Generating nginx config file...')
    mkdir('apps', app, 'nginx')
    with open(os.path.join('apps', app, 'nginx', 'nginx.conf'), 'w') as f:
        f.write(read_template('nginx.template', app, config))

def configure_auth(app):
    print('Generating authentication file...')
    mkdir('apps', app)
    htpasswd_path = os.path.join('apps', app, 'nginx', 'auth')
    if not os.path.exists(htpasswd_path):
        password = ask("Type a password for http authentication to Kibana and Elasticsearch")
        subprocess.call(['htpasswd', '-b', '-c', htpasswd_path, app, password])

def configure_docker(app, config):
    print('Generating docker config file...')
    mkdir('apps', app, 'data')
    mkdir_chmod(0o777, 'apps', app, 'data', 'elasticsearch')
    with open(os.path.join('apps', app, 'docker-compose.yml'), 'w') as f:
        f.write(read_template('docker-compose.template.yml', app, config))
    with open(os.path.join('apps', app, 'docker-compose-fluentbit.yml'), 'w') as f:
        f.write(read_template('docker-compose-fluentbit.template.yml', app, config))

def get_app_config(app):
    config_path = './config.json'
    try:
        global_config = json.load(open(config_path))
    except (ValueError, IOError):
        global_config = {}
    app_config = global_config.get(app, {})

    # Configure Elasticsearch host
    es_host = app_config.get('es_host') or ask(
        "What will be the public address (IP or hostname) of the Elasticsearch server for this app?"
    )
    app_config['es_host'] = es_host

    # Configure app ID
    app_id = app_config.get('id') or ask(
        "Select a 2-number ID (00-99) for this application."
        "This ID cannot be shared between two different applications"
    )
    if len(app_id) != 2 or not app_id.isdigit():
        sys.stderr.write("ERROR Invalid ID format\n")
        sys.exit(1)
    app_ids = {v['id']: k for k, v in global_config.iteritems()}
    if app_id in app_ids and app_ids[app_id] != app:
        sys.stderr.write("ERROR This ID is already taken by application {}\n".format(app_ids[app_id]))
        sys.exit(1)
    app_config['id'] = app_id

    # Save config
    global_config[app] = app_config
    with open(config_path, 'w') as f:
        json.dump(global_config, f, sort_keys=True, indent=4)
    return app_config

def read_template(path, app, config):
    template = open(path).read()
    template = template.replace('__APP__', app)
    template = template.replace('__ES_HOST__', config['es_host'])
    template = template.replace('__ID__', config['id'])
    return template

def ask(question):
    return input(question + ": ")

def mkdir(*path):
    if not os.path.exists(os.path.join(*path)):
        os.makedirs(os.path.join(*path))

def mkdir_chmod(mode, *path):
    if not os.path.exists(os.path.join(*path)):
        os.makedirs(os.path.join(*path), mode=mode)

if __name__ == '__main__':
    main()
