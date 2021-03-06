from __future__ import with_statement
import os
from fabric.api import *
from fabric.contrib.files import append, exists


##########
# Helper functions
##########


def push():
    project_update()
    restart_servers()
    
def push_quick():
    project_quick_update()
    code_reload()

def initial_install():
    for m in env.selected_machines:
        m.copy_ssh_keys(env.user)
        m.install()
    install_servers()
    install_global_python_packages()
    project_setup()
    server_config()
    restart_servers()

# def delete_old_releases():
#     releases = get_releases()
#     # Leave the last 10 releases
#     if len(releases) > 10:
#         for release in releases[:-10]:
#             delete_release(str(release))

# def rollback():
#     # This will rollback to the previous release
#     # Any system changes will still be in effect though
#     # installed packages, db changes, global configs, etc.
#     symlink_release(release=set_release('20100420170116'))

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

def project_update():
    """Updates the project to the latest version, installs all requirements and applies patches"""
    checkout_latest()
    install_project_requirements()
    symlink_release(release=env.release)
    syncdb()

def project_quick_update():
    """Updates the project to the latest version, installs all requirements and applies patches"""
    checkout_latest()
    symlink_release(release=env.release)

def server_config():
    for m in env.selected_machines:
        for s in m.servers:
            s.setup()
 
def syncdb():
    run_env('export CONFIG_IDENTIFIER=production; cd %s; django-admin.py syncdb --settings=project.settings --noinput' % env.paths['live'])
    
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

def checkout_latest():
    """Pull the latest code into the git repo and copy to a hashtag release directory"""
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
        setup_virtualenv()
    env.release = get_git_hash()
    env.paths['release'] = os.path.join(env.paths['releases'], env.release)    
    if not exists(env.paths['release']):
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
   run_env('pip install -r %s/deploy/requirements_all.txt' % (env.paths['release']))
   if exists('%s/deploy/requirements_%s.txt' % (env.paths['release'], env.name)):
        run_env('pip install -r %s/deploy/requirements_%s.txt' % (env.paths['release'], env.name))

def symlink_release(release=None):
    """Symlink our current release, uploads and settings file"""
    if not release:
        # Setting environment variables to current git hasgrelease
        release = get_git_hash()
    release_dir = os.path.join(env.paths['releases'], release)
    
    # Linking the main project
    project_dir = env.paths['live']
    if exists(project_dir):
        run('rm -rf %s' % project_dir)
    run('ln -s %s %s' % (release_dir, project_dir))
    
    # Linking the virtual_env shortcut
    env_dir = os.path.join(env.paths['live'], 'v_env')
    if exists(env_dir):
        run('rm -rf %s' % env_dir)
    run('ln -s %s %s' % (env.paths['v_env'], env_dir))


def restart_servers():
    for m in env.selected_machines:
        for s in m.servers:
            s.restart()

def code_reload():
    for m in env.selected_machines:
        for s in m.servers:
            s.code_reload()    

# Runs the command within the virtualenv
def run_env(cmd, *a, **kw):
    run("source %s; %s" % (os.path.join(env.paths['v_env'], 'bin/activate'), cmd), *a, **kw)