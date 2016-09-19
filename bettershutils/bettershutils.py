
import shutil
import os
from os import path
from functools import wraps
import contextlib
import glob
import fnmatch

def _get_num_args_text(min, max):
    if min is not None and max is not None:
        return '{} to {} arguments'.format(min, max)
    elif min is not None:
        return 'at least {} argument{}'.format(
            min, 's' if min > 1 else '')
    elif max is not None:
        return 'no more than {} arguments'.format(max)
    else:
        return 'any number of arguments'

def require_args(min=None, max=None,
                  errors={None: 'Invalid number of arguments'}):
    '''Decorator that checks if the function has received a valid number
    of arguments.

    Parameters
    ----------
    min : int or None
        The minimum number of arguments the function must accept.
        Defaults to None (no minimum).
    max : int or None
        The maximum number of arguments the function must accept
        Defaults to None (no maximum).
    '''
    def require_args_decorator(func):
        @wraps(func)
        def new_func(*args, **kwargs):
            if max is not None and len(args) > max:
                raise TypeError('{} takes {}, but {} given'.format(
                    func, _get_num_args_text(min, max), len(args)))
            elif min is not None and len(args) < min:
                raise TypeError('{} takes {}, but {} given'.format(
                    func, _get_num_args_text(min, max), len(args)))
            return func(*args, **kwargs)
        return new_func
    return require_args_decorator

def expand_paths(*args, do_glob=True):
    '''Assumes all the args of func are paths, and expands them.

    If any args are passed, the function's kwargs are also expanded as
    paths if they match one of the args.

    Parameters
    ----------
    do_glob : bool
        If True, glob patterns in the args are expanded. Defaults to True. 
    '''
    def expand_paths_decorator(func):
        @wraps(func)
        def new_func(*fargs, **fkwargs):
            print('fargs are', fargs)
            fargs = [expand_path(arg) for arg in fargs]
            print('and now', fargs)
            if do_glob:
                new_args = []
                for arg in fargs:
                    new_args.extend(glob.glob(arg))
                fargs = new_args
            
            for kwarg in fkwargs:
                if kwarg in args:
                    fkwargs[kwarg] = expand_path(fkwargs[kwarg])
                
            return func(*fargs, **fkwargs)
        return new_func
    return expand_paths_decorator

@require_args(min=2, max=None)
def mv(*args):
    '''Move files from one location to another.

    If the the final argument is a directory, all preceding arguments
    are moved into this dir.

    If the final argument is a filepath, there can only be one other
    argument, which is moved to the target location.

    '''
    target = args[-1]
    sources = args[:-1]
    
    if not path.isdir(target) and len(sources) > 1:
        raise ValueError('Target is not a directory but multiple '
                         'sources were specified')

    if path.isdir(target):
        for source in sources:
            shutil.move(source, target)
    else:
        shutil.move(sources[0], target)

@require_args(min=1)
@expand_paths()
def rm(*args, recursive=False, ignore_errors=False):
    '''
    Delete files and/or directories.

    Parameters
    ----------
    *args : strings
        The file and directory paths to delete. Glob patterns are expanded.
    recursive : bool
        If True, will recursively delete folders and their contents.
        Defaults to False.
    ignore_errors : bool
        If True, will ignore errors when e.g. specified  files do not exist. 
        Defaults to False.
    '''
    for arg in args:
        if not path.exists(arg) and ignore_errors:
            continue
        if path.isdir(arg):
            if not recursive:
                error = 'Cannot remove "{}": Is a directory'.format(arg)
                if ignore_errors:
                    print(error)
                else:
                    raise OSError(error)
            else:
                shutil.rmtree(arg, ignore_errors=ignore_errors)
        else:
            os.unlink(arg)

@require_args(min=2)
@expand_paths()
def cp(*args, recursive=False):
    '''Copy files and/or directories.

    Parameters
    ----------
    *args : strings
        The names of files to copy, and target directory. The final arg is the
        target filepath/directory, all preceding args are copied. Each path
        is expanded as a glob pattern.
    recursive : bool
        Whether to copy directories (recursively).  
    '''
    target = args[-1]
    sources = args[:-1]

    if not path.isdir(target) and len(sources) > 1:
        raise ValueError('Target is not a directory but multiple '
                         'sources were specified')

    if path.isdir(target):
        for source in sources:
            if path.isdir(source):
                if recursive:
                    dir_name = path.basename(source)
                    shutil.copytree(source, path.join(target, dir_name))
                else:
                    print('Omitting directory {}'.format(source))
            else:
                shutil.copy(source, target)
    else:
        source = sources[0]

        if path.isdir(source) and path.exists(target):
            raise FileExistsError('Cannot copy directory to file that '
                                  'already exists')
        elif path.isdir(source):
            shutil.copytree(source, target)
        else:
            shutil.copy(source, target)
    

def pwd():
    return expand_path(os.curdir)


@expand_paths('path', do_glob=False)
def ls(*args):
    if not args:
        args = ['.']
    results = {}
    for arg in args:
        if path.isdir(arg):
            results[arg] = os.listdir(arg)
        elif path.exists(arg):  # arg is a file
            results[arg] = [arg]
        else:
            results[arg] = glob.glob(arg)
    if len(results) == 1:
        return results[list(results.keys())[0]]
    return results

def mkdir(dir_name, mode=511, parents=False, exist_ok=False):
    if parents:
        os.makedirs(dir_name, mode=mode, exist_ok=exist_ok)
    else:
        if path.exists(dir_name):
            if exist_ok:
                return
        os.mkdir(dir_name, mode=mode)

# def ln(source, target, softlink=False):
#     pass

def expand_path(input):
    return path.abspath(path.expanduser(input))

@contextlib.contextmanager
def current_directory(new_dir):
    '''Context manager to temporarily move to a different directory.

    '''
    new_dir = expand_path(new_dir)
    cur_dir = os.getcwd()
    os.chdir(new_dir)
    yield
    os.chdir(cur_dir)
