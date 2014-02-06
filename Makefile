#
# to use a specific python version call
#   `make PYTHON=python2.2'
#

SHELL = /bin/sh

PYTHON = python
NOSETESTS = nosetests

all build:
	$(PYTHON) setup.py build

build-7.10.8:
	$(PYTHON) setup.py build --curl-config=/home/hosts/localhost/packages/curl-7.10.8/bin/curl-config

do-test:
	mkdir -p tests/tmp
	PYTHONSUFFIX=$$(python -V 2>&1 |awk '{print $$2}' |awk -F. '{print $$1 "." $$2}') && \
	PYTHONPATH=$$(ls -d build/lib.*$$PYTHONSUFFIX):$$PYTHONPATH \
	$(PYTHON) -c 'import pycurl; print(pycurl.version)'
	PYTHONPATH=$$(ls -d build/lib.*$$PYTHONSUFFIX):$$PYTHONPATH \
	$(NOSETESTS)
	./tests/ext/test-suite.sh

test: build do-test

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
	python2.2 setup.py bdist_wininst
	rm -rf build
	python2.3 setup.py bdist_wininst
	rm -rf build
	python2.4 setup.py bdist_wininst
	rm -rf build
	python2.2 setup_win32_ssl.py bdist_wininst
	rm -rf build
	python2.3 setup_win32_ssl.py bdist_wininst
	rm -rf build
	python2.4 setup_win32_ssl.py bdist_wininst
	rm -rf build

www docs:
	mkdir -p build
	rsync -av www build
	cd doc && for file in *.rst; do rst2html "$$file" ../build/www/htdocs/doc/`echo "$$file" |sed -e 's/.rst$$/.html/'`; done
	rst2html RELEASE-NOTES.rst build/www/htdocs/release-notes.html


.PHONY: all build test do-test strip install install_lib clean distclean maintainer-clean dist sdist windist

.NOEXPORT:
