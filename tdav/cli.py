#!/usr/bin/env python3

from webdav3.client import Client
import webdav3.exceptions

# import sys
import click

import re
import keyring
import readline
import dateutil

theclient = None

# ==========================================================================
# The default entry point can either call a subcommand directly if specified
# on the command line, or starts an interactive shell otherwise.

@click.group(invoke_without_command=True, chain=True)
@click.pass_context
def cli(ctx):
    if ctx.invoked_subcommand is None:
        cmd = cli.get_command(ctx,'shell')
        # cmd.parse_args(ctx,sys.argv[1:])
        cmd.invoke(ctx)


@cli.command()
@click.pass_context
def shell(ctx):

    while True:
        line = input("> ")

        try:
            run_textcommand(ctx,line)

        except click.UsageError as ex:
            click.echo(click.style(f"ERROR: {ex}", fg='red'))


def run_textcommand(ctx,line):

    tokens = line.split(' ')
    cmd = cli.get_command(ctx,tokens[0])
    if cmd is None:
        raise click.UsageError(f"unknown command '{tokens[0]}'", ctx)

    cmd.parse_args(ctx,tokens[1:])
    cmd.invoke(ctx)


@cli.command()
@click.argument("url")
@click.option("--username")
@click.option("--password", default=None)
def connect(url,username,password):

    options = {
        'webdav_hostname': url,
        'webdav_login': username,
        'webdav_password': password
    }

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
@click.argument("localfile")
def put(localfile,remotefile=None):
    print(localfile, "->", remotefile)


if __name__ == '__main__':
    cli()


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
