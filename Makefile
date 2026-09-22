#
# to use a specific python version call
#   `make PYTHON=python2.7'
#

SHELL = /bin/sh

PYTHON = python
PYTEST = pytest
PYFLAKES = pyflakes

PYTHONMAJOR=$$($(PYTHON) -V 2>&1 |awk '{print $$2}' |awk -F. '{print $$1}')
PYTHONMINOR=$$($(PYTHON) -V 2>&1 |awk '{print $$2}' |awk -F. '{print $$2}')

# src/module.c is first because it declares global variables
# which other files reference; important for single source build
SOURCES = src/easy.c src/easycb.c src/easyinfo.c src/easyopt.c src/easyperform.c \
	src/easyws.c src/mime.c src/module.c src/multi.c src/oscompat.c \
	src/pythoncompat.c src/share.c src/stringcompat.c src/threadsupport.c \
	src/url.c src/util.c

GEN_SOURCES = src/docstrings.c src/docstrings.h

ALL_SOURCES = src/pycurl.h $(GEN_SOURCES) $(SOURCES)

RELEASE_SOURCES = src/allpycurl.c

DOCSTRINGS_SOURCES = $(wildcard doc/docstrings/*.rst)

all: build
src-release: $(RELEASE_SOURCES)

src/docstrings.c src/docstrings.h: $(DOCSTRINGS_SOURCES)
	$(PYTHON) -c "import setup; setup.generate_docstrings()"

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
	make -C tests/fake-curl/libcurl
	./tests/run.sh
	$(PYFLAKES) python examples tests setup.py

test: build do-test
test-release: build-release do-test

# rails-style alias
c: console
console:
	PYTHONPATH=$$(ls -d build/lib.*$$PYTHONMAJOR*$$PYTHONMINOR):$$PYTHONPATH \
	$(PYTHON)

# (needs GNU binutils)
strip: build
	strip -p --strip-unneeded build/lib*/*.so
	chmod -x build/lib*/*.so

install:
	$(PYTHON) -m pip install .

clean:
	-rm -rf build dist
	-rm -f *.pyc *.pyo */*.pyc */*.pyo */*/*.pyc */*/*.pyo
	-rm -f MANIFEST
	-rm -f src/allpycurl.c $(GEN_SOURCES)

distclean: clean

maintainer-clean: distclean

dist sdist: distclean
	$(PYTHON) setup.py sdist

run-quickstart:
	./tests/run-quickstart.sh

# Rebuild missing or changed documentation.
# Editing docstrings in Python or C source will not cause the documentation
# to be rebuilt with this target, use docs-force instead.
docs: build
	PYTHONPATH=$$(ls -d build/lib.*$$PYTHONMAJOR*$$PYTHONMINOR):$$PYTHONPATH \
	$(PYTHON) -m sphinx doc build/doc
	cp ChangeLog build/doc

# Rebuild all documentation.
# As sphinx extracts documentation from pycurl modules, docs targets
# depend on build target.
docs-force: build
	# sphinx-docs has an -a option but it does not seem to always
	# rebuild everything
	rm -rf build/doc
	PYTHONPATH=$$(ls -d build/lib.*$$PYTHONMAJOR*$$PYTHONMINOR):$$PYTHONPATH \
	$(PYTHON) -m sphinx doc build/doc
	cp ChangeLog build/doc

.PHONY: all build test do-test strip install \
	clean distclean maintainer-clean dist sdist \
	docs docs-force

.NOEXPORT:
