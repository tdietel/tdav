
TDAV - Tiny WebDAV Client
=========================

This package implements a frontend for webdavclient3.

The aim is to create the best command-line WebDAV client ever. The concept is
inspired by [cadaver], which replicates the user interface of early FTP clients
(like ftp or ncftp) for WebDAV. However, cadaver is very basic and lacks a few
features that I am looking for, mainly in the area of automation. Also the
tab completion seems to have issues with filenames that contain spaces.

After automating some tasks with Python and the [webdavclient3] module, I
decided to package my hacks as a more versatile command-line tool.

References
----------

[cadaver]: http://www.webdav.org/cadaver/
[webdavclient3]: https://pypi.org/project/webdavclient3/
