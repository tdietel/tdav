#!/usr/bin/env python3

from webdav3.client import Client
import webdav3.exceptions

# import sys
import click

import re
import os
import getpass
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
def shell(verbose=False):

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

    m = re.search('(https?://[a-zA-Z\.]+)', url)
    if m:
        server = m.group(1)
    else:
        server = None

    if options['webdav_password'] is None and server is not None:
        options['webdav_password'] = keyring.get_password(server, username)

    if options['webdav_password'] is None:
        options['webdav_password'] = getpass.getpass("Enter password: ")

        if server is not None:
            save = input("Save password in key chain (yes/NO)? ")
            if save == 'yes':
                keyring.set_password(server, username, options['webdav_password'])

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
