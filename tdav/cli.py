#!/usr/bin/env python3

from webdav3.client import Client
import webdav3.exceptions

# import sys
import click

import re
import os
import keyring
import readline
import dateutil
import shlex
import jinja2

from datetime import datetime
from pprint import pprint

from .param import param

# import tdav.config

# ==========================================================================
# Global variables

theclient = None

# filepatterns = [
# # lambda x: re.sub(".*/notes.pdf", "Lecture Notes.pdf", x),
# # lambda x: re.sub("notes.pdf", "Lecture Notes.pdf", x),
#
# # lambda x: re.sub(".*/\wps\d.pdf", "/Statistical Physics/Lecture Notes.pdf", x),
# # lambda x: re.sub("wps\d.pdf", "/Statistical Physics/Lecture Notes.pdf", x),
#
# lambda x:
#   re.sub(".*/(2020-\d\d-\d\d) \d\d\.\d\d\.\d\d Statistical Physics 94813308411/zoom_0.mp4",
#          "/Statistical Physics/Zoom Recordings/\\1.mp4", x),
# ]
#
# put_regex_patterns = [
# ("wps\\d.pdf", "/Statistical Physics/Problem Set / Tutorial \\\\1.pdf"),
# ]
#
# for p in put_regex_patterns:
#     filepatterns.append( lambda x: re.sub(p[0],p[1],x))
#     filepatterns.append( lambda x: re.sub(".*/"+p[0],p[1],x))
#
# # print(filepatterns)

# ==========================================================================
# The default entry point can either call a subcommand directly if specified
# on the command line, or starts an interactive shell otherwise.

@click.group(invoke_without_command=True, chain=True)
@click.option('-v', '--verbose', count=True)
@click.pass_context
def cli(ctx, verbose):

    # Instantiate the config object of type tdav.param
    ctx.ensure_object( param )

    cfg = ctx.obj

    if cfg.connect is not None:
        url  = cfg.connect['url']
        user = cfg.connect['username'] if 'username' in cfg.connect else None
        pw   = cfg.connect['password'] if 'password' in cfg.connect else None

        _connect( url, user, pw )

    cfg.verbosity += verbose

    if ctx.invoked_subcommand is None:
        cmd = cli.get_command(ctx,'shell')
        # cmd.parse_args(ctx,sys.argv[1:])
        cmd.invoke(ctx)


@cli.command()
@click.argument("filename")
def load(filename):
    loadfile(filename)

def loadfile(filename):
    try:
        with open(filename) as f:
            for i,line in enumerate(f):
                run_textcommand(line)

    except FileNotFoundError:
        click.echo(click.style(f"ERROR: file '{filename}' not found", fg='red'))

    except click.UsageError as ex:
        click.echo(click.style(f"ERROR in {filename}:{i}: {ex}", fg='red'))


@cli.command()
def shell():

    while True:
        line = input("> ")

        try:
            run_textcommand(line)

        except click.UsageError as ex:
            click.echo(click.style(f"ERROR: {ex}", fg='red'))


# def run_textcommand(ctx,line):
def run_textcommand(line):

    tokens = shlex.split(line, comments=True)
    # print(tokens)

    cmd = cli.get_command(click.get_current_context(), tokens[0])

    if cmd is None:
        raise click.UsageError(f"unknown command '{tokens[0]}'")

    ctx = cmd.make_context(tokens[0], tokens[1:])
    cmd.invoke(ctx)


@cli.command()
@click.argument("url")
@click.option("--username")
@click.option("--password", default=None)
def connect(url,username,password=None):

    _connect(url,username,password)


def _connect(url,username,password):

    options = dict(
      webdav_hostname = url,
      webdav_login = username,
      webdav_password = password )

    if options['webdav_password'] is None:
        m = re.search('(https?://[a-zA-Z\.]+)', url)
        if m:
            server = m.group(1)
            options['webdav_password'] = keyring.get_password(server, username)

    global theclient
    theclient = Client(options)
    # theclient.verify()

@cli.command()
@click.argument("path",default="")
def ls(path):
    # global theclient

    if theclient is None:
        print("error: not connected")
        return

    for f in theclient.list(path,get_info=True):

        if f['isdir']:
            print("d", end="  ")
        else:
            print(".", end="  ")

        timefmt = "%Y-%m-%d %H:%M:%S"
        if f['modified'] is None:
            ti = dateutil.parser.parse(f['created'])
        else:
            ti = dateutil.parser.parse(f['modified'])

        print(ti.strftime("%Y-%m-%d %H:%M:%S"), end="  ")

        if f['size'] is None:
            print(f"{'':12}", end="  ")
        else:
            print(f"{f['size']:>12}", end="  ")

        print(f['name'])

@cli.command()
@click.argument("path",default="")
def mkdir(path):
    # global theclient

    if theclient is None:
        print("error: not connected")
        return

    theclient.mkdir(path)

@cli.command()
@click.argument('txt', nargs=-1)
def echo(txt):
    print(' '.join(txt))

@cli.command()
@click.argument("localfile")
def up(localfile):

    for u in click.get_current_context().obj.upscripts:

        for i in ['pattern', 'script']:
            if i not in u:
                print(f"error: upload script: required parameter {i} not found")

        m = re.match(u['pattern'],localfile)
        if m:
            for line in u['script']:
                run_textcommand(m.expand(line).replace('@',localfile))
            return

    print(f"no matching upload script for {localfile}")


@cli.command()
@click.argument('localfiles', nargs=-1)
@click.option('-n', '--dry-run', is_flag=True)
def mput(localfiles, dry_run):

    for f in localfiles:
        _put(f,None, dry_run)


@cli.command()
@click.argument("localfile")
@click.argument("remotefile", required=False)
@click.option('-n', '--dry-run', is_flag=True)
def put(localfile, remotefile, dry_run=False):
    # print(localfile, "->", remotefile)

    _put(localfile,remotefile,dry_run)

def _put(localfile, remotefile=None, dry_run=False):
    cfg = click.get_current_context().obj

    #### Check local file
    try:
        finfo = { 'stat': os.stat(localfile) }
    except FileNotFoundError as ex:
        print (f'Local file "{localfile}" does not exist')
        return

    finfo['mtime'] = datetime.fromtimestamp(finfo['stat'].st_mtime, dateutil.tz.gettz())

    if cfg.verbosity >= 2 :
        print ("Local file:")
        print ("  File name:", localfile)
        print ("  File size:", finfo['stat'].st_size)
        print ("  Modified: ", finfo['mtime'])
        # print ("  Modified: ", finfo['mtime'], finfo['mtime'].tzinfo)

    if remotefile is None:
        rpath = localfile

        for fp in cfg.filepatterns:
            m = re.match(fp['match'], rpath)
            if m:
                template = jinja2.Template(fp['dest'])
                rpath = template.render(**m.groupdict(), **cfg.variables)

    else:
        rpath = remotefile

    global theclient

    # pprint(rpath)
    # pprint(theclient.info(rpath))

    # retrieve info about remote file
    rinfo = None
    try:
        rinfo = theclient.info(rpath)

        # rinfo['mtime'] = datetime.strptime(rinfo['modified'], '%a, %d %b %Y %H:%M:%S %Z')
        rinfo['mtime'] = dateutil.parser.parse(rinfo['modified'])

        if cfg.verbosity >= 2 :
            print ("Remote file:")
            print ("  Full path:", rpath)
            print ("  File name:", rinfo['name'])
            print ("  File size:", rinfo['size'])
            # print ("  Modified: ", rinfo['mtime'], rinfo['mtime'].tzinfo)
            print ("  Modified: ", rinfo['mtime'])

    except webdav3.exceptions.RemoteResourceNotFound as ex:
        print ("Remote file does not exist")
        pass

    # print(localfile, "->", rpath)

    if rinfo is not None and rinfo['mtime'] > finfo['mtime']:
        print (f'Remote file is newer than local file {localfile} - skip upload')

    elif dry_run:
        click.echo(f'+++DRYRUN+++ Uploading {click.style(localfile, fg="blue")} to {click.style(rpath, fg="blue")}')

    else:
        click.echo(f'Uploading {click.style(localfile, fg="blue")} to {click.style(rpath, fg="blue")}')
        theclient.upload_sync(remote_path=rpath, local_path=localfile)


@cli.command()
@click.pass_context
def cfg(ctx):
    cf = ctx.obj

    print("Profiles:")
    pprint(cf.profiles)
    print()

    print("Upload scripts:")
    pprint(cf.upscripts)
    print()

if __name__ == '__main__':
    cli(obj={})


# import argparse
# import yaml
# import re
# import os
# from datetime import datetime
# import dateutil
# import readline

# # ---------------------------------------------------------------------------
# # Parse command line arguments and read configuration file
#
# parser = argparse.ArgumentParser(description='Upload file to WebDAV server.')
# parser.add_argument('--cfgfile', nargs=1, type=argparse.FileType('r'),
#                     help="Configuration file with DAV site information")
# parser.add_argument('filename', nargs='+', type=str,
#                     help="File to be uploaded to Vula")
#
# args = parser.parse_args()
#
# if 'cfgfile' not in args or args.cfgfile is None:
#     parser.print_help()
#
# if len(args.cfgfile) != 1 :
#     print("exactly ONE configuration file is expected")
#     exit(1)
#
# try:
#     cfg = yaml.safe_load(args.cfgfile[0])
# except yaml.YAMLError as exc:
#     print(exc)
#
# print (args)
# # print (cfg)
# # exit(1)
#
# # ---------------------------------------------------------------------------
# # Connect to WebDAV server
#
# # set default options from config file
# options = {
#  'webdav_hostname': cfg['vula']['site'],
#  'webdav_login':    cfg['vula']['username'],
#  'webdav_password': cfg['vula']['password']
# }
#
# # look up password in keyring if requested
# m = re.search('\+\+\+KEYRING\+\+\+(.+)\+\+\+(.*)', options['webdav_password'])
# if m:
#     if m.group(2)=="":
#         user = options['webdav_login']
#     else:
#         user = m.group(2)
#
#     options['webdav_password'] = keyring.get_password(m.group(1), user)
#
# # connect
# client = Client(options)
#
# # ---------------------------------------------------------------------------
# # Upload the file
#
# for i in args.filename:
#
#     #### Check local file
#     try:
#         finfo = { 'stat': os.stat(i) }
#     except FileNotFoundError as ex:
#         print (b'Local file "{i}" does not exist')
#         continue
#
#     finfo['mtime'] = datetime.fromtimestamp(finfo['stat'].st_mtime, dateutil.tz.gettz())
#
#     if True:
#         print ("Local file:")
#         print ("  File name:", i)
#         print ("  File size:", finfo['stat'].st_size)
#         print ("  Modified: ", finfo['mtime'])
#         # print ("  Modified: ", finfo['mtime'], finfo['mtime'].tzinfo)
#
#
#     #### Determine remote path
#     rpath = i
#
#
#     for pattern,repl in cfg['vula']['path'].items():
#         rpath = re.sub(pattern,repl,rpath)
#         # print (pattern,rpath)
#
#     if rpath==i:
#         print("File '%s' not found in configuration file" % i)
#         continue
#
#     # make sure we have variables for the following commands
#     if 'variables' not in cfg:
#         cfg['variables'] = {}
#
#     if 'variables' not in cfg['vula']:
#         cfg['vula']['variables'] = {}
#
#
#     # print(cfg)
#
#     # replace any convenience variables in the file names
#     vardict = {**cfg['variables'], **cfg['vula']['variables']}
#     # print(vardict)
#     rpath = rpath.format(**vardict)
#
#
#     # retrieve info about remote file
#     rinfo = None
#     try:
#         rinfo = client.info(rpath)
#
#         # rinfo['mtime'] = datetime.strptime(rinfo['modified'], '%a, %d %b %Y %H:%M:%S %Z')
#         rinfo['mtime'] = dateutil.parser.parse(rinfo['modified'])
#
#         if True:
#             print ("Remote file:")
#             print ("  Full path:", rpath)
#             print ("  File name:", rinfo['name'])
#             print ("  File size:", rinfo['size'])
#             # print ("  Modified: ", rinfo['mtime'], rinfo['mtime'].tzinfo)
#             print ("  Modified: ", rinfo['mtime'])
#
#     except webdav3.exceptions.RemoteResourceNotFound as ex:
#         # print ("Remote file does not exist")
#         pass
#
#
#     if rinfo is not None and rinfo['mtime'] > finfo['mtime']:
#         print (f'Remote file is newer than local file {i} - skip upload')
#
#     else:
#         print (f'Uploading "{i}" to "{rpath}"')
#         client.upload_sync(remote_path=rpath, local_path=i)
#         # print(client.info(rpath))
#
#     print()
