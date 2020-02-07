# https://github.com/Valloric/ycmd/blob/master/cpp/ycm/.ycm_extra_conf.py
# https://jonasdevlieghere.com/a-better-youcompleteme-config/
# https://github.com/arximboldi/dotfiles/blob/master/emacs/.ycm_extra_conf.py

import os
import os.path
from glob import glob
import logging
import ycm_core
import difflib

# flags used when no compilation_db is found
BASE_FLAGS = [
    '-std=c++1z',
    '-x', 'c++',
]

# flags are always added
EXTRA_FLAGS = [
    '-Wall',
    '-Wextra',
    '-Weverything',
    '-Wno-c++98-compat',
    '-Wno-c++98-compat-pedantic',
    # '-Wshadow',
    # '-Werror',
    # '-Wc++98-compat',
    # '-Wno-long-long',
    # '-Wno-variadic-macros',
    # '-fexceptions',
    # '-DNDEBUG',
]

SOURCE_EXTENSIONS = [
    '.cpp',
    '.cxx',
    '.cc',
    '.c',
    '.m',
    '.mm'
]


def generate_qt_flags():
    flags = ['-isystem', '/usr/include/qt/']
    for p in glob('/usr/include/qt/*/'):
        flags += ['-isystem', p]
    return flags


def similarity_ratio(s, t):
    return difflib.SequenceMatcher(a=s.lower(), b=t.lower()).ratio()


def find_similar_file_in_database(dbpath, filename):
    import json
    logging.info("Trying to find some file close to: " + filename)
    db = json.load(open(dbpath+ "/compile_commands.json"))

    best_filename = ''
    best_ratio = 0
    for entry in db:
        entry_filename = os.path.normpath(os.path.join(entry["directory"],
                                                       entry["file"]))

        if filename == entry_filename:
            logging.info("Found exact match: " + entry_filename)
            return entry_filename

        basename = os.path.splitext(filename)[0]
        for extension in SOURCE_EXTENSIONS:
            replacement_file = basename + extension
            if entry_filename == replacement_file:
                logging.info("Found match: " + replacement_file)
                return entry_filename

        ratio = similarity_ratio(str(filename), str(entry_filename))
        if ratio > best_ratio:
            best_filename = entry_filename
            best_ratio = ratio

    logging.info("Found closest match: " + best_filename)
    return best_filename


def find_nearest_compilation_database(root='.'):
    dirs = glob(root + '/*/compile_commands.json', recursive=True)

    if len(dirs) == 1:
        return dirs[0]
    elif len(dirs) > 1:
        logging.info("Multiple compilation databases found!")
        logging.info(dirs)
        dirs.sort(key=lambda x: os.stat(x).st_mtime, reverse=True)
        logging.info("Selecting newest: %s" % (dirs[0]))
        return dirs[0]

    parent = os.path.dirname(os.path.abspath(root))
    if parent == root:
        raise RuntimeError("Could not find compile_commands.json")
    return find_nearest_compilation_database(parent)


def find_nearest(path, target):
    candidates = [
        os.path.join(path, target),
        os.path.join(path, 'build', target),
        os.path.join(path, 'output', target),
    ]
    for candidate in candidates:
        if os.path.isfile(candidate) or os.path.isdir(candidate):
            logging.info("Found nearest " + target + " at " + candidate)
            return candidate
    parent = os.path.dirname(os.path.abspath(path))
    if parent == path:
        raise RuntimeError("Could not find " + target)
    return find_nearest(parent, target)


def flags_for_include(root):
    try:
        include_path = find_nearest(root, 'include')
        flags = []
        for dirroot, dirnames, filenames in os.walk(include_path):
            for dir_path in dirnames:
                real_path = os.path.join(dirroot, dir_path)
                flags = flags + ["-I" + real_path]
        return flags
    except Exception as err:
        logging.info("Error while looking flags for includes in root: " + root)
        logging.error(err)
        return None


def get_compilation_database(root):
    try:
        compilation_db_path = find_nearest_compilation_database(root)
        compilation_db_dir = os.path.dirname(compilation_db_path)
        logging.info("Set compilation database directory to " + compilation_db_dir)
        db = ycm_core.CompilationDatabase(compilation_db_dir)
        if db is None:
            logging.info("Compilation database file found but unable to load")
            return None
        return db
    except Exception as err:
        logging.info("Error while trying to find compilation database: " + root)
        logging.error(err)
        return None


def Settings(**kwargs):
    if kwargs['language'] != 'cfamily':
        return {}

    print(kwargs)
    client_data = kwargs['client_data']
    root = client_data.get('getcwd()', '.')
    filename = kwargs['filename']

    database = get_compilation_database(root)
    if database:
        filename = find_similar_file_in_database(database.database_directory,
                filename)
        compilation_info = database.GetCompilationInfoForFile(filename)
        print(compilation_info)
        if not compilation_info.compiler_flags_:
            return {}  #TODO use default flags
        final_flags = list(compilation_info.compiler_flags_)
        include_path_relative_to_dir = compilation_info.compiler_working_dir_
    else:
        final_flags = BASE_FLAGS
        include_flags = flags_for_include(root)
        if include_flags:
            final_flags += include_flags
        final_flags += generate_qt_flags()
        final_flags += ['-I', root,
                        '-I', root + '/include']
        include_path_relative_to_dir = root

    return {
        'flags': final_flags + EXTRA_FLAGS,
        'include_paths_relative_to_dir': include_path_relative_to_dir,
        'override_filename': filename,
        'do_cache': True
    }
