from __future__ import with_statement
import os
import time

#from fabric.api import hosts, run, sudo, cd
#from fabric.state import env
#from fabric.contrib.files import exists, append
#from fabric.utils import warn
#from fabric_helpers.servers import NginxServer, ApacheServer, Machines

#from fabric.api import abort, cd, env, get, hide, hosts, local, prompt, \
#    put, require, roles, run, runs_once, settings, show, sudo, warn

from fabric.api import *
from fabric.contrib.files import append, exists


################
# Environment SETUPS
###############
ENVIRONMENTS = {
    'dev': 'development',
    'staging': 'staging',
    'production': 'production',
}

def dev():
    setup_environments()
    fab_config(env.ENVIRONMENTS['dev'])

def staging():
    setup_environments()
    fab_config(env.ENVIRONMENTS['staging'])

def production():
    setup_environments()
    fab_config(env.ENVIRONMENTS['production'])

def setup_environments(envs=None):
    if envs:
        env.ENVIRONMENTS = envs
    elif not hasattr(env, 'ENVIRONMENTS'):
        env.ENVIRONMENTS = ENVIRONMENTS

def register_environment(key, value):
    if not hasattr(env, 'ENVIRONMENTS'):
        env.ENVIRONMENTS = {}
    env.ENVIRONMENTS[key] = value


def fab_config(env_name):
    env.name = env_name
    env.hosts = env.MACHINES.get_connections_for_env(env_name)
    env.selected_machines = env.MACHINES.get_by_env(env_name)
    if not hasattr(env, 'git_branch'):
        env.git_branch = 'master'
    if not hasattr(env, 'project_root'):
        env.project_root = os.path.join('/home/', env.user, env.project_name)
    
    env.paths = {
        'live': os.path.join(env.project_root, 'live'),
        'repo': os.path.join(env.project_root, 'repo'),
        'releases': os.path.join(env.project_root, 'releases'),
        'v_env': os.path.join(env.project_root, 'virtual_envs', env.git_branch)
    }
    
    env.paths['config'] = os.path.join(env.paths['live'], 'config')
    env.paths['apps'] = os.path.join(env.paths['live'], 'apps')
    # env.project_path = os.path.join(env.paths['live'], env.project_name) # Not created in the dict as it's symlinked not an actual dir

def initial_install():
    env.project_user = env.user
    env.user = 'root'
    for m in env.selected_machines:
        m.install()
        m.copy_ssh_keys(env.project_user)

def setup():
    install_servers()
    install_global_python_packages()
    project_setup()
    server_config()
    
def install_servers():
    for m in env.selected_machines:
        m.install_servers()

def install_global_python_packages():
    sudo('easy_install --upgrade setuptools')
    sudo('easy_install pip')
    sudo('pip install virtualenv')
    sudo('pip install virtualenvwrapper')

def project_setup():
    create_project_paths()
    clone_repo()
    checkout_latest()
    setup_virtualenv()
    install_project_requirements()
    symlink_release(release=env.release)

def server_config():
    for m in env.selected_machines:
        for s in m.servers:
            s.setup()
    
def create_project_paths():
    for path in env.paths.values():
        if not exists(path):
            run('mkdir -p %s;' % path)

def clone_repo():
    """Do initial clone of the git repo"""
    if exists(env.paths['repo']):
        # If it exists delete it to make sure we get the correct files/repo
        run('rm -rf %s' % env.paths['repo'])
    run('git clone %s %s' % (env.git_repo, env.paths['repo']))
    checkout_latest()

def checkout_latest():
    """Pull the latest code into the git repo and copy to a timestamped release directory"""
    with cd(env.paths['repo']):
        if hasattr(env, 'git_branch'):
            git_branch = run('git branch')
            # If not on the selected branch we need to create it or switch to it
            if git_branch.find("* %s" % env.git_branch) == -1:
                if git_branch.find(' %s' % env.git_branch) == -1:
                    # Branch doesn't exist locally so check it out from the server and switch to it
                    run("git checkout --track -b %s origin/%s" % (env.git_branch, env.git_branch))
                else:
                    # Branch exists but isn't current so switch to it
                    run("git checkout %s" % env.git_branch)
        run("git pull")
    if not exists(env.paths['v_env']):
        # This is a new branch so create a new virtualenv for it
        setup_project_virtualenv()
    env.release = get_git_hash()
    env.paths['release'] = os.path.join(env.paths['releases'], env.release)    
    run('cp -R %s %s; rm -rf %s/.git*' 
        % (env.paths['repo'], env.paths['release'], env.paths['release']))
    
def get_git_hash():
    with cd(env.paths['repo']):
        return run('git rev-parse HEAD')

def setup_virtualenv(site_packages=True):
    if site_packages:
        run('virtualenv %s' % env.paths['v_env'])
    else:
        run('virtualenv --no-site-packages %s' %  env.paths['v_env'])

    machine = env.MACHINES.get_by_host(env.host)
    pth_file = '%s/lib/python%s/site-packages/project.pth' % (
            env.paths['v_env'], str(machine.python_version))

    append(env.paths['live'], pth_file)
    append(env.paths['apps'], pth_file)


def install_project_requirements():
   """Install the required packages using pip"""
   run('pip install -r %s/deploy/requirements_all.txt -E %s' % (env.paths['release'], env.paths['v_env']))
   if exists('%s/deploy/requirements_%s.txt' % (env.paths['release'], env.name)):
        run('pip install -r %s/deploy/requirements_%s.txt -E %s' % (env.paths['release'], env.name, env.paths['v_env']))

def symlink_release(release=None):
    """Symlink our current release, uploads and settings file"""
    if not release:
        # Setting environment variables to current git hasgrelease
        release = get_git_hash()
    release_dir = os.path.join(env.paths['releases'], release)
    
    # Linking the main project
    project_dir = os.path.join(env.paths['live'])
    if exists(project_dir):
        run('rm -rf %s' % project_dir)
    run('ln -s %s %s' % (release_dir, project_dir))
