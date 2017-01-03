# (offline) WordPress discovery using python

This library provides a WordPress class for python, which can be used
to extract information about a WordPress instance found in a specific folder.
It parses common WordPress config files to extract information about the
WordPress Version, the DB credentials as well as the installed Plugins.

Furthermore it can automatically create a MySQL dump of the used database, and
compress the WordPress instance into a .tar.gz file.
The original intention was to implemented as quick solution to migrate a large
amount of WordPress installations from one server to another.

See the ```discover_folders.py``` file for quick introduction to find all WordPress
installations inside a specified folder. Can be used as follows:

```bash
python discover_folders.py /path/to/the/root/folder
```

The main functions are:

```python
if Wordpress.is_wordpress_folder(folder_path):
  wp = Wordpress(folder_path)
```

to test if ```folder_path``` is a WordPress installation and extract all
information on construction. See the (mostly commented) source for more
information.
