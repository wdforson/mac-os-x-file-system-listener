#! /usr/bin/python2.7

from argparse import ArgumentParser
import hashlib
import json
import os

def compute_hashes_for_all_source_files(source_tree_root, dirpath_filename_predicate):
  """ Compute the md5 hash for every file under the specified source tree that is accepted
  by dirpath_filename_predicate, and return a dictionary that maps filepaths to md5 hashes. """

  filepaths_to_hashes = {}
  for dirpath, dirnames, filenames in os.walk(source_tree_root):
    for filename in filenames:
      # ignore files that are rejected by dirpath_filename_predicate
      if dirpath_filename_predicate(dirpath, filename):
        filepath = os.path.join(os.path.abspath(dirpath), filename)
        filepaths_to_hashes[filepath] = hash_file(filepath)

  return filepaths_to_hashes

def hash_file(filepath):
  """ Compute the md5 has for the specified file and return it as a hex string. """

  h = hashlib.md5()
  with open(filepath, 'rb') as f:
    for chunk in iter(lambda: f.read(8192), b''):
      h.update(chunk)

  return h.hexdigest()

def load_potentially_empty_json_object(filepath):
  """ If the given filepath refers to an existing filesystem entity, attempt to load it as JSON;
  otherwise, just return an empty dictionary. """

  if not os.path.exists(filepath):
    return {}

  # NOTE: there are some error cases here that will case an IOException to be thrown
  #       (e.g. filepath refers to a directory or a non-JSON file)
  with open(filepath, 'rb') as f:
    return json.load(f)

DEFAULT_METADATA_FILENAME = '.do_cmd_if_source_has_changed_py_metadata.json'
def main():
  args = parse_args()
  metadata_filepath = args.metadata_filepath or os.path.join(args.source_tree_root, DEFAULT_METADATA_FILENAME)
  directories_to_ignore = set(os.path.abspath(d) for d in args.directories_to_ignore)

  # load the most recently recorded filepath->md5 hash mapping
  prev_mapping = load_potentially_empty_json_object(metadata_filepath)

  # skip over files that match the user-specified prefixes/suffixes, as well as the
  # script's own metadata file
  def dirpath_filename_predicate(dirpath, filename):
    return not (filter(lambda p: filename.startswith(p), args.prefixes_to_ignore) or
                filter(lambda s: filename.endswith(s), args.suffixes_to_ignore) or
                filter(lambda d: os.path.abspath(dirpath).startswith(d), directories_to_ignore) or
                os.path.join(dirpath, filename) == metadata_filepath)

  # re-compute an md5 hash for all non-ignorable files under the relevant source tree
  cur_mapping = compute_hashes_for_all_source_files(args.source_tree_root,
      dirpath_filename_predicate)

  # IFF any of the md5 hashes have changed since the last time we checked, write the updated
  # mapping to the metadata filepath, exec the user-specified script with the given args
  if prev_mapping != cur_mapping:
    with open(metadata_filepath, 'w') as f:
      json.dump(cur_mapping, f, indent=2)
    print 'changes detected. updated {}, about to run: {} {}'.format(
        metadata_filepath, args.executable, ' '.join(args.args))
    os.execvp(args.executable, [args.executable] + args.args)

def parse_args():
  parser = ArgumentParser()
  parser.add_argument('--source-tree-root', '-r', required=True,
      help='root directory of the source tree that should be scanned for changes')
  parser.add_argument('--executable', '-e', required=True,
      help='executable to run whenever source changes are detected')

  # FIXME: what is the best way to pass these args in on the command line?
  #        problem: suppose 'ls' is specified as the executable, and '-r' is specified as one of its arguments
  #                 ...argparse will treat that '-r' as a '--source-tree-root' argument
  #        one option would be [arg.lstrip() for arg in args], which would allow a user to pass in ' -r',
  #        which argparse will NOT recognize as an argument.
  #        BUT, wouldn't this produce non-obvious behavior for anyone who is not trying to specifically escape
  #        an argument value that is known to collide with a flag name? (e.g. someone who simply wants to pass
  #        in a string such as '  foo  ', which happens to contain leading whitespace)
  parser.add_argument('--args', '-a', nargs='*', default=[],
      help='arguments to pass to the specified executable that is run whenever source changes are detected')

  parser.add_argument('--prefixes-to-ignore', nargs='*', default=['.'],
      help='filenames with the specified prefix will be ignored when scanning for source changes')
  parser.add_argument('--suffixes-to-ignore', nargs='*', default=[],
      help='filenames with the specified suffix will be ignored when scanning for source changes')
  parser.add_argument('--directories-to-ignore', nargs='*', default=[],
      help='paths (relative or absolute) to directories to ignore when scanning for source changes')
  parser.add_argument('--metadata-filepath', '-m',
      help='filepath to use to store metadata used by this script. defaults to $(--source-tree-root)/{}'.format(
        DEFAULT_METADATA_FILENAME))

  return parser.parse_args()

if __name__ == '__main__':
  main()
