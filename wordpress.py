from os import listdir, popen
import os.path
import re
import tarfile


# ----------------
# helper functions
# ----------------

# simple os.path wrapper
def is_file(path, f):
    return os.path.isfile(os.path.join(path, f))


def is_folder(path, f):
    return os.path.isdir(os.path.join(path, f))


# simple filter for folders and files
def list_folders(path):
    if not os.path.exists(path):
        return []
    return [f for f in listdir(path) if is_folder(path, f)]


def list_files(path):
    if not os.path.exists(path):
        return []
    return [f for f in listdir(path) if is_file(path, f)]


class Wordpress:
    """
    This class represents a single wordpress installation, which contains all information
    like installed plugins, version numbers and database credentials.
    It is initialized by providing the root folder of the wordpress installation.
    """

    # a very simple method to check if the provided folder is a wordpress installation,
    # by checking for the existence of a wp-config.php file and the wp-admin
    # folder
    @staticmethod
    def is_wordpress_folder(folder):
        files = list_files(folder)
        folders = list_folders(folder)
        return "wp-config.php" in files and "wp-admin" in folders

    def __init__(self, path):
        """
        constructor takes path to the wordpress root folder
        """

        if not Wordpress.is_wordpress_folder(path):
            raise Execption('No Wordpress Instance')
            return

        # set path
        self.path = path
        self.name = os.path.basename(os.path.abspath(path))

        # set up empty values dict and plugins list
        self.values = {}
        self.plugins = []

        # extract actual information
        self.extractInformation()

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def extractInformation(self):
        """
        starts the file parsing for the information
        """
        self.parseVersionFile()
        self.parseConfigFile()
        self.parsePluginsInFolder('wp-content/plugins')
        # self.parseThemes()

    def getVariableValue(self, var_name, line):
        """
        parses a single line for a variable assignment
        parameters:
            var_name: the name of the variable which value should be extracted
            line: string, in which the variable is assigned
        """

        # simple regex, which searches for all occurences which look like
        #   var_name = value ;
        matches = re.findall(
            r"^\s*" + re.escape(var_name) + r"\s*=\s*.*;", line)

        # if no matches are found, return an dict, with valid set to false
        if len(matches) == 0:
            return {"valid": False}

        # take only the first occurence of our matched pattern
        # TODO: this can lead to problems if the variable is assigned more than
        # once on the same line (should normally not be the case in wordpress
        # source)
        m = matches[0]

        # extract the value of the variable via regex
        value = re.search(r"=.*;", m)
        value = value.group(0)
        value = value[1: len(value) - 1].strip()

        # if value is string remove ' and "
        value = re.sub(r"^[\'\"]", '', value)
        value = re.sub(r"[\'\"]$", '', value)
        return {"valid": True, "value": value}

    def getConstantValue(self, var_name, line, is_string=True):
        """
        similar to the getVariableValue() function, but extracts the value of a
        constant in php, which is defined as follows
            define('var_name', value);
        """

        # regex search for the define(var_name, ..); pattern
        matches = re.findall(
            r"define\s*\(\s*[\"\']" + re.escape(var_name) + r"[\"\']\s*,.*\)\s*;", line)

        # if no matches are found return invalid match
        if len(matches) == 0:
            return {"valid": False}
        pass

        # only consider first match (should not be a problem, since constants are
        # not defined more than once)
        m = matches[0]

        # extract value via regex
        value = re.search(r",.*\)", m).group(0)
        value = value.strip()[1:len(value) - 1].strip()
        value = re.sub(r"^[\'\"]", '', value)
        value = re.sub(r"[\'\"]$", '', value)
        return {"valid": True, "value": value}

    def parseVersionFile(self):
        """
        parse the version.php file of wordpress, in order to extract the information
        about the wordpress version, the wordpress database version, the required
        php and mysql version, as well as the installed wp_locale_package version
        """

        # assuming a standard path and filename
        f = 'wp-includes/version.php'
        constants = []
        variables = [
            '$wp_version',
            '$wp_db_version',
            '$required_php_version',
            '$required_mysql_version',
            '$wp_locale_package'
        ]

        # call general parseFile() function
        self.parseFile(f, variables, constants)

    def parseConfigFile(self):
        """
        parse the wp-config.php file, in order to extract the values for the
        database credentials, and the value of the WP_DEBUG flag
        """

        # assume standard wp-config.php filename
        f = 'wp-config.php'
        variables = []
        constants = [
            'DB_NAME',
            'DB_USER',
            'DB_PASSWORD',
            'DB_HOST',
            'WP_DEBUG'
        ]

        # call general parseFile() function
        self.parseFile(f, variables, constants)

    def parseFile(self, file_path, variables=[], constants=[]):
        """
        This is a gernal function, which parses the provided file in file_path
        line by line, and trys to extract the values for the variable names provided
        in variables, and the values for the constants provided in constants
        """

        # try to open the file
        # TODO: maybe raise error or return false, in order to indicate failure
        # :/
        try:
            f = open(os.path.join(self.path, file_path))
        except:
            return

        # go through the file line by line
        for line in f:

            # remove line ending
            line = line[:-1]

            # try to find the value for every constant name provided in
            # constants parameter
            for c in constants:
                tmp = self.getConstantValue(c, line)
                if tmp['valid']:
                    self.values[c] = tmp['value']

        # return to the beginning of the file
        f.seek(0)

        # same as before, but for variables rather than constants
        for line in f:
            line = line[:-1]
            for v in variables:
                tmp = self.getVariableValue(v, line)
                if tmp['valid']:
                    self.values[v] = tmp['value']

        # close the file
        f.close()

    def parsePluginsInFolder(self, folder_path, remaining_depth=1):
        """
        Parse all files and folders in folder_path recursively (default depth 1)
        and look for plugins files. Normally folder_path is 'wp-content/plugins'
        under the root folder
        """

        # list all files in the folder_path
        base_path = os.path.join(self.path, folder_path)
        files = list_files(base_path)

        # filter files for php ending
        files = [f for f in files if f.split(".")[-1] == "php"]

        # go through files
        for f in files:
            try:
                i = open(os.path.join(base_path, f))
                t = i.read()
                i.close()
            except:
                continue

            # test the contents of the file for indications of a wordpress plugins
            # using the isPluginFile() function
            if Plugin.isPluginFile(t):
                self.plugins.append(Plugin(t, os.path.join(base_path, f)))

        # if we have remaining depth, go down one level
        if remaining_depth > 0:
            folders = list_folders(base_path)

            # recursively parse subfolders
            for f in folders:
                self.parsePluginsInFolder(os.path.join(
                    folder_path, f), remaining_depth - 1)

    def dumpSQL(self, filename="mysqldump.sql"):
        """
        This function uses os.popen to call mysqldump in order to create a SQL dump
        of the the MYSQL database. It uses the database credentials which are extracted
        by parsing the 'wp-config.php' for the corresponding constants. The responding
        file is named with the filename parameter and will be located in the
        wordpress root directory.
        """

        # helper variables for shorter variables names
        db = self.values['DB_NAME']
        user = self.values['DB_USER']
        pw = self.values['DB_PASSWORD']
        host = self.values['DB_HOST']
        savefile = os.path.join(self.path, filename)

        # the command to execute by popen
        cmd = 'mysqldump -u %s -p%s -h %s %s > %s' % (
            user, pw, host, db, savefile)
        popen(cmd)

    def compress(self, file_path=''):
        """
        Create an .tar.gz file of the whole wordpress instance.
        Helpful for backups or migration of into different locations.
        The resulting filename is <rootfolder_name>.tar.gz and is located one level
        up off the wordpress root folder, or in the location provided by file_path
        """

        # generate file path for the resulting .tar.gz
        file_path = os.path.abspath(os.path.join(self.path, '..', self.name + '.tar.gz')
                                    ) if file_path == '' else os.path.join(file_path, self.name + '.tar.gz')

        # open the tar file, and add all files and directories to it
        tar = tarfile.open(file_path, "w:gz")
        for f in os.listdir(self.path):
            absolute_path = os.path.join(self.path, f)
            tar.add(absolute_path, os.path.relpath(absolute_path, self.path))

        # close the tar file
        tar.close()

    def prettyPrint(self):
        """
        Simple helper function to pretty print the information about the
        wordpress instance.
        """

        print "----------------------------------------------------------"
        print "Allgemein:"
        print ""
        print "Name: " + self.name
        print "Pfad: " + self.path
        print "Debug?: " + self.values['WP_DEBUG']
        print "----------------------------------------------------------"
        print "Datenbank:"
        print ""
        print "DB-Name: " + self.values['DB_NAME']
        print "DB-User: " + self.values['DB_USER']
        print "DB-PW: " + self.values['DB_PASSWORD']
        print "DB-Host: " + self.values['DB_HOST']
        print "----------------------------------------------------------"
        print "Plugins:"
        print ""

        for p in self.plugins:
            print "\t" + p.info['name'] + ":"
            print "\t" + (len(p.info['name']) + 1) * "^"
            print "\tHaupt-Datei: " + p.main_file

            if "version" in p.info.keys():
                print "\tVersion: " + p.info['version']

            if "uri" in p.info.keys():
                print "\tURL: " + p.info['uri']

            if "description" in p.info.keys():
                print "\tBeschreibung: " + p.info['description']

            print "\n\n"


class Plugin:
    """
    This class represents a single plugin installed in the wordpress instance.
    It contains information about the Plugin name, the Author, the version, etc.
    """

    @staticmethod
    def isPluginFile(text):
        """
        Main function to decide if the provided content of a file is the main
        plugin file. For now only searches the provided text for the following
        pattern on any line:

        <?php
            * Plugin Name: ...
        """

        # using re.DOTALL to let . also match newlines
        matches = re.findall(
            r"<\?php.*/\*+.*Plugin\s+Name\s*:\s*.*\n", text, re.DOTALL)
        return len(matches) > 0

    def __init__(self, text, main_file):
        """
        Simple construtor, which takes the content of the file (text),
        as well as the name of the file (main_file), and starts the information
        extraction with extractInformation().
        """
        self.main_file = main_file
        self.info = {}
        self.extractInformation(text)

    def __str__(self):
        return self.info['name']

    def __repr__(self):
        return self.info['name']

    def extractInformation(self, text):
        """
        Main function, which extracts the information from the php comment header
        which wordpress uses.
        """

        # dict follows the structure: 'variable_name': 'key_name in self.info'
        variables = {
            'Plugin Name': 'name',
            'Plugin URI': 'uri',
            'Description': 'description',
            'Version': 'version',
            'Author': 'author',
            'Author URI': 'author_uri'
        }

        # try to extract all values for the variable names given in 'variables'
        for v in variables:
            tmp = self.extractVariableValue(v, text)
            if tmp['valid']:
                self.info[variables[v]] = tmp['value']

    def extractVariableValue(self, var_name, text):
        """
        Another information extraction function, which parses the php
        comment header style, which wordpress uses to store information about
        plugins. Trys to find the pattern

            var_name: <some_value>

        in the string 'text'.
        """

        # match the regular expression, and return invalid match if nothing is
        # found
        matches = re.findall(re.escape(var_name) + r"\s*:.*\n", text)
        if len(matches) == 0:
            return {'valid': False}

        # use only the firt occurence
        m = matches[0]

        # regex match with groups
        value = re.search(r":.*\n", m)
        value = value.group(0)

        # return valid match, with correspoding value
        return {"valid": True, "value": value[1:len(value) - 1].strip()}


# TODO: implement and provide some kind of documentation.
#       should basically the as for plugins.
class Theme:

    def __init__(self, style, path):
        self.path = path
        self.folder = os.path.basename(path)
        extractInfo(style)

    def extractInfo(text):
        variables = {}
        pass
