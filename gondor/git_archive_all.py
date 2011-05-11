#! /usr/bin/python

from os import path, chdir
from subprocess import Popen, PIPE
from optparse import OptionParser
from sys import argv, stdout
from fnmatch import fnmatch

def archive_git(output_file,format='tar',repo_root='.', verbose=False):

    def git_files(repo_root=repo_root,exclude=True,verbose=False,prefix=''):

        excludes = []

        for filepath in Popen('cd %s && git ls-files --cached --full-name --no-empty-directory'%(repo_root,), shell=True, stdout=PIPE).stdout.read().splitlines():
            filename = path.join(filepath,prefix)
            fullpath = path.join(repo_root,filepath)


            # right now every time we find a .gitattributes, we
            # overwrite the previous patterns. might be nice to
            # use a dictionary that retains the patterns on a
            # parent-path level. But this works fine for a top-level
            # file in the main repo and top level of submodules
            if exclude and filename == '.gitattributes':
                excludes = []
                fh = open(filepath, 'r')
                for line in fh:
                    if not line: break
                    tokens = line.strip().split()
                    if 'export-ignore' in tokens[1:]:
                        excludes.append(tokens[0])
                fh.close()

            if not filename.startswith('.git') and not path.isdir(filepath):

                # check the patterns first
                ignore = False
                for pattern in excludes:
                    if fnmatch(filepath, pattern) or fnmatch(filename, pattern):
                        if verbose: print 'Exclude pattern matched (%s): %s' % (pattern, filepath)
                        ignore = True
                        break
                if ignore:
                    continue

                # baselevel is needed to tell the arhiver where it have to extract file
                yield fullpath,filename

        # get paths for every submodule
        for submodule in Popen("cd %s && git submodule --quiet foreach --recursive 'pwd'"%(repo_root,), shell=True, stdout=PIPE).stdout.read().splitlines():
            #chdir(submodule)
            # in order to get output path we need to exclude repository path from the submodule path
            prefix = submodule[len(repo_root)+1:]
            # recursion allows us to process repositories with more than one level of submodules
            #for git_file in git_files(path.join(repo_root,submodule)):
            for git_file in git_files(submodule,prefix=prefix):
                yield git_file


    if format == 'zip':
        from zipfile import ZipFile, ZIP_DEFLATED
        output_archive = ZipFile(path.abspath(output_file), 'w')
        for name, arcname in git_files():
            if verbose: print 'Compressing ' + arcname + '...'
            output_archive.write(name, prefix + arcname, ZIP_DEFLATED)
    elif format == 'tar':
        from tarfile import TarFile
        output_archive = TarFile(path.abspath(output_file), 'w')
        for name, arcname in git_files():
            if verbose: print 'Compressing ' + arcname + '...'
            #output_archive.add(path.join(name), arcname)
            #output_archive.add(path.join(name))
            output_archive.add(name,arcname)

if __name__ == '__main__':
    git_repositary_path = path.abspath('')
    git_repositary_name = path.basename(git_repositary_path)

    parser = OptionParser(usage="usage: %prog --output OUTPUT_FILE [--format FORMAT] [-v] [--prefix PREFIX]", version="%prog 1.0")

    parser.add_option('--format', type='choice', dest='format', choices=['zip','tar'],
                        default='tar',
                        help="format of the resulting archive: tar or zip. The default output format is %default")

    parser.add_option('--prefix', type='string', dest='prefix',
                        default='', help="prepend PREFIX to each filename in the archive")

    parser.add_option('-o', '--output', type='string', dest='output_file', default='', help='output file')
    parser.add_option('-v', '--verbose', action='store_true', dest='verbose', help='enable verbose mode')

    parser.add_option('--no-exclude', action='store_false', dest='exclude',
                        default=True, help="Dont read .gitattributes files for patterns containing export-ignore attrib")

    (options, args) = parser.parse_args()

    if options.output_file == '':
       parser.error('You must specify output file')
    elif path.isdir(options.output_file):
       parser.error('You cannot use directory as output')

    archive_git(options.output_file,options.format)