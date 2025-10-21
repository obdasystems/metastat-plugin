Metastat Eddy Plugin
=====================

This repository contains the Eddy plugin for Metastat,
a metadata repository for Istat.

Installing from the repository
------------------------------

This plugin is still a work-in-progress, to install the plugin from the git repository:

* Clone the repository:

```bash
git clone https://github.com/obdasystems/metastat-plugin
```

* Create a symlink from the Eddy plugin directory to the project folder:
 
```bash
ln -s $EDDY_PLUGIN_DIR/metastat-plugin $PROJECT_FOLDER
```

or for Windows:
```shell
mklink /d '<EDDY_PLUGIN_DIR>\metastat-plugin' '<PROJECT_FOLDER>'
```

then Eddy will find it when scanning for plugins.

The plugin folder differs from OS to OS. The following are the usual locations:

* *Linux*: `~/.local/share/eddy/plugins/`
* *macOS*: `~/Library/Application Support/eddy/plugins/`
* *Windows*: `%USERPROFILE%/AppData/Roaming/eddy/plugins/`
