:author: Gustavo Rezende <nsigustavo@gmail.com>

Gedit Pyflakes Plugins
======================

Geditpyflakes plugin allow users to run Pyflakes inside Gedit and show found pyflakes's error messages.


Get and install
===============

You can download geditpyflakes::

    $ wget http://github.com/nsigustavo/geditpyflakes/tarball/master
    $ tar -xzvf nsigustavo-geditpyflakes*.tar.gz

Put the geditpyflakes.gedit-plugin file and the whole content directory into ~/.gnome2/gedit/plugins::

    $ cd nsigustavo-geditpyflakes*
    $ mkdir ~/.gnome2/gedit/plugins
    $ cp -rf * ~/.gnome2/gedit/plugins

Install dependences: pynotify and pyflakes

In gedit main menu go to: Edit -> Preferences

In Preferences dialog go to Plugins tab

Find 'Gedit Pyflakes Plugins' in plugin list and check it



Getting involved !
==================

Gedit Pyflakes Plugins is development may be viewed and followed on github::

  http://github.com/nsigustavo/geditpyflakes


Retrieve the source code using git::

    $ git clone git://github.com/nsigustavo/geditpyflakes.git

