"""\
Package resource API
--------------------

A resource is a logical file contained within a package, or a logical
subdirectory thereof.  The package resource API expects resource names
to have their path parts separated with ``/``, *not* whatever the local
path separator is.  Do not use os.path operations to manipulate resource
names being passed into the API.

The package resource API is designed to work with normal filesystem packages,
.egg files, and unpacked .egg files.  It can also work in a limited way with
.zip files and with custom PEP 302 loaders that support the ``get_data()``
method.
"""
__all__ = [
    'register_loader_type', 'get_provider', 'IResourceProvider',
    'ResourceManager', 'iter_distributions', 'require', 'resource_string',
    'resource_stream', 'resource_filename', 'set_extraction_path',
    'cleanup_resources', 'parse_requirements', # 'glob_resources'
]

import sys, os, zipimport, time, re
_provider_factories = {}

def register_loader_type(loader_type, provider_factory):
    """Register `provider_factory` to make providers for `loader_type`

    `loader_type` is the type or class of a PEP 302 ``module.__loader__``,
    and `provider_factory` is a function that, passed a *module* object,
    returns an ``IResourceProvider`` for that module.
    """
    _provider_factories[loader_type] = provider_factory

def get_provider(moduleName):
    """Return an IResourceProvider for the named module"""
    module = sys.modules[moduleName]
    loader = getattr(module, '__loader__', None)
    return _find_adapter(_provider_factories, loader)(module)


class IResourceProvider:

    """An object that provides access to package resources"""

    def get_resource_filename(manager, resource_name):
        """Return a true filesystem path for `resource_name`

        `manager` must be an ``IResourceManager``"""

    def get_resource_stream(manager, resource_name):
        """Return a readable file-like object for `resource_name`

        `manager` must be an ``IResourceManager``"""

    def get_resource_string(manager, resource_name):
        """Return a string containing the contents of `resource_name`

        `manager` must be an ``IResourceManager``"""

    def has_resource(resource_name):
        """Does the package contain the named resource?"""

    def has_metadata(name):
        """Does the package's distribution contain the named metadata?"""

    def get_metadata(name):
        """The named metadata resource as a string"""

    def get_metadata_lines(name):
        """Yield named metadata resource as list of non-blank non-comment lines

       Leading and trailing whitespace is stripped from each line, and lines
       with ``#`` as the first non-blank character are omitted.
       """

    # XXX list_resources?  glob_resources?





class ResourceManager:
    """Manage resource extraction and packages"""

    extraction_path = None

    def __init__(self):
        self.cached_files = []

    def resource_exists(self, package_name, resource_name):
        """Does the named resource exist in the named package?"""
        return get_provider(package_name).has_resource(self, resource_name)

    def resource_filename(self, package_name, resource_name):
        """Return a true filesystem path for specified resource"""
        return get_provider(package_name).get_resource_filename(self,resource_name)

    def resource_stream(self, package_name, resource_name):
        """Return a readable file-like object for specified resource"""
        return get_provider(package_name).get_resource_stream(self,resource_name)

    def resource_string(self, package_name, resource_name):
        """Return specified resource as a string"""
        return get_provider(package_name).get_resource_string(self,resource_name)


















    def get_cache_path(self, archive_name, names=()):
        """Return absolute location in cache for `archive_name` and `names`

        The parent directory of the resulting path will be created if it does
        not already exist.  `archive_name` should be the base filename of the
        enclosing egg (which may not be the name of the enclosing zipfile!),
        including the ".egg" extension.  `names`, if provided, should be a
        sequence of path name parts "under" the egg's extraction location.

        This method should only be called by resource providers that need to
        obtain an extraction location, and only for names they intend to
        extract, as it tracks the generated names for possible cleanup later.
        """
        extract_path = self.extraction_path
        extract_path = extract_path or os.path.expanduser('~/.python-eggs')
        target_path = os.path.join(extract_path, archive_name, *names)
        _ensure_directory(target_path)
        self.cached_files.append(target_path)
        return target_path


    def postprocess(self, filename):
        """Perform any platform-specific postprocessing of file `filename`

        This is where Mac header rewrites should be done; other platforms don't
        have anything special they should do.

        Resource providers should call this method ONLY after successfully
        extracting a compressed resource.  They must NOT call it on resources
        that are already in the filesystem.
        """
        # XXX









    def set_extraction_path(self, path):
        """Set the base path where resources will be extracted to, if needed.

        If not set, this defaults to ``os.expanduser("~/.python-eggs")``.
        Resources are extracted to subdirectories of this path based upon
        information given by the ``IResourceProvider``.  You may set this to a
        temporary directory, but then you must call ``cleanup_resources()`` to
        delete the extracted files when done.  There is no guarantee that
        ``cleanup_resources()`` will be able to remove all extracted files.

        (Note: you may not change the extraction path for a given resource
        manager once resources have been extracted, unless you first call
        ``cleanup_resources()``.)
        """
        if self.cached_files:
            raise ValueError(
                "Can't change extraction path, files already extracted"
            )

        self.extraction_path = path

    def cleanup_resources(self, force=False):
        """
        Delete all extracted resource files and directories, returning a list
        of the file and directory names that could not be successfully removed.
        This function does not have any concurrency protection, so it should
        generally only be called when the extraction path is a temporary
        directory exclusive to a single process.  This method is not
        automatically called; you must call it explicitly or register it as an
        ``atexit`` function if you wish to ensure cleanup of a temporary
        directory used for extractions.
        """
        # XXX








def iter_distributions(requirement=None, path=None):
    """Iterate over distributions in `path` matching `requirement`

    The `path` is a sequence of ``sys.path`` items.  If not supplied,
    ``sys.path`` is used.

    The `requirement` is an optional string specifying the name of the
    desired distribution.
    """
    if path is None:
        path = sys.path

    if requirement is not None:
        requirements = list(parse_requirements(requirement))
        try:
            requirement, = requirements
        except ValueError:
            raise ValueError("Must specify exactly one requirement")

    for item in path:
        source = get_dist_source(item)
        for dist in source.iter_distributions(requirement):
            yield dist


















def require(*requirements):
    """Ensure that distributions matching `requirements` are on ``sys.path``

    `requirements` must be a string or a (possibly-nested) sequence
    thereof, specifying the distributions and versions required.
    XXX THIS IS DRAFT CODE FOR DESIGN PURPOSES ONLY RIGHT NOW
    """
    all_distros = {}
    installed = {}
    for dist in iter_distributions():
        key = dist.name.lower()
        all_distros.setdefault(key,[]).append(dist)
        if dist.installed():
            installed[key] = dist   # XXX what if more than one on path?

    all_requirements = {}

    def _require(requirements,source=None):
        for req in parse_requirements(requirements):
            name,vers = req # XXX
            key = name.lower()
            all_requirements.setdefault(key,[]).append((req,source))
            if key in installed and not req.matches(installed[key]):
                raise ImportError(
                    "The installed %s distribution does not match"  # XXX
                )   # XXX should this be a subclass of ImportError?
            all_distros[key] = distros = [
                dist for dist in all_distros.get(key,[])
                if req.matches(dist)
            ]
            if not distros:
                raise ImportError(
                    "No %s distribution matches all criteria for " % name
                )   # XXX should this be a subclass of ImportError?
        for key in all_requirements.keys(): # XXX sort them
            pass
            # find "best" distro for key and install it
            # after _require()-ing its requirements
        
    _require(requirements)
        
class DefaultProvider:
    """Provides access to package resources in the filesystem"""

    egg_info = None

    def __init__(self, module):
        self.module = module
        self.loader = getattr(module, '__loader__', None)
        self.module_path = os.path.dirname(module.__file__)

    def get_resource_filename(self, manager, resource_name):
        return self._fn(resource_name)

    def get_resource_stream(self, manager, resource_name):
        return open(self._fn(resource_name), 'rb')

    def get_resource_string(self, manager, resource_name):
        return self._get(self._fn(resource_name))

    def has_resource(self, resource_name):
        return self._has(self._fn(resource_name))

    def has_metadata(self, name):
        if not self.egg_info:
            raise NotImplementedError("Only .egg supports metadata")
        return self._has(os.path.join(self.egg_info, *name.split('/')))

    def get_metadata(self, name):
        if not self.egg_info:
            raise NotImplementedError("Only .egg supports metadata")
        return self._get(os.path.join(self.egg_info, *name.split('/')))

    def get_metadata_lines(self, name):
        return yield_lines(self.get_metadata(name))







    def _has(self, path):
        return os.path.exists(path)

    def _get(self, path):
        stream = open(path, 'rb')
        try:
            return stream.read()
        finally:
            stream.close()

    def _fn(self, resource_name):
        return os.path.join(self.module_path, *resource_name.split('/'))


register_loader_type(type(None), DefaultProvider)



class NullProvider(DefaultProvider):
    """Try to implement resource support for arbitrary PEP 302 loaders"""

    def _has(self, path):
        raise NotImplementedError(
            "Can't perform this operation for unregistered loader type"
        )

    def _get(self, path):
        if hasattr(self.loader, 'get_data'):
            return self.loader.get_data(path)
        raise NotImplementedError(
            "Can't perform this operation for loaders without 'get_data()'"
        )


register_loader_type(object, NullProvider)






class ZipProvider(DefaultProvider):
    """Resource support for zips and eggs"""

    egg_name = None
    eagers   = None

    def __init__(self, module):
        self.module = module
        self.loader = module.__loader__
        self.zipinfo = zipimport._zip_directory_cache[self.loader.archive]
        self.zip_pre = self.loader.archive+os.sep

        path = self.module_path = os.path.dirname(module.__file__)
        old = None
        self.prefix = []
        while path!=old:
            if path.lower().endswith('.egg'):
                self.egg_name = os.path.basename(path)
                self.egg_info = os.path.join(path, 'EGG-INFO')
                break
            old = path
            path, base = os.path.split(path)
            self.prefix.append(base)

    def _short_name(self, path):
        if path.startswith(self.zip_pre):
            return path[len(self.zip_pre):]
        return path

    def _has(self, path):
        return self._short_name(path) in self.zipinfo

    def _get(self, path):
        return self.loader.get_data(path)

    def get_resource_stream(self, manager, resource_name):
        return StringIO(self.get_resource_string(manager, resource_name))




    def _extract_resource(self, manager, resource_name):
        parts = resource_name.split('/')
        zip_path = os.path.join(self.module_path, *parts)
        zip_stat = self.zipinfo[os.path.join(*self.prefix+parts)]
        t,d,size = zip_stat[5], zip_stat[6], zip_stat[3]
        date_time = (
            (d>>9)+1980, (d>>5)&0xF, d&0x1F,                      # ymd
            (t&0xFFFF)>>11, (t>>5)&0x3F, (t&0x1F) * 2, 0, 0, -1   # hms, etc.
        )
        timestamp = time.mktime(date_time)
        real_path = manager.get_cache_path(self.egg_name, self.prefix+parts)

        if os.path.isfile(real_path):
            stat = os.stat(real_path)
            if stat.st_size==size and stat.st_mtime==timestamp:
                # size and stamp match, don't bother extracting
                return real_path

        # print "extracting", zip_path

        data = self.loader.get_data(zip_path)
        open(real_path, 'wb').write(data)
        os.utime(real_path, (timestamp,timestamp))
        manager.postprocess(real_path)
        return real_path

    def _get_eager_resources(self):
        if self.eagers is None:
            eagers = []
            for name in ('native_libs.txt', 'eager_resources.txt'):
                if self.has_metadata(name):
                    eagers.extend(self.get_metadata_lines(name))
            self.eagers = eagers
        return self.eagers







    def get_resource_filename(self, manager, resource_name):
        if not self.egg_name:
            raise NotImplementedError(
                "resource_filename() only supported for .egg, not .zip"
            )

        # should lock for extraction here
        eagers = self._get_eager_resources()
        if resource_name in eagers:
            for name in eagers:
                self._extract_resource(manager, name)

        return self._extract_resource(manager, resource_name)


register_loader_type(zipimport.zipimporter, ZipProvider)


def StringIO(*args, **kw):
    """Thunk to load the real StringIO on demand"""
    global StringIO
    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO
    return StringIO(*args,**kw)


def get_distro_source(path_item):
    pass    # XXX











def yield_lines(strs):
    """Yield non-empty/non-comment lines of a ``basestring`` or sequence"""
    if isinstance(strs,basestring):
        for s in strs.splitlines():
            s = s.strip()
            if s and not s.startswith('#'):     # skip blank lines/comments
                yield s
    else:
        for ss in strs:
            for s in yield_lines(ss):
                yield s

LINE_END = re.compile(r"\s*(#.*)?$").match         # whitespace and comment
CONTINUE = re.compile(r"\s*\\\s*(#.*)?$").match    # line continuation
DISTRO   = re.compile(r"\s*(\w+)").match           # Distribution name
VERSION  = re.compile(r"\s*(<=?|>=?|==|!=)\s*((\w|\.)+)").match  # version info
COMMA    = re.compile(r"\s*,").match               # comma between items
























def parse_requirements(strs):
    """Yield ``Requirement`` objects for each specification in `strs`

    `strs` must be an instance of ``basestring``, or a (possibly-nested)
    sequence thereof.
    """
    # create a steppable iterator, so we can handle \-continuations
    lines = iter(yield_lines(strs))
    for line in lines:
        line = line.replace('-','_')
        match = DISTRO(line)
        if not match:
            raise ValueError("Missing distribution spec", line)
        distname = match.group(1)
        p = match.end()
        specs = []
        while not LINE_END(line,p):
            if CONTINUE(line,p):
                try:
                    line = lines.next().replace('-','_'); p = 0
                except StopIteration:
                    raise ValueError(
                        "\\ must not appear on the last nonblank line"
                    )
            match = VERSION(line,p)
            if not match:
                raise ValueError("Expected version spec in",line,"at",line[p:])
            specs.append(match.group(1,2))
            p = match.end()
            match = COMMA(line,p)
            if match:
                p = match.end() # skip the comma
            elif not LINE_END(line,p):
                raise ValueError("Expected ',' or EOL in",line,"at",line[p:])

        yield distname, specs





def _get_mro(cls):
    """Get an mro for a type or classic class"""
    if not isinstance(cls,type):
        class cls(cls,object): pass
        return cls.__mro__[1:]
    return cls.__mro__

def _find_adapter(registry, ob):
    """Return an adapter factory for `ob` from `registry`"""
    for t in _get_mro(getattr(ob, '__class__', type(ob))):
        if t in registry:
            return registry[t]


def _ensure_directory(path):
    dirname = os.path.dirname(path)
    if not os.path.isdir(dirname):
        os.makedirs(dirname)


# Set up global resource manager

_manager = ResourceManager()

def _initialize(g):
    for name in dir(_manager):
        if not name.startswith('_'):
            g[name] = getattr(_manager, name)
_initialize(globals())












