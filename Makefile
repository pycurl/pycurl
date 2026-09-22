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

SOURCES = src/easy.c src/easycb.c src/easyinfo.c src/easyopt.c src/easyperform.c \
	src/easyws.c src/mime.c src/module.c src/multi.c src/oscompat.c \
	src/pythoncompat.c src/share.c src/stringcompat.c src/threadsupport.c \
	src/url.c src/util.c

GEN_SOURCES = src/docstrings.c src/docstrings.h

ALL_SOURCES = src/pycurl.h $(GEN_SOURCES) $(SOURCES)

DOCSTRINGS_SOURCES = $(wildcard doc/docstrings/*.rst)

all: build

src/docstrings.c src/docstrings.h: $(DOCSTRINGS_SOURCES)
	$(PYTHON) -c "import setup; setup.generate_docstrings()"

gen: $(ALL_SOURCES)

build: $(ALL_SOURCES)
	$(PYTHON) setup.py build

do-test:
	make -C tests/fake-curl/libcurl
	./tests/run.sh
	$(PYFLAKES) python examples tests setup.py

test: build do-test

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
	-rm -f $(GEN_SOURCES)

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
