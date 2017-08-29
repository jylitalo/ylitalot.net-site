#!/usr/bin/python

#
# doctest requires MiniMock
# in Mac OS X: sudo easy_install MiniMock
#
import fnmatch
import glob
import os
import stat
import sys


class Jekyll(object):
    @staticmethod
    def find_source_dir(dir=os.getcwd()):
        """
        >>> Jekyll.find_source_dir('/tmp/octo/source/_posts')
        '/tmp/octo/source'
        >>> Jekyll.find_source_dir('/tmp/octo/source/by-lens')
        '/tmp/octo/source'
        >>> Jekyll.find_source_dir('/tmp/octo/source')
        '/tmp/octo/source'
        >>> Jekyll.find_source_dir('/tmp/jekyll/_posts')
        '/tmp/jekyll'
        >>> Jekyll.find_source_dir('/tmp/jekyll/_site')
        '/tmp/jekyll'
        >>> Jekyll.find_source_dir('/b/to/fail')
        Traceback (most recent call last):
        ...
        AssertionError: unable to determine source directory from /b/to/fail
        """
        # Jekyll
        if dir.endswith('/_posts'):
            return dir[:dir.rfind('/')]
        if dir.endswith('/_site'):
            return dir[:dir.rfind('/')]
        if os.access(dir + '/_posts', os.R_OK):
            return dir
        assert False, 'unable to determine source directory from ' + dir

    @staticmethod
    def head(datetime, layout, title):
        if ':' in title:
            title = "'%s'" % (title)
        return """---
date: '%s'
layout: %s
status: publish
title: %s
---
""" % (datetime, layout, title)


class AssetsFinder(Jekyll):
    def __init__(self):
        self._dir = None
        self._linked = {}
        self._url_names = {}
        self.scaled_images_root = '../images'
    # end of __init__(self)

    @property
    def dir(self): return self._dir

    @dir.setter
    def dir(self, dname):
        """
        >>> a = AssetsFinder()
        >>> a.dir('invalid')
        Traceback (most recent call last):
        ...
        AssertionError: Source Directory (invalid) is missing sub-directories: _posts, _images, assets
        >>> from minimock import mock
        >>> mock('os.path.isdir',returns=True)
        >>> a.dir('valid')
        >>> self._dir
        valid
        """
        errors = []
        for key in ['_posts', self.scaled_images_root]:
            if not os.path.isdir('%s/%s' % (dname, key)):
                errors += [key]
        msg = 'Source directory (%s) is missing sub-directories: %s'
        assert not errors, msg % (dname, ', '.join(errors))
        self._dir = dname
    # end of dif(self, dname)

    def _is_valid_filename(fname):
        return not self._ignore(fname) and self._validate_found(fname)

    def _scan_tree(self, subdir):
        ret = []
        ignore = len(self.dir)
        for root, dirnames, fnames in os.walk(self.dir + subdir):
            root = root[ignore:]
            fnames = [os.path.join(root, fn) for fn in fnames]
            fnames = [fn for fn in fnames if self._is_valid_filename(fn)]
            ret.extend(fnames)
        print("scan_tree(%s) = %s" % (subdir, str(ret)))
        return ret
    # enf of _scan_tree(self,subdir)

    def _ignore(self, fname):
        """
        >>> i = AssetsFinder()
        >>> i._ignore('/foobar/.DS_Store')
        True
        >>> i._ignore('/images/foobar.jpg')
        True
        >>> i._ignore('/_posts/.#1970-01-01-foobar.markdown')
        True
        >>> i._ignore('/_posts/1970-01-01-foobar.markdown')
        False
        """
        if fname.endswith('.DS_Store'):
            return True
        if fname.find('/.#') > -1:
            return True
        if fname.startswith('/images/') and fname.count('/') == 2:
            return True
        return False
    # end of _ignore(fname)

    def _find_markdown_files(self):
        """
        Returns list of markdown files under self.dir

        >>> a = AssetsFinder()
        >>> ret1 = ('.',[],['index.markdown','1970-01-01-valid.markdown'])
        >>> ret2 = ('abc',[],['.#fo.markdown#','abc.markdown','abc.markdown~'])
        >>> from minimock import mock
        >>> mock('os.walk',returns=[ret1,ret2])
        >>> a._find_markdown_files()
        Called os.walk(None, followlinks=True)
        ['./index.markdown', './1970-01-01-valid.markdown', 'abc/abc.markdown']
        """
        ret = []
        for root, dirnames, fnames in os.walk(self.dir):
            for suffix in ['markdown', 'md']:
                flist = fnmatch.filter(fnames, '[0-9a-z]*.' + suffix)
                ret.extend([os.path.join(root, fn) for fn in flist])
        return ret
    # end of _find_markdown_files(self)

    @staticmethod
    def get_url(fname):
        """
        Determine the filename under website.
        >>> AssetsFinder.get_url('f/source/_posts/2013-11-27-foobar.markdown')
        'foobar.html'
        >>> AssetsFinder.get_url('f/source/_posts/2013-11-27-foo-bar.md')
        'foo-bar.html'
        >>> AssetsFinder.get_url('f/source/foobar.markdown')
        'foobar.html'
        >>> AssetsFinder.get_url('f/source/foo-bar.md')
        'foo-bar.html'
        """
        for suffix in ['.markdown', '.md']:
            if fname.endswith(suffix):
                fname = fname[:-len(suffix)]
                break
        if fname.startswith('_posts/'):
            begin_index = len('yyyy-mm-dd-')
            return os.path.basename(fname)[begin_index:] + '.html'
        else:
            return os.path.basename(fname) + '.html'
    # end of get_url(fname)

    @staticmethod
    def fix_filename(fname, lines):
        """
        date: header in markdown and filename don't match.
        """
        date_str = None
        for line in lines:
            line = line.rstrip()
            if line.startswith("date: '") and line[-1] == "'":
                date_str = line[line.find("'")+1:line.rfind(' ')]
        basename = os.path.basename(fname)
        if date_str and not basename.startswith(date_str + '-'):
            fname2 = fname.replace(basename[:len(date_str)], date_str)
            print('git mv -f %s %s' % (fname, fname2))
            os.system('git mv -f %s %s' % (fname, fname2))
            return fname2
        return fname

    def scan(self, dir=os.getcwd()):
        self.dir = self.find_source_dir(dir)
        print('### using %s as root directory' % (self.dir))
        fnames = self._find_markdown_files()
        assert fnames, 'Unable to find any markdown files from ' + self.dir
        img = '/images/'
        imglen = len(img)
        print('### processing %d markdown files' % (len(fnames)))
        for fname in fnames:
            f = open(fname)
            lines = f.readlines()
            f.close()
            fname = self.fix_filename(fname, lines)
            url_name = self.get_url(fname)
            duplicate = \
                url_name in self._url_names \
                and self._url_names[url_name] != fname
            msg = 'Found duplicate url on following files: %s, %s'
            assert not duplicate, msg % (self._url_names[url_name], fname)
            # end of if url_name in ...
            self._url_names[url_name] = fname
            for line in lines:
                for link in self._extract_from_markdown(line):
                    if link.startswith(img):
                        link = '%s/%s' % (
                            self.scaled_images_root, link[imglen:])
                    if link in self._linked:
                        self._linked[link] += [url_name]
                    else:
                        self._linked[link] = [url_name]
                # end of for link in
            # end of for line in ...
        # end of for fname in ...
    # end of scan(self)

    @staticmethod
    def _extract_from_markdown(line):
        """
        >>> AssetsFinder._extract_from_markdown('foobar')
        []
        >>> AssetsFinder._extract_from_markdown('[foobar](/images/link.jpg)')
        ['/images/link.jpg']
        >>> AssetsFinder._extract_from_markdown('[f](/images/link.jpg 'f')')
        ['/images/link.jpg']
        >>> AssetsFinder._extract_from_markdown('{% img /images/s.jpg 'f'}')
        ['/images/s.jpg']
        >>> md = '[![f](/i/a.jpg 'f')](/i/b.jpg 'g')'
        >>> AssetsFinder._extract_from_markdown(md)
        ['/i/a.jpg', '/i/b.jpg']
        """
        links = []
        if line.startswith('{% slide '):
            link = line.split(' ')[2]
            line = '(%s_t.jpg)(%s_l.jpg)' % (link, link)
        elif line.startswith('{% cover '):
            link = line.split(' ')[2]
            line = '(%s_t.jpg)(%s_c.jpg)' % (link, link)
        # end of if line.startswith ...

        for field in line.split('(/images')[1:]:
            field = '/images%s' % (field[:field.find(')')])
            if ' "' in field:
                field = field[:field.find(' "')]
            links += [field]
        # end of for field in ...
        for c in [' ', '"', "'"]:
            for field in line.split('%s/images' % (c))[1:]:
                field = '/images' + field[:field.find(c, 1)]
                links += [field]
        # end of for c in ...
        return links
    # end of _extract_from_markdown(line)

    def _validate_found(self, fname): return True

    def _validate_waste(self, fname): print("WASTE: '%s'" % (fname))

    def _validate_missing(self, fname):
        print("MISSING: '%s' (%s)" % (fname, ', '.join(self._linked[fname])))

    def validate(self):
        found = set(self._scan_tree(self.scaled_images_root))
        linked = set(self._linked.keys())
        waste = list(found - linked)
        waste.sort()
        for fname in waste:
            self._validate_waste(fname)
        missing = list(linked - found)
        missing.sort()
        for fname in missing:
            fname = fname.replace(
                        '/images/', '%s/' % (self.scaled_images_root))
            self._validate_missing(fname)
    # end of validate(self)


class AssetsFixer(AssetsFinder):
    def __init__(self):
        AssetsFinder.__init__(self)
        self._original_images_root = []
        for d in ['original_jpg', 'jpg']:
            self._original_images_root += [os.path.expanduser('~/kuvat/' + d)]
        self._validate_original = True
        self._convert_missing = True
        self._original_missing = []
    # end of __init__(self)

    def _original_image(self, fname):
        # Setup
        begin_index = fname.find('/', len(self.scaled_images_root) + 1)
        end_index = len('_t.jpg')
        if fname[-end_index] != '_':
            end_index = len('.jpg')
        # Execute
        for d in self._original_images_root:
            pattern = '%s%s.*' % (d, fname[begin_index:-end_index])
            original_fname = glob.glob(pattern)
            if original_fname:
                return original_fname[0]
            original_fname = glob.glob(pattern.replace('/IMG_', '/img_'))
            if original_fname:
                return original_fname[0]
        return None
    # end of _original_image(self, fname)

    def _validate_found(self, fname):
        # Setup
        if fname == '/%s/2014/03/P3260000_t.jpg' % (self.scaled_images_root):
            return False
        if not self._validate_original:
            return True
        orig_fname = self._original_image(fname)
        if not orig_fname:
            return False
        # Execute
        full_fname = self.dir + fname
        orig_mtime = os.stat(orig_fname)[stat.ST_MTIME]
        full_mtime = os.stat(full_fname)[stat.ST_MTIME]
        if orig_mtime < full_mtime:
            return True
        print('unlink %s (%d vs. %d)' % (full_fname, orig_mtime, full_mtime))
        os.unlink(full_fname)
        return False
    # end of _validate_found(self, fname)

    def _validate_waste(self, fname):
        print('unlinking %s%s (validate waste)' % (self.dir, fname))
        os.unlink('%s%s' % (self.dir, fname))

    def _resize_image(self, src, dest, resolution):
        cmdline = 'convert -resize %s %s %s' % (resolution, src, dest)
        print('### ' + cmdline)
        os.system(cmdline)

    def _validate_missing(self, fname):
        # Setup
        if fname == '/%s/2014/03/P3260000_t.jpg' % (self.scaled_images_root):
            return
        if not self._convert_missing:
            AssetsFinder._validate_missing(self, fname)
            return
        original_fname = self._original_image(fname)
        if not original_fname:
            self._original_missing += [(fname, ', '.join(self._linked[fname]))]
            return
        # Execute
        full_fname = self.dir + fname
        dname = os.path.dirname(full_fname)
        if not os.access(dname, os.F_OK):
            os.makedirs(dname)
        assert os.access(dname, os.W_OK), 'need write access to ' + dname
        # print('### images for: ' + ','.join(self._linked[fname]))
        if fname.endswith('_t.jpg'):
            args = '-thumbnail 150x150^ -gravity center -extent 150x150'
            cmdline = 'convert %s %s %s' % (args, original_fname, full_fname)
            print('### ' + cmdline)
            os.system(cmdline)
        elif fname.endswith('_c.jpg'):
            self._resize_image(original_fname, full_fname, '750x750')
        elif fname.endswith('_l.jpg'):
            self._resize_image(original_fname, full_fname, '1600x1600')
        else:
            print('### unknown suffix on ' + fname)
        # end of if fname.endswith ...
    # end of _validate_missing(self, fname)

    def validate(self):
        AssetsFinder.validate(self)
        if self._original_missing:
            print '!!! Original image missing for:'
            for fname, references in self._original_missing:
                print('!!! %s references: %s' % (fname, references))
    # end of validate(self)


if __name__ == '__main__':
    assets = AssetsFixer()
    assets.scan()
    assets.validate()
