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
	cd src && $(MAKE) clean

distclean: clean

maintainer-clean: distclean

dist sdist: distclean
	$(PYTHON) setup.py sdist

# target for maintainer
windist: distclean
	rm -rf build
	python2.1 setup.py bdist_wininst
	rm -rf build
	python2.2 setup.py bdist_wininst
	rm -rf build
	python2.3b1 setup.py bdist_wininst
	rm -rf build
	python2.1 setup_win32_ssl.py bdist_wininst
	rm -rf build
	python2.2 setup_win32_ssl.py bdist_wininst
	rm -rf build
	python2.3b1 setup_win32_ssl.py bdist_wininst
	rm -rf build


.PHONY: all build test strip install install_lib clean distclean maintainer-clean dist sdist windist

.NOEXPORT:
