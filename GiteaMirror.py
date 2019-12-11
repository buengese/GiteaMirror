#!/usr/bin/env python3

import github # https://github.com/PyGithub/PyGithub
import gitlab
import requests
import argparse
import json
import sys

gitea_url = "http://git.example.com/api/v1"
gitea_token = ""
github_token = ""



class Gitea(object):

    def __init__(self):
        self.session = requests.Session()  # Gitea
        self.session.headers.update({
            "Content-type": "application/json",
            "Authorization": "token {0}".format(gitea_token),
        })

    def get_org(self, name):
        r = self.session.get("{0}/orgs/{1}".format(gitea_url, name))
        print(r)
        if r.status_code != 200:
            print("Cannot get user details", file=sys.stderr)
            exit(1)

        gitea_uid = json.loads(r.text)["id"]
        return gitea_uid

    def create_org(self, name, description=None):
        m = {
            "username": name,
            "description": description
        }

        jsonstring = json.dumps(m)

        r = self.session.post("{0}/orgs".format(gitea_url), data=jsonstring)
        if r.status_code != 201:
            if r.status_code == 422:
                return
            print(r.status_code, r.text, jsonstring)

    def migrate(self, name, description, clone_url, gitea_uid):
        m = {
            "repo_name": name,
            "description": description,
            "clone_addr": clone_url,
            "mirror": True,
            "uid": gitea_uid,
        }

        jsonstring = json.dumps(m)

        r = self.session.post("{0}/repos/migrate".format(gitea_url), data=jsonstring)
        if r.status_code != 201:  # if not CREATED
            if r.status_code == 409:  # repository exists
                return
            print(r.status_code, r.text, jsonstring)


def mirror_github_user(user, name=None):
    gitea = Gitea()
    gh = github.Github(github_token)

    try:
        usr = gh.get_user(user)
    except github.BadCredentialsException:
        print("Invalid GitHub credentials!")
        sys.exit(1)
    except github.UnknownObjectException:
        print('GitHub User not found!')
        sys.exit(1)

    if name is None:
        name = user

    gitea.create_org(name, usr.bio)
    uid = gitea.get_org(name)

    for repo in usr.get_repos():
        print(repo.full_name)
        gitea.migrate(repo.name, repo.description, repo.clone_url, uid)


def mirror_github_org(organization, name=None):
    gitea = Gitea()
    gh = github.Github(github_token)

    try:
        org = gh.get_organization(organization)
    except github.BadCredentialsException:
        print("Invalid GitHub credentials!")
        sys.exit(1)
    except github.UnknownObjectException:
        print("GitHub Organization not found!")
        sys.exit(1)

    if name is None:
        name = organization

    gitea.create_org(name, org.description)
    uid = gitea.get_org(name)

    for repo in org.get_repos():
        print(repo.full_name)
        gitea.migrate(repo.name, repo.description, repo.clone_url, uid)


def mirror_gitlab_org(gitlab_url, organization, name=None):
    gitea = Gitea()
    gl = gitlab.Gitlab(gitlab_url)

    try:
        org = gl.groups.get(organization)
    except Exception as e:
        print(str(e))
        sys.exit(1)

    if name is None:
        name = organization

    gitea.create_org(name, org.description)
    uid = gitea.get_org(name)

    for repo in org.projects.list(all=True):
        print(repo.name)
        gitea.migrate(repo.name, repo.description, repo.http_url_to_repo, uid)


def mirror_gitlab_user(gitlab_url, user, name=None):
    gitea = Gitea()
    gl = gitlab.Gitlab(gitlab_url)

    try:
        usr = gl.users.get(user)
    except Exception as e:
        print(str(e))
        sys.exit(1)

    if name is None:
        name = user

    gitea.create_org(name, usr.bio)
    uid = gitea.get_org(name)

    for repo in usr.projects.list():
        print(repo)
        gitea.migrate(repo.name, repo.description, repo.http_url_to_repo, uid)


def build_parser():
    # Base
    parser = argparse.ArgumentParser(description='GiteaMirror Command Line Interface')

    mode_group = parser.add_subparsers(dest='mode', help='Which mode to use.')
    mode_group.required = True

    # Github
    mode_parser = mode_group.add_parser('github')
    type_group = mode_parser.add_subparsers(dest='type', help='Which mirror type to create.')
    type_group.required = True

    # We can mirror single projects or entire users or groups
    for mirror_type in ['user', 'group']:
        type_parser = type_group.add_parser(mirror_type)
        type_parser.add_argument('github_path')
        type_parser.add_argument('--name', required=False)

    # Gitlab
    mode_parser = mode_group.add_parser('gitlab')
    type_group = mode_parser.add_subparsers(dest='type', help='Which mirror type to create.')
    type_group.required = True

    for mirror_type in ['user', 'group']:
        type_parser = type_group.add_parser(mirror_type)
        type_parser.add_argument('gitlab_url')
        type_parser.add_argument('gitlab_path')

        type_parser.add_argument('--name', required=False)

    return parser


def main(argv):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.mode == "github":
        if args.type == "user":
            mirror_github_user(args.github_path, args.name)
        if args.type == "group":
            mirror_github_org(args.github_path, args.name)
    if args.mode == "gitlab":
        if args.type == "user":
            mirror_gitlab_user(args.gitlab_url, args.gitlab_path, args.name)
        if args.type == "group":
            mirror_gitlab_org(args.gitlab_url, args.gitlab_path, args.name)


if __name__ == '__main__':
    main(sys.argv[1:])
