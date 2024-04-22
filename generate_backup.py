import json
import requests
import os
import sys
import csv
import subprocess
import getpass
import pathlib

import argparse
import time
from typing import NamedTuple
from datetime import timedelta


class Args(NamedTuple):
    """ Command-line arguments """
    url: str
    deploy: str


def get_args() -> Args:
    """ Get command-line arguments """
    parser = argparse.ArgumentParser(
        description='Script for generating backups',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('url', metavar='url', help='url of the service')
    parser.add_argument('deploy', metavar='deploy', help='name of the deploy')

    args = parser.parse_args()

    return Args(args.url, args.deploy)


def get_list_db(url):
    action_url = "http://{}/web/database/list".format(url)
    data = {"params": {}}
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(action_url, data=json.dumps(data), headers=headers)
        db = response.json()
    except requests.exceptions.RequestException as e:
        print("URL:", url)
        print("Connection establishment failed!")
        print(e)
        print("------------------------------")
        db = {"error": e}

    return db


def dump_db_odoo(db_name):
    try:
        operation = subprocess.check_output('sh odoo-backup.sh {}'.format(db_name), shell=True).decode('utf-8')
        print('Backup files generated!')

        output_from_script = operation.splitlines()
        dump_name = output_from_script[-1]

    except subprocess.CalledProcessError as e:
        dump_name = None
        print("Error generating backup files: ")
        print(e)

    return dump_name


def upload_dump_to_s3(list_db, data):
    deploy = data['deploy']
    directory = data['directory']
    for db in list_db:
        print('DATABASE:', db)
        if 'test' in db:
            print('Test database will not be downloaded!!!')
            continue
        else:
            dump_name = dump_db_odoo(db)
            if dump_name:
                bucket_name = 's3://backups-odoo-prod/{}/{}/{}'.format(deploy, db, dump_name)
                dir_dump = '{}{}'.format(directory, dump_name)
                operation = 'aws s3 cp {} {} --acl public-read --no-progress --only-show-errors'.format(dir_dump, bucket_name)
                print('Uploading...')
                os.system(operation)
                print('Bucket:', bucket_name)
                os.system('rm {}*'.format(directory))
        print('-------------------------------------')


def generate_backups(url, deploy):
    current_user = getpass.getuser()
    file_route = "/home/{0}/backup/".format(current_user)

    if not pathlib.Path(file_route).exists():
        os.system("mkdir /home/{0}/backup/".format(current_user))

    data = {
        'deploy': deploy,
        'directory': '/home/{0}/backup/'.format(current_user)
    }

    db = get_list_db(url)
    if db.get('error'):
        print('¡CONNECTION PROBLEM!\n Review data and try again.')
    else:
        list_db = db['result']
        print('DEPLOY:', data['deploy'])
        upload_dump_to_s3(list_db, data)


def main():
    start_time = time.time()

    args = get_args()
    url, deploy = args.url, args.deploy

    try:
        generate_backups(url, deploy)
    except Exception as e:
        print("Error: ")
        print(e)
        print('-------------------------------------')


    end_time = time.time()  # Tiempo de finalización de la ejecución
    execution_time = timedelta(seconds=end_time - start_time)  # Calcular tiempo de ejecución
    print("Execution time:", execution_time)


if __name__ == '__main__':
    main()

