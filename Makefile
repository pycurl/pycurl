#
# to use a specific python version call
#   `make PYTHON=python2.2'
#

SHELL = /bin/sh

PYTHON = python2.2
PYTHON = python

all build:
	$(PYTHON) setup.py build

test: build
	$(PYTHON) tests/test_internals.py -q

install install_lib:
	$(PYTHON) setup.py $@

clean:
	-rm -rf build dist
	-rm -f *.pyc *.pyo */*.pyc */*.pyo
	-rm -f MANIFEST
	cd src && $(MAKE) clean

distclean: clean

maintainer-clean: distclean

dist sdist: distclean
	$(PYTHON) setup.py sdist

windist:
	$(PYTHON) setup.py bdist_wininst

.PHONY: all build test install install_lib clean distclean maintainer-clean dist sdist windist

.NOEXPORT:

