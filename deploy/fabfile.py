# from __future__ import with_statement
# import os
# import time
# 
# from fabric.api import hosts, run, sudo, cd
# from fabric.contrib.files import exists, append
# from fabric.state import env
# from fabric.utils import warn

from fabric_helpers import *
from fabric_helpers.servers import Machines, Machine, PostgresqlServer, NginxServer, ApacheServer
from project.settings.production import DATABASE_NAME, DATABASE_USER, DATABASE_PASSWORD

# The holder for the various machines that this fabfile is concerned with
MACHINES = Machines()
USER = 'james'

#APACHE = ApacheServer('apache') # Site name should be the name of the config file
POSTGRES = PostgresqlServer()
APACHE = ApacheServer(sites=['django_site'])
NGINX = NginxServer(sites=['django_site'])

# Registering individual machines
MACHINES.register(
    Machine('173.203.86.90', ENVIRONMENTS['production'], 
        short_name="prod", servers=[POSTGRES, APACHE, NGINX])
)

env.MACHINES = MACHINES
env.user = USER
env.project_name = 'zoo'
env.project_folder_name = 'project' 
env.project_root = os.path.join('/home/', USER, env.project_name)
env.git_repo = 'git://github.com/punteney/fab_test.git'
env.DATABASE_NAME = DATABASE_NAME
env.DATABASE_USER = DATABASE_USER
env.DATABASE_PASSWORD = DATABASE_PASSWORD