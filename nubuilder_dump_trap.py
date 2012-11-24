#!/usr/bin/env python

"""
Dump nuBuilder debug log (zzsys_trap).

Some SQL queries appear to be hex encoded.  This tool decodes those
queries (but leaves unencoded queries alone) and formats the log for
easier reading.
"""

import MySQLdb
import optparse
import os
import re
import sys

# Default root directory of nuBuilder installation.
# Override with --root option.
if os.name == "nt":
    DEFAULT_ROOT = r"C:\Program Files\nuBuilder"  # need suggestion
else:
    DEFAULT_ROOT = "/var/www/nubuilder"

def hexstr(string):
    """Decode a string of hex char pairs."""
    decoded = "".join(
        chr(int(c1 + c2, 16))
        for c1, c2 in zip(string[0::2], string[1::2])
    )
    return decoded


def decode_tra_message(message):
    """Decode and format a tra_message."""
    indent = "  "
    parts = re.split(
        "('(?:[0-9A-F][0-9A-F]){20,}')",
        message,
        flags=re.IGNORECASE
    )
    new_parts = list()
    for num, part in enumerate(parts):
        if num % 2 == 1:
            part = "'%s'" % hexstr(part[1:-1])
        else:
            part = part.replace("; ", "\n" + indent)
        new_parts.append(part)
    return indent + "".join(new_parts)


def main():
    """main"""
    option_parser = optparse.OptionParser(
        usage="usage: %prog [options] APPLICATION\n" +
            "  Dump nuBuilder debug log (zzsys_trap)."
    )
    option_parser.add_option(
        "--root",
        dest="root",
        metavar="DIR",
        default=DEFAULT_ROOT,
        help="root dir of nuBuilder installation (default=%default)"
    )
    option_parser.add_option(
        "--purge",
        action="store_true",
        dest="purge",
        default=False,
        help="purge all records from zzsys_trap"
    )

    (options, args) = option_parser.parse_args()
    if len(args) != 1:
        option_parser.error("no application specified")

    config_filename = os.path.join(options.root, "db", args[0], "config.php")
    if not os.path.exists(config_filename):
        option_parser.error("Config file '%s' not found." % config_filename)

    config_vars = dict()
    with open(config_filename) as config_file:
        for line in config_file:
            match = re.search(
                r" *(\$[a-z0-9_]+) *= *\"(.+)\";",
                line,
                flags=re.IGNORECASE
            )
            if match:
                config_vars[match.group(1)] = match.group(2)

    connection = None
    try:
        connection = MySQLdb.connect(
            config_vars["$DBHost"],
            config_vars["$DBUser"],
            config_vars["$DBPassword"],
            config_vars["$DBName"]
        )

        cursor = connection.cursor()
        table = "%s.zzsys_trap" % config_vars["$DBName"]
        if options.purge:
            cursor.execute("DELETE FROM %s" % table)
        else:
            cursor.execute(
                "SELECT zzsys_trap_id, sys_added, tra_message FROM %s" %
                table
            )

        for zzsys_trap_id, sys_added, tra_message in cursor.fetchall():
            print "%s, %i" % (sys_added, zzsys_trap_id)
            print decode_tra_message(tra_message)

    except MySQLdb.Error, ex:
        print "Error %d: %s" % (ex.args[0], ex.args[1])
        sys.exit(1)

    finally:
        if connection:
            connection.close()


if __name__ == "__main__":
    sys.exit(main())
