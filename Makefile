#
# to use a specific python version call
#   `make PYTHON=python2.7'
#

SHELL = /bin/sh

PYTHON = python
NOSETESTS = nosetests

# -c on linux
# freebsd does not understand -c
CHMOD_VERBOSE=-v

BUILD_WWW = build/www

RSYNC = rsync
##RSYNC_FLAGS = -av --relative -e ssh
RSYNC_FLAGS = -av --relative --delete --delete-after -e ssh

RSYNC_FILES = \
	htdocs \
	htdocs/download/.htaccess \
	upload

RSYNC_EXCLUDES = \
	'--exclude=htdocs/download/' \
	'--exclude=upload/Ignore/'

RSYNC_TARGET = /home/groups/p/py/pycurl/

RSYNC_USER = armco@web.sourceforge.net

# src/module.c is first because it declares global variables
# which other files reference; important for single source build
SOURCES = src/module.c src/easy.c src/multi.c src/oscompat.c src/pythoncompat.c \
	src/share.c src/stringcompat.c src/threadsupport.c

GEN_SOURCES = src/docstrings.c src/docstrings.h

ALL_SOURCES = src/pycurl.h $(GEN_SOURCES) $(SOURCES)

RELEASE_SOURCES = src/allpycurl.c

DOCSTRINGS_SOURCES = \
	doc/docstrings/curl.rst \
	doc/docstrings/curl_close.rst \
	doc/docstrings/curl_errstr.rst \
	doc/docstrings/curl_getinfo.rst \
	doc/docstrings/curl_pause.rst \
	doc/docstrings/curl_perform.rst \
	doc/docstrings/curl_reset.rst \
	doc/docstrings/curl_setopt.rst \
	doc/docstrings/curl_unsetopt.rst \
	doc/docstrings/multi.rst \
	doc/docstrings/multi_add_handle.rst \
	doc/docstrings/multi_close.rst \
	doc/docstrings/multi_fdset.rst \
	doc/docstrings/multi_info_read.rst \
	doc/docstrings/multi_perform.rst \
	doc/docstrings/multi_remove_handle.rst \
	doc/docstrings/multi_select.rst \
	doc/docstrings/multi_socket_action.rst \
	doc/docstrings/multi_socket_all.rst \
	doc/docstrings/pycurl_global_cleanup.rst \
	doc/docstrings/pycurl_global_init.rst \
	doc/docstrings/pycurl_module.rst \
	doc/docstrings/pycurl_version_info.rst \
	doc/docstrings/share.rst \
	doc/docstrings/share_close.rst \
	doc/docstrings/share_setopt.rst

all: build
src-release: $(RELEASE_SOURCES)

src/docstrings.c src/docstrings.h: $(DOCSTRINGS_SOURCES)
	$(PYTHON) setup.py docstrings

src/allpycurl.c: $(ALL_SOURCES)
	echo '#define PYCURL_SINGLE_FILE' >src/.tmp.allpycurl.c
	cat src/pycurl.h >>src/.tmp.allpycurl.c
	cat src/docstrings.c $(SOURCES) |sed -e 's/#include "pycurl.h"//' -e 's/#include "docstrings.h"//' >>src/.tmp.allpycurl.c
	mv src/.tmp.allpycurl.c src/allpycurl.c

gen: $(ALL_SOURCES)

build: $(ALL_SOURCES)
	$(PYTHON) setup.py build

build-release: $(RELEASE_SOURCES)
	PYCURL_RELEASE=1 $(PYTHON) setup.py build

do-test:
	mkdir -p tests/tmp
	PYTHONSUFFIX=$$(python -V 2>&1 |awk '{print $$2}' |awk -F. '{print $$1 "." $$2}') && \
	PYTHONPATH=$$(ls -d build/lib.*$$PYTHONSUFFIX):$$PYTHONPATH \
	$(PYTHON) -c 'import pycurl; print(pycurl.version)'
	PYTHONPATH=$$(ls -d build/lib.*$$PYTHONSUFFIX):$$PYTHONPATH \
	$(NOSETESTS) -a '!standalone'
	PYTHONPATH=$$(ls -d build/lib.*$$PYTHONSUFFIX):$$PYTHONPATH \
	$(NOSETESTS) -a standalone
	./tests/ext/test-suite.sh

test: build do-test
test-release: build-release do-test

# rails-style alias
c: console
console:
	PYTHONSUFFIX=$$(python -V 2>&1 |awk '{print $$2}' |awk -F. '{print $$1 "." $$2}') && \
	PYTHONPATH=$$(ls -d build/lib.*$$PYTHONSUFFIX):$$PYTHONPATH \
	$(PYTHON)

# (needs GNU binutils)
strip: build
	strip -p --strip-unneeded build/lib*/*.so
	chmod -x build/lib*/*.so

install install_lib:
	$(PYTHON) setup.py $@

clean:
	-rm -rf build dist
	-rm -f *.pyc *.pyo */*.pyc */*.pyo */*/*.pyc */*/*.pyo
	-rm -f MANIFEST
	-rm -f src/allpycurl.c $(GEN_SOURCES)
	cd src && $(MAKE) clean

distclean: clean

maintainer-clean: distclean

dist sdist: distclean
	$(PYTHON) setup.py sdist

# Rebuild missing or changed documentation.
# Editing docstrings in Python or C source will not cause the documentation
# to be rebuilt with this target, use docs-force instead.
docs: build
	mkdir -p build/docstrings
	for file in doc/docstrings/*.rst; do tail -n +3 $$file >build/docstrings/`basename $$file`; done
	PYTHONSUFFIX=$$(python -V 2>&1 |awk '{print $$2}' |awk -F. '{print $$1 "." $$2}') && \
	PYTHONPATH=$$(ls -d build/lib.*$$PYTHONSUFFIX):$$PYTHONPATH \
	sphinx-build doc build/doc

# Rebuild all documentation.
# As sphinx extracts documentation from pycurl modules, docs targets
# depend on build target.
docs-force: build
	# sphinx-docs has an -a option but it does not seem to always
	# rebuild everything
	rm -rf build/doc
	PYTHONSUFFIX=$$(python -V 2>&1 |awk '{print $$2}' |awk -F. '{print $$1 "." $$2}') && \
	PYTHONPATH=$$(ls -d build/lib.*$$PYTHONSUFFIX):$$PYTHONPATH \
	sphinx-build doc build/doc

www: docs
	mkdir -p build
	rsync -a www build --delete
	rsync -a build/doc/ build/www/htdocs/doc --exclude .buildinfo --exclude .doctrees
	cp doc/static/favicon.ico build/www/htdocs
	cp ChangeLog build/www/htdocs

rsync: rsync-prepare
	cd $(BUILD_WWW) && \
	$(RSYNC) $(RSYNC_FLAGS) $(RSYNC_EXCLUDES) $(RSYNC_FILES) $(RSYNC_USER):$(RSYNC_TARGET)

rsync-dry:
	$(MAKE) rsync 'RSYNC=rsync --dry-run'

rsync-check:
	$(MAKE) rsync 'RSYNC=rsync --dry-run -c'

# NOTE: Git does not maintain metadata like owners and file permissions,
#       so we have to care manually.
# NOTE: rsync targets depend on www.
rsync-prepare:
	chgrp $(CHMOD_VERBOSE) -R pycurl $(BUILD_WWW)
	chmod $(CHMOD_VERBOSE) g+r `find $(BUILD_WWW) -perm +400 -print`
	chmod $(CHMOD_VERBOSE) g+w `find $(BUILD_WWW) -perm +200 -print`
	chmod $(CHMOD_VERBOSE) g+s `find $(BUILD_WWW) -type d -print`
##	chmod $(CHMOD_VERBOSE) g+rws `find $(BUILD_WWW) -type d -perm -770 -print`
	chmod $(CHMOD_VERBOSE) g+rws `find $(BUILD_WWW) -type d -print`
	chmod $(CHMOD_VERBOSE) o-rwx $(BUILD_WWW)/upload
	#-rm -rf `find $(BUILD_WWW) -name .xvpics -type d -print`

.PHONY: all build test do-test strip install install_lib \
	clean distclean maintainer-clean dist sdist \
	docs docs-force \
	rsync rsync-dry rsync-check rsync-prepare

.NOEXPORT:
